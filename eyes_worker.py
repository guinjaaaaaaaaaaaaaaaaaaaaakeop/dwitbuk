"""Runs one eyes request in a fresh, read-only host session and saves the structured answer.

  python eyes_worker.py --request FILE --response FILE [--host claude|codex] [--model M] [--effort E] [--max-turns N]

The request is a `dwitbuk/eyes-request@1` packet (late eyes: findings), or a `chongdae/request@1` with stage `verify` (the eyes
placed before a gate: a `dwitbuk/review@1` verdict). The reader is the host's model: it gets the packet on stdin, may Read files
under the target, and must answer with one JSON object whose findings quote the record and the tree. dwitbuk validates on consume;
chongdae reads the verdict. A verdict carries what the eyes read (`read`, from the session's own stream), and an accept that read
nothing of the tree, or only the diff where the contract names behaviour, says so in `non-claims` — still an accept.
"""
import argparse
import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dwitbuk import EYES_SCHEMA, REVIEW_SCHEMA, documents_or_records, flat, grounded, strings, verify_packet, weigh  # noqa: E402
from hostcall import run_claude, run_codex, claude_answer, worker_record  # noqa: E402  (vendored: the same file in each plugin of this family)

PROMPT = ("This is a dwitbuk late-eyes request. Change no files. Follow the packet's `instructions` exactly. "
          "Read a file under `target` when the diff is not enough. Output one JSON object only, no prose, no code fence.\n")


def claude(packet, schema, args):
    code, stdout, stderr = run_claude(PROMPT + json.dumps(packet, ensure_ascii=False), schema, cwd=packet["target"], add_dirs=[packet["target"]], model=args.model, effort=args.effort, max_turns=args.max_turns)
    worker = worker_record(stdout, args.response, "claude-code", args.model)
    if code:
        raise SystemExit("claude exited %d: %s" % (code, stderr[-500:]))
    out, why = claude_answer(stdout)
    if out is None:
        raise SystemExit(why)
    out["worker"] = worker
    return out


def codex(packet, schema_doc, args):
    code, stdout, stderr, last = run_codex(PROMPT + json.dumps(packet, ensure_ascii=False), schema_doc, packet["target"], model=args.model, effort=args.effort, beside=args.response)
    if code:
        raise SystemExit("codex exited %d: %s" % (code, stderr[-500:]))
    out = json.loads(last or "")
    out["worker"] = worker_record(stdout, args.response, "codex", args.model, stderr)
    return out


SHELL_WRAPPER = re.compile(r"^/bin/(?:ba|z)?sh -l?c (.*)$", re.S)   # Codex runs each command as the argument of a login shell
DIFF_ONLY = re.compile(r"^git(?:\s+-\S+(?:\s+\S+)?)*\s+(?:diff|status|show|log)\b")   # what the packet already holds: the change, not the tree
SAYS_NOTHING = re.compile(r"^(?:printf|echo|cd|true|pwd)\b")


def is_verdict(text):
    """A message that is an answer (a JSON object with a verdict or findings), not a word on the way ("let me read …")."""
    try:
        doc = json.loads(str(text or "").strip())
    except ValueError:
        return False
    return isinstance(doc, dict) and ("verdict" in doc or "findings" in doc)


def eyes_read(transcript):
    """What the eyes read, from the stream the worker kept (`<response>.transcript.jsonl`): the files a Claude session opened
    (Read, Grep, Glob) and the commands a Codex session ran, each with its exit code — and whether its first answer came
    before anything was read. None when there is no stream: what was read is then not on record."""
    if not transcript or not os.path.exists(transcript):
        return None
    files, commands, answered_first = [], [], None
    for line in open(transcript, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line) if line.strip() else None
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        it = d.get("item") or {}
        if d.get("type") == "item.completed" and it.get("type") == "command_execution":
            cmd = it.get("command", "")
            m = SHELL_WRAPPER.match(cmd)
            if m:
                try:
                    cmd = shlex.split(m.group(1))[0]
                except ValueError:
                    cmd = m.group(1)
            commands.append({"command": cmd[:300], "exit": it.get("exit_code")})
        elif d.get("type") == "item.completed" and it.get("type") == "agent_message" and answered_first is None and is_verdict(it.get("text")):
            answered_first = not files and not commands
        elif d.get("type") == "assistant":
            for c in (d.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    inp = c.get("input") or {}
                    if c.get("name") in ("Read", "Grep", "Glob"):
                        files.append("%s %s" % (c["name"], inp.get("file_path") or inp.get("path") or inp.get("pattern") or ""))
                    elif c.get("name") == "Bash":
                        commands.append({"command": inp.get("command", "")[:300], "exit": None})
                elif isinstance(c, dict) and c.get("type") == "text" and answered_first is None and is_verdict(c.get("text")):
                    answered_first = not files and not commands
    return {"files": files, "commands": commands, **({"answered-before-reading": True} if answered_first else {})}


def beyond_the_diff(command):
    """Whether a command read the tree beyond what the packet's diff already shows: any part of it that is not git's view of
    the change (`git diff`, `status`, `show`, `log`) or an echo."""
    parts = [p.strip() for p in re.split(r"&&|\|\||[;|\n]", command) if p.strip()]
    return any(not DIFF_ONLY.match(p) and not SAYS_NOTHING.match(p) for p in parts)


def unread_accept(read, packet):
    """The non-claim an accept carries when the eyes read nothing of the tree — or only the diff while the contract names
    behaviour in code the diff does not show whole (the slice has tests, or its files are not all documents or records). guin-site run a0ec,
    cache-build: the second verifier answered `accept` first, then ran one `git diff`, then the same verdict — 607 output
    tokens on exactly the input the first verifier rejected — and the record said only "accept". Kept as accept: what was
    read is said, not judged. None when the eyes read the tree."""
    if read is None:
        return "accepted, and what the eyes read is not on record (no transcript of their session)"
    first = " — and gave the verdict before reading anything" if read.get("answered-before-reading") else ""
    ran = [c for c in read["commands"] if c.get("exit") in (0, None)]
    if read["files"] or any(beyond_the_diff(c["command"]) for c in ran):
        return None
    if not ran:
        return "accepted without reading the tree: the eyes opened no file and ran no command — the verdict rests on the packet alone%s" % first
    contract = flat("\n".join(strings(packet.get("contract"))))
    files = list(packet.get("touched") or []) + list(packet.get("touched_since") or [])   # a0ec's request had `touched: []`, the work in `touched_since`
    if contract and (packet.get("tests") or (files and not documents_or_records(files, packet.get("target") or "."))):
        return ("accepted without reading the touched files or the tests: the eyes read the diff only (%s), and the contract names "
                "behaviour the diff alone does not show%s" % ("; ".join("`%s`" % c["command"][:160] for c in ran), first))
    return None


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
        # the verifier's own rule, enforced here too: a reject without a grounded finding (quoted from both sides, or from the
        # tree for an anomaly) is not a reject
        out["findings"] = [f for f in out.get("findings", []) if grounded(f)]
        # and a quote must be where the finding says it is: a sentence of the tests writer's read as the builder's turned a
        # passing build into a reject (guin-site run a0ec) — dropped from the grounds, kept visible under `unfounded`
        out = weigh(out, packet)
        if out.get("verdict") == "reject" and not out["findings"]:
            out["verdict"], out["summary"] = "accept", "rejected without a quoted finding; counted as accept"
        if out.get("verdict") == "accept" and isinstance(out.get("worker"), dict):
            # what the eyes actually read, beside the verdict: an accept is auditable only if that is on record
            read = eyes_read(os.path.join(os.path.dirname(os.path.abspath(args.response)), out["worker"]["transcript"])
                             if out["worker"].get("transcript") else None)
            if read is not None:
                out["read"] = read
            said = unread_accept(read, packet)
            if said:
                out["non-claims"] = list(out.get("non-claims") or []) + [said]
        out = {"artifact-type": "dwitbuk/review@1", **out}
    Path(args.response).parent.mkdir(parents=True, exist_ok=True)
    with open(args.response + ".tmp", "w", encoding="utf-8", newline="\n") as fh:   # LF on every host; the response is diffed and fingerprinted
        fh.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    os.replace(args.response + ".tmp", args.response)   # whole or absent: the runner polls for this file
    print("response -> %s" % args.response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
