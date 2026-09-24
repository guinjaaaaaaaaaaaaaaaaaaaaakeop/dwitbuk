"""Stop hook — the eyes placed by the environment: when a session tries to end, read what it changed.

On only when the project says so (hunsu.json `settings: {"dwitbuk": {"stop-eyes": true}}`, read where it is written; a lock
that carries it, from before, still counts) — a model
call per stop is the team's decision, not the plugin's. Then: nothing dirty -> exit 0; else pack the dirty files as a diff, the plan
(or nothing) as the contract, lens `fresh`, run the eyes worker, and if it finds anything, refuse the stop (exit 2) with the findings
on stderr — the session reads them and answers before it ends. Findings also land in the latest review when there is one.
A second stop in the same turn (`stop_hook_active`) is allowed through: the eyes speak once. Scratch goes to `.dwitbuk/` (not committed).
Inside a worker session (AGENT_WORKER=1 — the eyes, a judge, a builder are host sessions too, and the host runs the project's hooks
in them) the hook does nothing: otherwise the eyes' session would stop, fire this hook, and spawn the eyes again without end.
"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import dwitbuk  # noqa: E402


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if payload.get("stop_hook_active") or os.environ.get("AGENT_WORKER"):
        return 0   # the second stop of a turn, or a worker session (the eyes, a judge, a builder): the eyes speak once, and never inside themselves
    cwd = payload.get("cwd") or os.getcwd()
    # a product's settings are read from the manifest, where a person writes them: a switch works as soon as it is written,
    # also while a working source is tried with `hunsu dev` (when `hunsu lock` rightly refuses)
    # (hunsu.json, this machine's overlay in hunsu.local.json on top; a lock that carries it, from before, still counts)
    mine = lambda doc: ((doc.get("settings") or {}).get("dwitbuk") or {})
    conf = {**mine(dwitbuk.load(os.path.join(cwd, "hunsu.lock.json"))), **mine(dwitbuk.load(os.path.join(cwd, "hunsu.json"))),
            **mine(dwitbuk.load(os.path.join(cwd, "hunsu.local.json")))}
    if not conf.get("stop-eyes"):
        return 0
    dirty = [l[3:].strip().replace("\\", "/") for l in (dwitbuk.git(cwd, "status", "--porcelain", "--untracked-files=all", "--", ".") or "").splitlines() if len(l) > 3]
    prefix = (dwitbuk.git(cwd, "rev-parse", "--show-prefix") or "").strip().replace("\\", "/")
    dirty = [p[len(prefix):] if prefix and p.startswith(prefix) else p for p in dirty]
    left_out = tuple(p for p in dwitbuk.record_paths(cwd) if p != "mangsang/")   # records, machine state, the environment — and this hook's own scratch; mangsang/ relations stay in: a confirmed quote is a claim about the tree
    dirty = [p for p in dirty if not p.startswith(left_out) and not p.endswith(".local.json")]
    if not dirty:
        return 0
    plan_path = os.path.join(cwd, "plan", "PLAN.md")
    request = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": os.path.abspath(cwd).replace(os.sep, "/"), "task": "session",
               "brief": "what this session changed, read at its end", "touched": dirty,
               "contract": {"plan": io.open(plan_path, encoding="utf-8").read()[:40000]} if os.path.exists(plan_path) else {}, "checks": [], "tests": []}
    packet = dwitbuk.verify_packet(request)
    packet["lens"] = "fresh"
    packet["diff_leaves_out"] = list(left_out)
    packet["instructions"] = ("You are the eyes at the end of a session. Read what it changed (the diff) against the plan if there is one. " + dwitbuk.LENSES["fresh"] +
                              " Report contradictions with a quote from each side, anomalies with a tree quote. No quote, no finding. "
                              "Paths under `diff_leaves_out` are left out of `touched` on purpose (records, machine state, the environment); their absence is not a finding. Change no files.")
    folder = os.path.join(cwd, ".dwitbuk")   # this machine's, like .mangsang/: not committed
    os.makedirs(folder, exist_ok=True)
    ignore = os.path.join(cwd, ".gitignore")
    lines = io.open(ignore, encoding="utf-8").read().split("\n") if os.path.exists(ignore) else []
    if ".dwitbuk/" not in lines:
        io.open(ignore, "a", encoding="utf-8", newline="\n").write(("" if not lines or lines[-1] == "" else "\n") + ".dwitbuk/\n")
    dwitbuk.save(os.path.join(folder, "eyes-request.json"), {**packet, "artifact-type": "dwitbuk/eyes-request@1"})
    import time
    with io.open(os.path.join(folder, "stop.log"), "a", encoding="utf-8", newline="\n") as log:
        log.write("%s start touched=%s pid=%d\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dirty, os.getpid()))   # a line before the eyes: if the host cuts the hook off, this is what remains
    done = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "eyes_worker.py"), "--request", os.path.join(folder, "eyes-request.json"),
                           "--response", os.path.join(folder, "eyes-response.json"), "--effort", os.environ.get("DWITBUK_STOP_EFFORT", "medium")],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    with io.open(os.path.join(folder, "stop.log"), "a", encoding="utf-8", newline="\n") as log:
        log.write("%s end rc=%d\n%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), done.returncode, (done.stderr or done.stdout).strip()[-600:]))
    if done.returncode:
        print("dwitbuk stop-eyes: the eyes did not answer (%s) — nothing decided; see .dwitbuk/stop.log" % (done.stderr or done.stdout).strip()[-200:], file=sys.stderr)
        return 0
    resp = dwitbuk.load(os.path.join(folder, "eyes-response.json"))
    findings = [f for f in resp.get("findings", []) if str(f.get("tree_quote", "")).strip() and str(f.get("why", "")).strip()
                and (f.get("kind") == "anomaly" or str(f.get("record_quote", "")).strip())]
    if not findings:
        return 0
    if dwitbuk.reviews(cwd):
        class A: dir, by = folder, "stop-eyes"
        try:
            dwitbuk.cmd_eyes(type("Args", (), {"target": cwd, "mode": "consume", "dir": folder, "by": "stop-eyes"})())
        except SystemExit:
            pass
    lines = ["%s @ %s: %s — tree: \u201c%s\u201d" % (f["kind"], f.get("where", ""), f["why"], f["tree_quote"][:120]) for f in findings]
    print("dwitbuk stop-eyes: %d finding(s) on what this session changed — address each (fix, or say why not) before ending:\n- " % len(findings) + "\n- ".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
