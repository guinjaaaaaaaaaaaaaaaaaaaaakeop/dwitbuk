"""SessionStart hook — one fact, when there is one: how many objections of the latest review nobody has disposed of.

The reviewer is placed by the runner when a run ends (chongdae's `reviewer` role, declared in hunsu.json), so reviews now
accumulate without anyone asking for them; what still needs a person is the disposition. This line says so at the start of
a session — a count and the review's id, never an instruction on what to decide. Nothing open, no reviews, or a worker
session (AGENT_WORKER=1): silent. Never blocks; keeps machine-local session notification state. Under hunsu's probe (HUNSU_SURVEY=1, an empty temporary
project): its standing text — what the line says in any state, as a template with no review id or count — since the empty
project's answer was nothing and a judge reading it learned nothing of what dwitbuk tells a session.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import dwitbuk  # noqa: E402


STANDING = ("dwitbuk: when objections are open, the full line `dwitbuk: N undisposed objection(s) in <review> (<kind> N, …)` "
            "is said once per session; later starts of the same "
            "session while nothing changed get a short line without the count. `follow` lists them; a person disposes each "
            "with `dispose`; an agent never disposes one on its own; nothing open, no reviews, or a worker session: silent.")


def open_objections(cwd):
    """(review id, [findings]) of the latest review's objections no disposal answers — the same set `follow` lists; (None, [])
    when there is nothing to say."""
    rid, open_ = dwitbuk.open_charges(cwd)
    return rid, [f for _, f in open_]


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if os.environ.get("AGENT_WORKER"):
        return 0
    if os.environ.get("HUNSU_SURVEY"):   # hunsu's probe: what the line says, not what an empty project holds
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": STANDING}}))
        return 0
    cwd = payload.get("cwd") or os.getcwd()
    try:
        rid, open_ = open_objections(cwd)
    except (OSError, ValueError):
        return 0   # a review file this hook cannot read is `review`'s problem, not a session start's
    if not open_:
        return 0
    engine = os.path.join(os.path.dirname(HERE), "dwitbuk.py").replace(os.sep, "/")
    msg = ('dwitbuk: %d undisposed objection(s) in %s (%s) — `python3 "%s" follow --target .` lists them; a person disposes each: '
           '`python3 "%s" dispose %s/<n> --as accepted|dismissed --why "<their words>" --by <name> --target .`; an agent never disposes one on its own.'
           % (len(dwitbuk.distinct(open_)), rid, dwitbuk.count_text(open_), engine, engine, rid))
    session = payload.get("session_id")
    if session:
        path = os.path.join(cwd, ".dwitbuk", "session-start.json")
        digest = hashlib.sha256(json.dumps(sorted([list(dwitbuk.charge(f)) for f in open_])).encode()).hexdigest()
        current = {"review": rid, "open": digest}
        try:
            try:
                with open(path, encoding="utf-8") as stream:
                    state = json.load(stream)
                sessions = state["sessions"]
                if not isinstance(sessions, dict) or any(not isinstance(v, dict) for v in sessions.values()):
                    raise ValueError("invalid session state")
            except (OSError, ValueError, TypeError, KeyError):
                state = {"sessions": {}}
            sessions = state["sessions"]
            same = sessions.get(session) == current
            if not same:
                sessions.pop(session, None)
                sessions[session] = current
                while len(sessions) > 64:
                    del sessions[next(iter(sessions))]
            dwitbuk.save(path, state)
            if same:
                msg = ("dwitbuk: %s's undisposed objection(s) are as this session was told — unchanged; "
                       '`python3 "%s" follow --target .` lists them, and a person disposes each.' % (rid, engine))
        except (OSError, ValueError, TypeError, KeyError):
            pass
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
