"""Self-check for dwitbuk. A temp git project with hand-written run records; every kind of finding fires once, dispositions carry.

  python test_dwitbuk.py
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dwitbuk  # noqa: E402
import eyes_worker as w  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, indent=1))


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = dwitbuk.main(list(argv))
        except SystemExit as err:
            code = err.code if isinstance(err.code, int) else 1
            out.write(str(err) + "\n")
    return code, out.getvalue()


def git(cwd, *a):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env).stdout.strip()


class Project:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="dwitbuk-test-")
        git(self.dir, "init", "-q", "-b", "main")
        write(os.path.join(self.dir, "a.py"), "x = 1\n")
        git(self.dir, "add", "-A"); git(self.dir, "commit", "-q", "-m", "base")
        self.base = git(self.dir, "rev-parse", "HEAD")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        shutil.rmtree(self.dir, ignore_errors=True)

    def reporter(self, findings, name="fake"):
        """A reporter the lock declares: prints the given dwitbuk/findings@1 (recorded from chongdae's real `report`, trimmed)."""
        script = os.path.join(self.dir, name + ".py")
        write(script, "import json, sys\nprint(json.dumps(%s))\n" % json.dumps({"artifact-type": "dwitbuk/findings@1", "source": name, "findings": findings}))
        lock = dwitbuk.load(os.path.join(self.dir, "hunsu.lock.json"))
        lock.setdefault("reporters", {})[name] = [sys.executable, script, "--since", "{since}"]
        write(os.path.join(self.dir, "hunsu.lock.json"), lock)

    def run_record(self, rid, tasks, non_claims=(), plan_extra=None):
        plan = {"artifact-type": "chongdae/plan@1", "goal": rid, "tasks": [{"id": t, "role": "r", "checks": [["x"]]} for t in tasks], **(plan_extra or {})}
        state = {"status": "complete", "tasks": tasks, "non-claims": list(non_claims)}
        write(os.path.join(self.dir, ".chongdae", rid, "plan.json"), plan)
        write(os.path.join(self.dir, ".chongdae", rid, "state.json"), state)

    def latest(self):
        return dwitbuk.reviews(self.dir)[-1]


def kinds(review):
    out = {}
    for f in review["findings"]:
        out[f["kind"]] = out.get(f["kind"], 0) + 1
    return out



class Skip(Exception):
    """Raised by a test that cannot run on this host; the runner reports it as SKIP, never as PASS."""


def stream(*events):
    return "".join(json.dumps(e) + "\n" for e in events)

def test_review_collects_typed_findings_from_the_locks_reporters_and_groups_by_kind():
    with Project() as pj:
        # no reporters declared: the review says so, and computes nothing from any product's directory
        pj.run_record("run-20260101-000001-aaaa", {"S1": {"status": "done", "confirmed": {"delegated": "away"}}})
        code, out = run("review", "--since", pj.base, "--target", pj.dir)
        assert code == 0 and kinds(pj.latest()) == {"no-reporters": 1}, kinds(pj.latest())
        # two reporters (recorded from chongdae `report` and hunsu `check --findings`), plus one that does not answer in the type
        pj.reporter([{"kind": "outside-run", "where": "b.py", "files": ["b.py"], "text": "changed since x; no completed run recorded touching it"},
                     {"kind": "outside-run", "where": "hunsu.json", "files": ["hunsu.json"], "text": "changed since x; no completed run recorded touching it"},
                     {"kind": "unattributed", "where": "run-20260101-000002-bbbb/S2", "text": "these runs completed without recording touched files"},
                     {"kind": "delegated", "where": "run-20260101-000002-bbbb/S2", "text": "gate passed by delegation (no verifier): owner was away"},
                     {"kind": "delegated", "where": "run-20260101-000002-bbbb/S2", "text": "provider decisions (1) passed by delegation: trivial"},
                     {"kind": "non-claim", "where": "run-20260101-000001-aaaa", "text": "S1: x untested"},
                     {"kind": "non-claim", "where": "run-20260101-000002-bbbb", "text": "S2 (provider): x untested"},
                     {"kind": "non-claim", "where": "run-20260101-000002-bbbb", "text": "S2 (provider): y untested"}], "chongdae")
        pj.reporter([{"kind": "unreviewed", "where": "hunsu.json resolutions['reviewing']", "text": "applied from the judge's proposal, marked reviewed: false"}], "hunsu")
        write(os.path.join(pj.dir, "broken.py"), "print('not json')\n")
        lock = dwitbuk.load(os.path.join(pj.dir, "hunsu.lock.json"))
        lock["reporters"]["broken"] = [sys.executable, os.path.join(pj.dir, "broken.py")]
        write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
        import time; time.sleep(1.1)
        code, out = run("review", "--since", pj.base, "--target", pj.dir)
        assert code == 0, out
        r = pj.latest()
        assert sorted(r["reporters"]) == ["broken", "chongdae", "hunsu"]
        k = kinds(r)
        assert k == {"outside-run": 1, "unattributed": 1, "delegated": 2, "non-claim": 2, "unreviewed": 1, "reporter-failed": 1, "undisposed": 1, "review-debt": 1}, k
        outside = next(f for f in r["findings"] if f["kind"] == "outside-run")
        assert outside["files"] == ["b.py", "hunsu.json"], outside
        assert next(f for f in r["findings"] if f["kind"] == "unreviewed")["source"] == "hunsu"
        assert "gave no dwitbuk/findings@1" in next(f["text"] for f in r["findings"] if f["kind"] == "reporter-failed")
        nc = [f["text"] for f in r["findings"] if f["kind"] == "non-claim"]
        assert any("x untested  [x2]" in t for t in nc) and any(t.startswith("y untested") for t in nc), nc
        assert next(f for f in r["findings"] if f["kind"] == "undisposed")["text"].startswith("no-reporters")


def load_review(pj):
    return json.load(open(os.path.join(pj.dir, "reviews", pj.latest()["id"] + ".json"), encoding="utf-8"))


def save_review(pj, r):
    json.dump(r, open(os.path.join(pj.dir, "reviews", r["id"] + ".json"), "w", encoding="utf-8"))


def test_dispositions_carry_and_vanished_findings_become_undisposed():
    with Project() as pj:
        pj.reporter([{"kind": "outside-run", "where": "b.py", "files": ["b.py"], "text": "changed; no run"},
                     {"kind": "unattributed", "where": "run-1/S1", "text": "no touched"},
                     {"kind": "delegated", "where": "run-1/S1", "text": "gate passed by delegation (no verifier): away"}])
        run("review", "--since", pj.base, "--target", pj.dir)
        first = pj.latest()
        assert kinds(first) == {"outside-run": 1, "unattributed": 1, "delegated": 1}, kinds(first)
        # delegated is an observation — a fact of the record; disposing it is refused
        idx = next(i for i, f in enumerate(first["findings"]) if f["kind"] == "delegated")
        assert first["findings"][idx]["layer"] == "observation", first["findings"][idx]
        code, out = run("dispose", "%s/%d" % (first["id"], idx), "--as", "accepted", "--why", "fine", "--by", "kim", "--target", pj.dir)
        assert code != 0 and "an observation is a fact, not a charge" in out, out
        assert run("dispose", "%s/99" % first["id"], "--as", "accepted", "--why", "x", "--target", pj.dir)[0] != 0
        # nobody read the unattributed one: a disposition by delegation is recorded as such (no person's name), like a gate
        u = next(i for i, f in enumerate(first["findings"]) if f["kind"] == "unattributed")
        assert run("dispose", "%s/%d" % (first["id"], u), "--as", "dismissed", "--target", pj.dir)[0] != 0, "one of --why / --delegated is required"
        assert run("dispose", "%s/%d" % (first["id"], u), "--as", "dismissed", "--why", "x", "--delegated", "y", "--target", pj.dir)[0] != 0, "not both"
        code, out = run("dispose", "%s/%d" % (first["id"], u), "--as", "dismissed", "--delegated", "the person was away; the run is a test", "--target", pj.dir)
        du = pj.latest()["findings"][u]["disposition"]
        assert code == 0 and "(delegated)" in out and du["as"] == "dismissed" and du["delegated"] == "the person was away; the run is a test" and du["by"] is None
        # the disposal carries the charge it answers: the finding's own text and where, copied at disposal time
        assert du["finding_text"] == first["findings"][u]["text"] and du["where"] == first["findings"][u]["where"], du
        r = load_review(pj); r["findings"][u].pop("disposition"); save_review(pj, r)
        # a person disposes the outside-run objection; the observation is not debt and follow does not count it
        b = next(i for i, f in enumerate(first["findings"]) if f["kind"] == "outside-run")
        assert run("dispose", "%s/%d" % (first["id"], b), "--as", "accepted", "--why", "fine", "--by", "kim", "--target", pj.dir)[0] == 0
        code, out = run("follow", "--target", pj.dir)
        assert code == 1 and "undisposed findings: 1" in out and "delegated" not in out, out
        # b.py goes back to how it was: the outside-run finding stops recurring — its disposition was recorded, so no carry
        pj.reporter([{"kind": "unattributed", "where": "run-1/S1", "text": "no touched"},
                     {"kind": "delegated", "where": "run-1/S1", "text": "gate passed by delegation (no verifier): away"}])
        import time; time.sleep(1.1)
        run("review", "--target", pj.dir)
        second = pj.latest()
        assert second["id"] != first["id"] and second["since"] == first["head"]
        by_kind = {f["kind"]: f for f in second["findings"]}
        assert by_kind["unattributed"]["first-seen"] == first["id"] and by_kind["delegated"]["layer"] == "observation"
        assert "outside-run" not in by_kind and "undisposed" not in by_kind, by_kind.keys()
        # the previous review still held an open objection (unattributed): the new review accuses itself of the debt
        assert by_kind["review-debt"]["layer"] == "objection" and first["id"] in by_kind["review-debt"]["text"] and "1 undisposed objection" in by_kind["review-debt"]["text"], by_kind["review-debt"]
        code, out = run("follow", "--target", pj.dir)
        assert code == 1 and "undisposed findings: 2" in out, out   # unattributed + review-debt; the observation is not counted
        # the third review: the debt is recomputed (it names the second review now), never carried as undisposed
        time.sleep(1.1)
        run("review", "--target", pj.dir)
        third = pj.latest()
        assert sum(f["kind"] == "undisposed" for f in third["findings"]) == 0, [f for f in third["findings"] if f["kind"] == "undisposed"]
        debt = [f for f in third["findings"] if f["kind"] == "review-debt"]
        assert len(debt) == 1 and second["id"] in debt[0]["text"] and "2 undisposed objection" in debt[0]["text"], debt


def test_disposal_is_machine_judgeable_quote_stored_and_quoted_findings_warn_without_one():
    with Project() as pj:
        pj.reporter([{"kind": "unattributed", "where": "run-1/S1", "text": "no touched"}])
        run("review", "--since", pj.base, "--target", pj.dir)
        r = load_review(pj)
        # a quote-grounded finding, as `eyes consume` writes it (kind contradiction/anomaly)
        r["findings"].append({"kind": "contradiction", "where": "run-1/S1 vs a.py", "layer": "objection",
                              "text": "record-vs-tree: says done — record: \u201cdone\u201d — tree: \u201cTODO\u201d"})
        save_review(pj, r)
        rid, ci = r["id"], len(r["findings"]) - 1
        # disposing a quoted finding without --quote: warns, does not refuse
        code, out = run("dispose", "%s/%d" % (rid, ci), "--as", "dismissed", "--why", "the TODO is in a comment", "--by", "kim", "--target", pj.dir)
        assert code == 0 and "grounded in quotes" in out and "harder to audit" in out, out
        # with --quote: stored verbatim, no warning
        r = load_review(pj); r["findings"][ci].pop("disposition"); save_review(pj, r)
        code, out = run("dispose", "%s/%d" % (rid, ci), "--as", "dismissed", "--why", "the TODO is in a comment", "--by", "kim",
                        "--quote", "# TODO(kim): rename later", "--target", pj.dir)
        assert code == 0 and "grounded in quotes" not in out, out
        d = pj.latest()["findings"][ci]["disposition"]
        assert d["quote"] == "# TODO(kim): rename later" and d["finding_text"] == r["findings"][ci]["text"] and d["where"] == "run-1/S1 vs a.py", d
        # an unquoted finding disposed without --quote: no warning — a disposal may be a pure decision
        ui = next(i for i, f in enumerate(r["findings"]) if f["kind"] == "unattributed")
        code, out = run("dispose", "%s/%d" % (rid, ui), "--as", "accepted", "--why", "known gap", "--by", "kim", "--target", pj.dir)
        assert code == 0 and "grounded in quotes" not in out, out
        d = pj.latest()["findings"][ui]["disposition"]
        assert d["finding_text"] == "no touched" and d["where"] == "run-1/S1" and "quote" not in d, d


def test_layers_are_fail_closed_and_a_reporter_may_mark_its_own_kind_informational():
    with Project() as pj:
        pj.reporter([{"kind": "delegated", "where": "run-1/S1", "text": "re-confirmed by delegation"},
                     {"kind": "totally-new-kind", "where": "x", "text": "nobody classified this"},
                     {"kind": "fyi", "where": "y", "text": "informational, says the reporter", "layer": "observation"},
                     {"kind": "stale", "where": "z", "text": "an objection kind stays one even if a reporter says otherwise? no — trust it", "layer": "objection"}])
        run("review", "--since", pj.base, "--target", pj.dir)
        r = pj.latest()
        by_kind = {f["kind"]: f for f in r["findings"]}
        assert by_kind["delegated"]["layer"] == "observation"
        assert by_kind["totally-new-kind"]["layer"] == "objection", "unknown kinds fail closed"
        assert by_kind["fyi"]["layer"] == "observation", "a reporter's explicit layer is trusted"
        assert by_kind["stale"]["layer"] == "objection"
        code, out = run("follow", "--target", pj.dir)
        assert code == 1 and "undisposed findings: 2" in out and "fyi" not in out and "delegated" not in out, out
        fyi = next(i for i, f in enumerate(r["findings"]) if f["kind"] == "fyi")
        code, out = run("dispose", "%s/%d" % (r["id"], fyi), "--as", "accepted", "--why", "x", "--by", "kim", "--target", pj.dir)
        assert code != 0 and "an observation is a fact, not a charge" in out, out


def test_review_debt_does_not_fire_when_the_previous_review_is_clean():
    with Project() as pj:
        pj.reporter([{"kind": "delegated", "where": "run-1/S1", "text": "re-confirmed by delegation"}])
        code, out = run("review", "--since", pj.base, "--target", pj.dir)
        assert kinds(pj.latest()) == {"delegated": 1} and "observations (facts of the record, not disposal debt): 1" in out, out
        assert run("follow", "--target", pj.dir)[0] == 0, "an observation is not debt"
        import time; time.sleep(1.1)
        run("review", "--target", pj.dir)
        assert "review-debt" not in kinds(pj.latest()), kinds(pj.latest())


# Recorded from a real late-eyes run, trimmed: one finding with both quotes, one the reader could not quote.
EYES_RESPONSE = {"findings": [
    {"kind": "record-vs-tree", "where": "run-20260101-000001-aaaa/S1 touched; target root (proposals.json)",
     "record_quote": "\"touched\": [\"a.py\", \"proposals.json\"]", "tree_quote": "Glob **/proposals.json under target: No files found",
     "why": "the record names a touched path the tree does not have"},
    {"kind": "plan-vs-code", "where": "plan/PLAN.md#Q1", "record_quote": "prints one line", "tree_quote": "", "why": "no quote from the tree"},
    {"kind": "style", "where": "a.py", "record_quote": "x", "tree_quote": "y", "why": "not a kind"},
    {"kind": "anomaly", "where": "a.py", "record_quote": "", "tree_quote": "x = 2", "why": "a bare constant nothing reads"}]}


def test_eyes_packet_carries_diff_records_plan_and_open_findings_and_consume_keeps_only_quoted_contradictions():
    with Project() as pj:
        pj.run_record("run-20260101-000001-aaaa", {"S1": {"status": "done", "touched": ["a.py", "proposals.json"], "confirmed": {"by": "kim"}}})
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        write(os.path.join(pj.dir, "plan", "PLAN.md"), "# plan\n\n## Q1\n\nprints one line\n")
        write(os.path.join(pj.dir, "mangsang", "relations", "R-1.json"), {"id": "R-1"})
        out_dir = os.path.join(pj.dir, "eyes")
        assert run("eyes", "consume", "--dir", out_dir, "--target", pj.dir)[0] != 0, "no review yet"
        run("review", "--since", pj.base, "--target", pj.dir)
        code, out = run("eyes", "request", "--out", out_dir, "--since", pj.base, "--lens", "fresh", "--lens", "contract", "--target", pj.dir)
        assert code == 0 and os.path.exists(os.path.join(out_dir, "eyes-fresh-request.json")) and os.path.exists(os.path.join(out_dir, "eyes-contract-request.json")), out
        assert run("eyes", "request", "--out", out_dir, "--lens", "nope", "--target", pj.dir)[0] != 0
        write(os.path.join(pj.dir, "SPEC.md"), "# spec\n\nprints two lines\n")
        code, out = run("eyes", "request", "--out", out_dir, "--since", pj.base, "--contract", "SPEC.md", "--target", pj.dir)
        assert code == 0, out
        packet = json.load(open(os.path.join(out_dir, "eyes-request.json"), encoding="utf-8"))
        assert "prints two lines" in packet["plan"], "a contract document stands in for the plan"
        code, out = run("eyes", "request", "--out", out_dir, "--since", pj.base, "--target", pj.dir)
        packet = json.load(open(os.path.join(out_dir, "eyes-request.json"), encoding="utf-8"))
        assert packet["since"] == pj.base and "+x = 2" in packet["diff"], packet["diff"]
        assert "mangsang/relations/R-1.json" in packet["new_files"] and "plan/PLAN.md" in packet["new_files"], "untracked files are part of the change"
        assert ".chongdae" in packet["diff_leaves_out"] and packet["runs"][0]["tasks"][0]["state"]["touched"] == ["a.py", "proposals.json"]
        assert "prints one line" in packet["plan"] and any(f["kind"] == "no-reporters" for f in packet["open_findings"])
        write(os.path.join(out_dir, "eyes-response.json"), EYES_RESPONSE)
        code, out = run("eyes", "consume", "--dir", out_dir, "--by", "test", "--target", pj.dir)
        assert code == 0 and "2 finding(s) added" in out and "2 rejected" in out, out
        r = pj.latest()
        added = [f for f in r["findings"] if f["kind"] == "contradiction"]
        assert len(added) == 1 and "proposals.json" in added[0]["where"] and "record: " in added[0]["text"] and added[0]["by"] == "test"
        assert any(f["kind"] == "anomaly" and "bare constant" in f["text"] for f in r["findings"])
        # consuming the same answer again adds nothing; the finding carries into the next review like any other
        code, out = run("eyes", "consume", "--dir", out_dir, "--by", "test", "--target", pj.dir)
        assert "0 finding(s) added" in out, out
        import time; time.sleep(1.1)
        run("review", "--target", pj.dir)
        assert any(f["kind"] == "undisposed" and f["text"].startswith("contradiction") for f in pj.latest()["findings"])
        assert any(f["kind"] == "undisposed" and f["text"].startswith("anomaly") for f in pj.latest()["findings"])


def test_verify_packet_carries_contract_touched_diff_and_the_builders_report():
    with Project() as pj:
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        write(os.path.join(pj.dir, "b.py"), "y = 1\n")
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "run": "run-1", "task": "S1", "target": pj.dir,
               "contract": {"Q1": "## Q1\n\nprints one line"}, "checks": [["python", "t.py"]], "tests": ["t.py"],
               "touched": ["a.py", "b.py", ".chongdae/run-1/x.json"], "built": {"summary": "did it", "verified": [{"check": "python t.py", "exit": 0}]}}
        p = dwitbuk.verify_packet(req)
        assert p["mode"] == "verify" and p["touched"] == ["a.py", "b.py"] and "+x = 2" in p["diff"] and "b.py (new file)" in p["diff"]
        assert p["contract"]["Q1"].endswith("prints one line") and p["built"]["summary"] == "did it" and "premise, not a verdict" in p["instructions"]
        assert dwitbuk.REVIEW_SCHEMA["properties"]["verdict"]["enum"] == ["accept", "reject"]


def test_runs_are_read_from_one_file_per_task_and_session_tasks_define_themselves():
    with Project() as pj:
        root = os.path.join(pj.dir, ".chongdae", "run-20260101-000003-cccc")
        write(os.path.join(root, "plan.json"), {"artifact-type": "chongdae/plan@1", "goal": "session", "kind": "session", "tasks": []})
        write(os.path.join(root, "state.json"), {"artifact-type": "chongdae/run@1", "status": "complete"})
        write(os.path.join(root, "tasks", "T1.json"), {"artifact-type": "chongdae/task@1", "status": "done", "touched": ["a.py"], "claimed_by": "alice",
                                                       "def": {"id": "T1", "role": "implementer", "checks": []}, "non-claims": ["no check decides this task; done means the agent said so"]})
        write(os.path.join(root, "tasks", "T2.json"), {"artifact-type": "chongdae/task@1", "status": "done", "touched": ["b.py"], "confirmed": {"delegated": "late", "verifier": None},
                                                       "def": {"id": "T2", "role": "implementer", "checks": [["x"]]}})
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        write(os.path.join(pj.dir, "b.py"), "y = 1\n")
        write(os.path.join(pj.dir, "c.py"), "z = 1\n")
        name, plan, state = dwitbuk.runs(pj.dir)[0]
        assert [t["id"] for t in plan["tasks"]] == ["T1", "T2"] and state["non-claims"] == ["T1: no check decides this task; done means the agent said so"]
        # the reader serves the eyes packet, never a review: a review without reporters computes nothing from this directory
        run("review", "--since", pj.base, "--target", pj.dir)
        assert kinds(pj.latest()) == {"no-reporters": 1}


def test_stop_hook_steps_aside_inside_a_worker_session_and_without_the_switch():
    with Project() as pj:
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")   # dirty
        hook = os.path.join(HERE, "hooks", "stop_eyes.py")
        def run_hook(payload, **env):
            done = subprocess.run([sys.executable, hook], input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, **env))
            return done.returncode, done.stdout + done.stderr
        assert run_hook({"cwd": pj.dir})[0] == 0, "no switch in the lock: nothing runs"
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"settings": {"dwitbuk": {"stop-eyes": True}}})
        assert run_hook({"cwd": pj.dir}, AGENT_WORKER="1")[0] == 0, "inside a worker session: nothing runs"
        assert run_hook({"cwd": pj.dir, "stop_hook_active": True})[0] == 0, "the second stop of a turn: nothing runs"
        assert not os.path.exists(os.path.join(pj.dir, ".dwitbuk")), "and no scratch was written"



def test_worker_record_names_the_model_and_keeps_the_transcript():
    """The host does not tell anyone which model a session ran on except in its own stream: the init event. The worker
    keeps that (model, turns, cost, session) and the whole stream next to the response, so `performed_by` can name the
    model and a bare verdict can be audited. A Codex call, which has no such stream, records host and the model asked for."""
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="eyes-")
    try:
        resp = os.path.join(d, "sub", "T1.response.json")
        text = stream({"type": "system", "subtype": "init", "model": "claude-x-1", "session_id": "s1"},
                      {"type": "assistant", "message": {}},
                      {"type": "result", "num_turns": 4, "total_cost_usd": 0.05, "session_id": "s1", "structured_output": {}})
        rec = w.worker_record(text, resp, "claude-code")
        assert rec == {"host": "claude-code", "model": "claude-x-1", "turns": 4, "cost_usd": 0.05, "session": "s1", "transcript": "T1.response.transcript.jsonl"}, rec
        kept = open(os.path.join(d, "sub", "T1.response.transcript.jsonl"), encoding="utf-8").read()
        assert kept.count("\n") == 3 and '"model": "claude-x-1"' in kept.replace('"model":"', '"model": "'), kept
        assert w.worker_record(None, resp, "codex", "gpt-x") == {"host": "codex", "model": "gpt-x"}
        assert w.worker_record("not json\n", resp, "claude-code", "asked-for")["model"] == "asked-for", "no init event: the model asked for, not a guess"
    finally:
        shutil.rmtree(d, ignore_errors=True)

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("PASS", name)
            except Skip as why:
                print("SKIP", name, "--", why)
            except (Exception, SystemExit) as err:   # a self-check that dies between tests lies by omission
                failed += 1
                print("FAIL", name, "--", "%s: %s" % (type(err).__name__, err))
    print("all passed" if not failed else "%d failed" % failed)
    sys.exit(1 if failed else 0)
