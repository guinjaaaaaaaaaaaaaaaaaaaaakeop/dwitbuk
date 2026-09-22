"""Runs one eyes request in a fresh, read-only host session and saves the structured answer.

  python eyes_worker.py --request FILE --response FILE [--host claude|codex] [--model M] [--effort E] [--max-turns N]

The request is a `dwitbuk/eyes-request@1` packet (late eyes: findings), or a `chongdae/request@1` with stage `verify` (the eyes
placed before a gate: a `dwitbuk/review@1` verdict). The reader is the host's model: it gets the packet on stdin, may Read files
under the target, and must answer with one JSON object whose findings quote the record and the tree. dwitbuk validates on consume;
chongdae reads the verdict.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dwitbuk import EYES_SCHEMA, REVIEW_SCHEMA, verify_packet  # noqa: E402

PROMPT = ("This is a dwitbuk late-eyes request. Change no files. Follow the packet's `instructions` exactly. "
          "Read a file under `target` when the diff is not enough. Output one JSON object only, no prose, no code fence.\n")


def claude(packet, schema, args):
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose", "--no-session-persistence",
           "--setting-sources", "", "--strict-mcp-config", "--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob",
           "--max-turns", str(args.max_turns), "--json-schema", json.dumps(schema), "--add-dir", packet["target"]]
    if args.model:
        cmd += ["--model", args.model]
    if args.effort:
        cmd += ["--effort", args.effort]
    done = subprocess.run(cmd, input=(PROMPT + json.dumps(packet, ensure_ascii=False)).encode("utf-8"), capture_output=True,
                          cwd=packet["target"], env=dict(os.environ, CLAUDE_CODE_DISABLE_AUTO_MEMORY="1", AGENT_WORKER="1"))
    stdout = done.stdout.decode("utf-8", "replace")
    worker = worker_record(stdout, args.response, "claude-code", args.model)
    if done.returncode:
        raise SystemExit("claude exited %d: %s" % (done.returncode, done.stderr.decode("utf-8", "replace")[-500:]))
    result = None
    for line in stdout.split("\n"):
        if line.strip():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("type") == "result":
                result = event
    if not result or result.get("is_error"):
        raise SystemExit("claude: %s" % ((result or {}).get("subtype") or "no result event"))
    out = result.get("structured_output")
    out = out if out is not None else json.loads(result["result"].strip())
    out["worker"] = worker
    return out


def worker_record(stdout_text, response_path, host, model=None, stderr_text=None):
    """Who did this call, from the host's own account of the session — model, turns, cost — with the whole stream kept next
    to the response as `<response>.transcript.jsonl`. The runner copies this into `performed_by`; an answer whose procedure is
    not on disk cannot be audited (a verdict of "accept, no findings" says nothing about what was read).
    Claude Code says it in its stream (`init`: model; `result`: turns, cost, session). Codex says it in the header it prints
    on stderr (`model:`, `session id:`, `reasoning effort:`); its stream is `--json` items on stdout."""
    rec = {"host": host, "model": model}
    if host == "codex":
        # `--json` gives the item stream and the thread id, not the header; the model is in the rollout Codex keeps for
        # that thread (~/.codex/sessions/**/rollout-*-<thread id>.jsonl, `turn_context.model`)
        m = re.search(r'"thread_id":\s*"([^"]+)"', stdout_text or "")
        if m:
            rec["session"] = m.group(1)
            home = os.environ.get("HUNSU_CODEX_DIR") or os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
            for dirpath, _, files in os.walk(os.path.join(home, "sessions")):
                for f in files:
                    if f.endswith(m.group(1) + ".jsonl"):
                        with open(os.path.join(dirpath, f), encoding="utf-8", errors="replace") as fh:
                            for line in fh:
                                mm = re.search(r'"turn_context".*?"model":\s*"([^"]+)"', line)
                                if mm:
                                    rec["model"] = rec["model"] or mm.group(1)
                                    ee = re.search(r'"effort":\s*"([^"]+)"', line)
                                    if ee:
                                        rec["effort"] = ee.group(1)
                                    break
        for key, name in (("model", "model"), ("session id", "session"), ("reasoning effort", "effort")):   # the header, when a host prints one
            mh = re.search(r"^%s:\s*(.+?)\s*$" % re.escape(key), stderr_text or "", re.M)
            if mh and not rec.get(name):
                rec[name] = mh.group(1)
        kept = "".join(x for x in (stderr_text, stdout_text) if x)
        if kept:
            path = re.sub(r"\.json$", "", response_path) + ".transcript.jsonl"
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(kept if kept.endswith("\n") else kept + "\n")
            rec["transcript"] = os.path.basename(path)
        return rec
    if stdout_text is None:
        return rec
    for line in stdout_text.split("\n"):
        try:
            event = json.loads(line) if line.strip() else None
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            rec["model"] = event.get("model") or model
        elif event.get("type") == "result":
            rec["turns"], rec["cost_usd"], rec["session"] = event.get("num_turns"), event.get("total_cost_usd"), event.get("session_id")
    path = re.sub(r"\.json$", "", response_path) + ".transcript.jsonl"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(stdout_text if stdout_text.endswith("\n") else stdout_text + "\n")
    rec["transcript"] = os.path.basename(path)
    return rec


def codex(packet, schema_doc, args):
    schema = Path(args.response).with_suffix(".schema.json")
    schema.write_text(json.dumps(schema_doc), encoding="utf-8")
    last = Path(args.response).with_suffix(".last.txt")   # codex's raw last message; the response file is written once, whole, by main
    cmd = [shutil.which("codex") or "codex", "exec", "--json", "-C", packet["target"], "-s", os.environ.get("AGENT_CODEX_SANDBOX", "read-only"), "--skip-git-repo-check", "--output-schema", str(schema), "-o", str(last)]   # no turn budget on Codex: `codex exec` has no turn limit to give (unknown -c keys are accepted silently, so none is pretended); the session ends on its own
    if args.model:
        cmd += ["-m", args.model]
    if args.effort:
        cmd += ["-c", 'model_reasoning_effort="%s"' % args.effort]
    done = subprocess.run(cmd, input=(PROMPT + json.dumps(packet, ensure_ascii=False)).encode("utf-8"), capture_output=True, env=dict(os.environ, AGENT_WORKER="1"))
    if done.returncode:
        raise SystemExit("codex exited %d: %s" % (done.returncode, done.stderr.decode("utf-8", "replace")[-500:]))
    out = json.loads(last.read_text(encoding="utf-8"))
    out["worker"] = worker_record(done.stdout.decode("utf-8", "replace"), args.response, "codex", args.model, done.stderr.decode("utf-8", "replace"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--request", required=True)
    ap.add_argument("--response", required=True)
    ap.add_argument("--host", choices=["claude", "codex"], default="claude")
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default=None)
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--prompt-only", action="store_true", help="print the prompt this call would send and exit — for a session that dispatches the host's own subagent (a `native:` provider) instead of this worker")
    args = ap.parse_args()
    packet = json.loads(Path(args.request).read_text(encoding="utf-8"))
    verify = packet.get("artifact-type") == "chongdae/request@1" and packet.get("stage") == "verify"
    if verify:
        packet = verify_packet(packet)
    elif packet.get("artifact-type") != "dwitbuk/eyes-request@1":
        raise SystemExit("not a dwitbuk eyes request or a chongdae verify request: %s" % args.request)
    schema = REVIEW_SCHEMA if verify else EYES_SCHEMA
    if args.prompt_only:
        print(PROMPT + json.dumps(packet, ensure_ascii=False) + "\n\n# Answer\n\nYour whole final message is one JSON object, nothing else, matching this schema:\n" + json.dumps(schema))
        return 0
    try:
        out = (claude if args.host == "claude" else codex)(packet, schema, args)
    except SystemExit as err:
        if not verify:
            raise
        out = {"verdict": None, "findings": [], "summary": str(err)}   # chongdae stops on a missing verdict; it never treats silence as accept
    if verify:
        # the verifier's own rule, enforced here too: a reject without a finding quoted from both sides is not a reject
        out["findings"] = [f for f in out.get("findings", []) if all(str(f.get(k, "")).strip() for k in ("record_quote", "tree_quote", "why"))]
        if out.get("verdict") == "reject" and not out["findings"]:
            out["verdict"], out["summary"] = "accept", "rejected without a quoted finding; counted as accept"
        out = {"artifact-type": "dwitbuk/review@1", **out}
    Path(args.response).parent.mkdir(parents=True, exist_ok=True)
    with open(args.response + ".tmp", "w", encoding="utf-8", newline="\n") as fh:   # LF on every host; the response is diffed and fingerprinted
        fh.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    os.replace(args.response + ".tmp", args.response)   # whole or absent: the runner polls for this file
    print("response -> %s" % args.response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
