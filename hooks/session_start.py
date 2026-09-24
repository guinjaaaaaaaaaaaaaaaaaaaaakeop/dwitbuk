"""SessionStart hook — one fact, when there is one: how many objections of the latest review nobody has disposed of.

The reviewer is placed by the runner when a run ends (chongdae's `reviewer` role, declared in hunsu.json), so reviews now
accumulate without anyone asking for them; what still needs a person is the disposition. This line says so at the start of
a session — a count and the review's id, never an instruction on what to decide. Nothing open, no reviews, or a worker
session (AGENT_WORKER=1): silent. Never blocks, never writes.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import dwitbuk  # noqa: E402


def open_objections(cwd):
    """(review id, [findings]) of the latest review's undisposed objections; (None, []) when there is nothing to say."""
    latest = dwitbuk.reviews(cwd)[-1:]
    if not latest:
        return None, []
    r = latest[0]
    return r.get("id"), [f for f in r.get("findings", []) if not f.get("disposition") and dwitbuk.layer(f) == "objection"]


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if os.environ.get("AGENT_WORKER"):
        return 0
    cwd = payload.get("cwd") or os.getcwd()
    try:
        rid, open_ = open_objections(cwd)
    except (OSError, ValueError):
        return 0   # a review file this hook cannot read is `review`'s problem, not a session start's
    if not open_:
        return 0
    kinds = {}
    for f in open_:
        kinds[f.get("kind", "?")] = kinds.get(f.get("kind", "?"), 0) + 1
    engine = os.path.join(os.path.dirname(HERE), "dwitbuk.py").replace(os.sep, "/")
    msg = ("dwitbuk: %d undisposed objection(s) in %s (%s) — `python3 \"%s\" follow --target .` lists them; `dispose <review>/<n> --as accepted|dismissed --why ... --by NAME` answers one."
           % (len(open_), rid, ", ".join("%s %d" % kv for kv in sorted(kinds.items())), engine))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
