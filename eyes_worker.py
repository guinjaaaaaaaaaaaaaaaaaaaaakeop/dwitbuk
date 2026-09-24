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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dwitbuk import EYES_SCHEMA, REVIEW_SCHEMA, verify_packet  # noqa: E402
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
