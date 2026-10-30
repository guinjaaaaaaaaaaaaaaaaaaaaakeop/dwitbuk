"""Self-check for dwitbuk. A temp git project with hand-written run records; every kind of finding fires once, dispositions carry.

  python test_dwitbuk.py
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dwitbuk  # noqa: E402
import eyes_worker as w  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "hooks"))
import session_start  # noqa: E402


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

    def reporter(self, findings, name="fake", standing=False):
        """A reporter the lock declares: prints the given dwitbuk/findings@1 (recorded from chongdae's real `report`, trimmed)."""
        script = os.path.join(self.dir, name + ".py")
        doc = {"artifact-type": "dwitbuk/findings@1", "source": name, "findings": findings, **({"standing": True} if standing else {})}
        write(script, "import sys\nprint(%r)\n" % json.dumps(doc))   # the JSON as a string: `true` is not Python
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

def test_a_reporters_plugin_is_the_copy_from_the_marketplace_the_project_declares():
    """Matched by name alone, the first install record belonged to another project, and a review ran its 1.1.0 reporters."""
    home = tempfile.mkdtemp(prefix="dwitbuk-home-")
    old = os.environ.get("HUNSU_CLAUDE_DIR")
    try:
        with Project() as p:
            os.environ["HUNSU_CLAUDE_DIR"] = home
            write(os.path.join(home, "plugins", "installed_plugins.json"), {"plugins": {
                "mangsang@other": [{"scope": "project", "projectPath": "/elsewhere", "installPath": "/cache/other/1.1.0"}],
                "mangsang@mangsang": [{"scope": "project", "projectPath": "/third", "installPath": "/cache/mangsang/1.4.0"},
                                      {"scope": "project", "projectPath": p.dir, "installPath": "/cache/mangsang/1.5.0"}]}})
            write(os.path.join(p.dir, "hunsu.json"), {"plugins": {"mangsang": {"marketplace": "mangsang"}}})
            assert dwitbuk.plugin_root(p.dir, "mangsang") == "/cache/mangsang/1.5.0"
            write(os.path.join(p.dir, "hunsu.json"), {"plugins": {"mangsang": {"marketplace": "absent"}}})
            try:
                dwitbuk.plugin_root(p.dir, "mangsang")
                raise AssertionError("a declared marketplace with no install here must stop, not fall back to another copy")
            except SystemExit as err:
                assert "not installed for it here" in str(err)
    finally:
        if old is None:
            os.environ.pop("HUNSU_CLAUDE_DIR", None)
        else:
            os.environ["HUNSU_CLAUDE_DIR"] = old
        shutil.rmtree(home, ignore_errors=True)


def test_a_run_seen_again_is_answered_and_what_no_check_can_decide_is_said_not_charged():
    """guin-site, 2026-09-30: eleven reviews in a day, forty objections, all delegated. A run's non-claims were grouped with
    other runs', so the `where` changed with each review's span and the same charge came back new ("run A" -> "run A, run
    B"): "no check decides this task" was answered ten times. The project's declared outside-runs setting was listed as an
    objection in every review. And a contract or design task (domain plan) or a test task has no check by nature."""
    with Project() as pj:
        for rid, tasks in (("run-20260101-000001-aaaa", {"C1": {"domain": "plan", "role": "session"}, "B1": {"domain": "code", "role": "session"}}),
                           ("run-20260101-000002-bbbb", {"T2": {"domain": "code", "role": "nitpick"}})):
            write(os.path.join(pj.dir, ".chongdae", rid, "plan.json"), {"artifact-type": "chongdae/plan@1", "goal": rid,
                  "tasks": [{"id": k, "checks": [], **v} for k, v in tasks.items()]})
            write(os.path.join(pj.dir, ".chongdae", rid, "state.json"), {"status": "complete", "tasks": {k: {"status": "done"} for k in tasks}})
        nc = "no check decides this task; done means the agent said so"
        first = [{"kind": "non-claim", "where": "settings.chongdae.outside-runs", "text": "content, docs: the project's own procedure, declared in hunsu.json; 3 file(s) changed there since abc1234 are not reported as outside-run"},
                 {"kind": "non-claim", "where": "run-20260101-000001-aaaa", "text": "C1: " + nc},
                 {"kind": "non-claim", "where": "run-20260101-000001-aaaa", "text": "B1: " + nc}]
        pj.reporter(first, "chongdae")
        assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
        r = pj.latest()
        setting = next(f for f in r["findings"] if f["where"] == "settings.chongdae.outside-runs")
        assert dwitbuk.layer(setting) == "observation", setting   # the project's own declaration
        # C1 (plan) and B1 (a code task with no check) share a run: the run's finding is a charge because B1 is one
        objs = [f for f in r["findings"] if f["kind"] == "non-claim" and dwitbuk.layer(f) == "objection"]
        assert [f["where"] for f in objs] == ["run-20260101-000001-aaaa"], objs
        idx = r["findings"].index(objs[0])
        assert run("dispose", "%s/%d" % (r["id"], idx), "--as", "accepted", "--why", "B1 was checked by hand", "--by", "kim", "--target", pj.dir)[0] == 0
        # the next review spans one more run: the first run's charge keeps its identity and its answer; the test task's is said
        import time; time.sleep(1.1)
        pj.reporter(first + [{"kind": "non-claim", "where": "run-20260101-000002-bbbb", "text": "T2: " + nc}], "chongdae")
        code, out = run("review", "--since", pj.base, "--target", pj.dir)
        r2 = pj.latest()
        again = next(f for f in r2["findings"] if f["kind"] == "non-claim" and f["where"] == "run-20260101-000001-aaaa")
        assert again["disposition"]["why"] == "B1 was checked by hand", again   # answered when it read `[tasks C1, B1]`: the same charge
        assert again["text"].endswith("  [tasks: C1 (run-20260101-000001-aaaa), B1 (run-20260101-000001-aaaa); also in other runs: T2 (run-20260101-000002-bbbb)]"), again
        t2 = next(f for f in r2["findings"] if f["where"] == "run-20260101-000002-bbbb")
        assert dwitbuk.layer(t2) == "observation", t2
        assert "0 objection(s)" in out and "already answered, carried with their disposition: 1" in out, out


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
        k = kinds(r)
        assert k == {"outside-run": 1, "unattributed": 1, "delegated": 2, "non-claim": 3, "unreviewed": 1, "reporter-failed": 1, "undisposed": 1}, k   # no debt line: the carry is the debt
        outside = next(f for f in r["findings"] if f["kind"] == "outside-run")
        assert "b.py" in outside["where"] and "hunsu.json" in outside["where"] and "files" not in outside, outside   # grouped by directory; the list is not saved
        assert "source" not in next(f for f in r["findings"] if f["kind"] == "unreviewed") and "reporters" not in r   # written once, read by nothing
        assert "gave no dwitbuk/findings@1" in next(f["text"] for f in r["findings"] if f["kind"] == "reporter-failed")
        nc = [f["text"] for f in r["findings"] if f["kind"] == "non-claim"]
        assert sorted(t for t in nc if t.startswith("x untested")) == ["x untested  [tasks: S1 (run-20260101-000001-aaaa); also in other runs: S2 (run-20260101-000002-bbbb)]",
                                                                      "x untested  [tasks: S2 (run-20260101-000002-bbbb); also in other runs: S1 (run-20260101-000001-aaaa)]"] and "y untested  [task S2]" in nc, nc   # one per run; the repeat named, not `[x2]`
        carry = next(f for f in r["findings"] if f["kind"] == "undisposed")
        assert carry["carries"][0] == "no-reporters" and carry["text"].startswith("no reporters declared") and carry["raised-in"].endswith("/0"), carry   # whole, pointing back


def load_review(pj, rid=None):
    return json.load(open(os.path.join(pj.dir, "reviews", (rid or pj.latest()["id"]) + ".json"), encoding="utf-8"))


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
        assert code == 0 and "(delegated, nobody named as handing it off" in out and du["as"] == "dismissed" and du["delegated"] == "the person was away; the run is a test" and du["by"] is None
        assert "delegated-by" not in du, du
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
        assert by_kind["unattributed"]["first-seen"] == first["id"]
        assert "delegated" not in by_kind and by_kind["unchanged"]["layer"] == "observation" and by_kind["unchanged"]["seen-in"] == [first["id"]], by_kind.keys()   # the observation is on record in the first review; counted here
        assert "outside-run" not in by_kind and "undisposed" not in by_kind, by_kind.keys()
        # the previous review still held an open objection (unattributed): the charge itself is here, once — no debt line restating it
        assert "review-debt" not in by_kind, by_kind.keys()
        code, out = run("follow", "--target", pj.dir)
        assert code == 1 and "undisposed findings: 1" in out, out   # the unattributed charge, once
        # the third review: the charge is still reported, so it is the reporter's own finding again — one copy, no carry beside it
        time.sleep(1.1)
        run("review", "--target", pj.dir)
        third = pj.latest()
        assert sum(f["kind"] == "undisposed" for f in third["findings"]) == 0 and "review-debt" not in kinds(third), third["findings"]


def test_one_charge_is_disposed_once_across_consecutive_reviews():
    """Reviews in a row each held their own copy of one charge — found again, then carried as `undisposed`, with a debt line
    pointing back at the older copy — and every copy was disposed on its own. One disposal answers the charge everywhere."""
    import time
    with Project() as pj:
        charges = [{"kind": "non-claim", "where": "run-1", "text": "(provider) rendering size was not checked"},
                   {"kind": "verifier-reject", "where": "run-1/T1 attempt 1", "text": "claim-unverified: no command behind the claim"}]
        pj.reporter(charges)
        run("review", "--since", pj.base, "--target", pj.dir)
        first = pj.latest()
        time.sleep(1.1); run("review", "--target", pj.dir)          # the same run's record, read again: found again
        second = pj.latest()
        pj.reporter([]); time.sleep(1.1); run("review", "--target", pj.dir)   # no longer reported: carried as undisposed
        third = pj.latest()
        carried = [i for i, f in enumerate(third["findings"]) if f["kind"] == "undisposed"]
        assert len(carried) == 2 and all(third["findings"][i]["layer"] == "objection" for i in carried), third["findings"]
        assert all(third["findings"][i]["raised-in"].startswith(second["id"] + "/") for i in carried), third["findings"]
        before = {rid: load_review(pj, rid) for rid in (first["id"], second["id"])}
        for i in carried:
            code, out = run("dispose", "%s/%d" % (third["id"], i), "--as", "accepted", "--why", "known", "--by", "kim", "--target", pj.dir)
            assert code == 0 and "other place" not in out and "one answer for the charge first seen in %s" % first["id"] in out, out
        for rid, r in before.items():
            assert load_review(pj, rid) == r, "an earlier review is history: the answer is written once, not copied into it"
        assert run("follow", "--target", pj.dir)[0] == 0
        time.sleep(1.1); run("review", "--target", pj.dir)
        fourth = pj.latest()
        assert not [f for f in fourth["findings"] if f.get("layer") == "objection"], fourth["findings"]   # nothing owed, nothing carried
        # a charge answered in an older review and found again later inherits that answer, whichever review held it
        pj.reporter(charges[:1]); time.sleep(1.1); run("review", "--target", pj.dir)
        again = pj.latest()
        f = next(f for f in again["findings"] if f["kind"] == "non-claim")
        assert f["disposition"]["as"] == "accepted", f


def test_disposal_carries_the_charge_and_its_quote_for_the_next_reader_and_quoted_findings_warn_without_one():
    """The pair (finding, reason) sits in the disposal for the person who reads the review later — no machine judge reads it
    (none exists in any product; the wording that promised one is gone)."""
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
        assert code == 0 and "grounded in quotes" in out and "harder for the next reader" in out, out
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


def test_follow_prints_each_charge_whole_grouped_by_kind_and_path_asks_what_concerns_a_file():
    """Measured on a site: `follow` was the read at every resume and disposal, but it cut each text at 90 characters and
    listed flat, so every disposal round opened reviews/*.json too. Now the charge is whole, under its kind with a count,
    still behind the `<review>/<n>` handle `dispose` takes; `--path` answers "what is open on this file" before an edit."""
    with Project() as pj:
        long_text = "plan-vs-code: the draft card renders preview and open only; " + "the publish button appears on the detail screen. " * 3 + "END"
        pj.reporter([{"kind": "contradiction", "where": "run-1/T attempt 1: src/admin.html:274-285", "text": long_text},
                     {"kind": "contradiction", "where": "run-1/T: docs/plan.md#Admin", "text": "second"},
                     {"kind": "stale", "where": "rel-7", "text": "the relation's anchor moved", "files": ["src/admin.html", "lib/x.py"]},
                     {"kind": "stale", "where": "lib/a.pyc, src/admin.html.bak", "text": "names neither file"},
                     {"kind": "delegated", "where": "src/admin.html", "text": "an observation, never listed"}])
        run("review", "--since", pj.base, "--target", pj.dir)
        r = load_review(pj)
        r["findings"][0].update(record_quote="Drafts have preview and publish buttons.", tree_quote="bits.push(open);")
        save_review(pj, r)
        code, out = run("follow", "--target", pj.dir)
        lines = out.splitlines()
        assert code == 1 and lines[-1] == "undisposed findings: 4", out   # the last line and the exit code are what they were
        assert long_text in out and "%s/0  run-1/T attempt 1: src/admin.html:274-285" % r["id"] in out, out   # whole, with its handle
        assert "contradiction (2)" in lines and "stale (2)" in lines and lines.index("stale (2)") > lines.index("contradiction (2)"), out
        assert "record: \u201cDrafts have preview and publish buttons.\u201d" in out and "tree: \u201cbits.push(open);\u201d" in out, out
        assert "files: src/admin.html, lib/x.py" in out and "delegated" not in out, out
        code, out = run("follow", "--path", "src/admin.html", "--target", pj.dir)
        assert code == 1 and out.splitlines()[-1] == "undisposed findings: 2 naming src/admin.html (4 in all)", out
        assert "contradiction (1)" in out and "stale (1)" in out and "second" not in out and "names neither" not in out, out
        code, out = run("follow", "--path", os.path.join(pj.dir, "docs", "plan.md"), "--target", pj.dir)   # absolute: relative to the target
        assert code == 1 and "second" in out and "undisposed findings: 1 naming docs/plan.md" in out, out
        code, out = run("follow", "--path", "./a.py", "--target", pj.dir)
        assert code == 0 and out.splitlines()[-1] == "undisposed findings: 0 naming a.py (4 in all)", out


def test_follow_brief_is_a_readers_line_and_says_nothing_when_nothing_is_open():
    """jokbo gives the agent, at its first look at a file, one line per fact that bears on it; full outputs pasted into a
    context were ignored, and `follow --path` printed even "undisposed findings: 0 naming ...". `--brief`: the first charge
    cut near 120 characters with its kind and the count, `+N more` when there are more — and no output at all, exit 0,
    when nothing is open on the file. The `note` read declares it in every manifest that carries `reads`."""
    with Project() as pj:
        long_text = "plan-vs-code: the draft card renders preview and open only; " + "the publish button appears on the detail screen. " * 3 + "END"
        pj.reporter([{"kind": "contradiction", "where": "run-1/T attempt 1: src/admin.html:274-285", "text": long_text},
                     {"kind": "stale", "where": "rel-7", "text": "the relation's anchor moved", "files": ["src/admin.html"]},
                     {"kind": "stale", "where": "docs/plan.md#Admin", "text": "short\n  charge"},
                     {"kind": "delegated", "where": "lib/b.py", "text": "an observation, never a charge"}])
        run("review", "--since", pj.base, "--target", pj.dir)
        code, out = run("follow", "--path", "src/admin.html", "--brief", "--target", pj.dir)
        lines = out.splitlines()
        assert code == 1 and len(lines) == 2, out
        assert lines[0].startswith("2 open objection(s) on this file: contradiction \u2014 plan-vs-code: the draft card"), out
        assert "END" not in out and lines[0].endswith("\u2026") and len(lines[0]) < 200, out
        assert lines[1] == "+1 more (`dwitbuk follow --path src/admin.html`)", out
        code, out = run("follow", "--path", "docs/plan.md", "--brief", "--target", pj.dir)
        assert code == 1 and out == "1 open objection(s) on this file: stale \u2014 short charge\n", repr(out)   # one: no "+N more"
        for quiet in ("a.py", "lib/b.py"):   # nothing named, or only an observation: nothing printed, not "0"
            code, out = run("follow", "--path", quiet, "--brief", "--target", pj.dir)
            assert code == 0 and out == "", (quiet, code, out)
        code, out = run("follow", "--brief", "--target", pj.dir)
        assert code != 0 and "--path" in out, out
    with Project() as pj:   # no review at all: still nothing
        code, out = run("follow", "--path", "a.py", "--brief", "--target", pj.dir)
        assert code == 0 and out == "", out
    for manifest in ("plugin.json", os.path.join(".claude-plugin", "plugin.json"), os.path.join(".codex-plugin", "plugin.json")):
        reads = dwitbuk.load(os.path.join(HERE, manifest))["reads"]
        assert reads["note"] == ["python3", "{plugin:dwitbuk}/dwitbuk.py", "follow", "--path", "{path}", "--brief", "--target", "{target}"], manifest
        assert "--brief" not in reads["file"], manifest   # the whole read stays


def test_an_observation_is_written_once_and_counted_after_that():
    """Measured on a site: 120 relations confirmed by delegation came back as 120 `delegated` observations in every review,
    58 KB of a 96 KB file, forever. An observation is a fact; once a review holds it in full, later reviews count it in one
    `unchanged` line that names that review — and still recognize it as the same fact three reviews on. A changed text is
    a new fact, written in full again. Objections are untouched: they inherit and become `undisposed` as before."""
    import time
    with Project() as pj:
        obs = [{"kind": "delegated", "where": "R-1 a realizes c", "text": "re-confirmed by delegation: plan-07"},
               {"kind": "delegated", "where": "R-2 b realizes c", "text": "re-confirmed by delegation: plan-07"}]
        pj.reporter(obs + [{"kind": "left-open", "where": "run-1/T", "text": "left open when the run closed"}])
        assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
        first = pj.latest()
        assert kinds(first) == {"delegated": 2, "left-open": 1}, kinds(first)
        time.sleep(1.1); assert run("review", "--target", pj.dir)[0] == 0
        second = pj.latest()
        assert kinds(second) == {"unchanged": 1, "left-open": 1}, kinds(second)
        u = next(f for f in second["findings"] if f["kind"] == "unchanged")
        assert u["layer"] == "observation" and u["seen-in"] == [first["id"]] and "count" not in u and u["text"].startswith("2 observation(s)") and "delegated 2" in u["text"], u
        assert next(f for f in second["findings"] if f["kind"] == "left-open")["first-seen"] == first["id"]
        time.sleep(1.1); assert run("review", "--target", pj.dir)[0] == 0
        third = pj.latest()   # two reviews on: still one line, still pointing at the review that holds them
        assert kinds(third)["unchanged"] == 1 and next(f for f in third["findings"] if f["kind"] == "unchanged")["seen-in"] == [first["id"]], third["findings"]
        # one fact changes: it is written in full again; the other stays counted
        pj.reporter([dict(obs[0], text="re-confirmed by delegation: plan-09"), obs[1], {"kind": "left-open", "where": "run-1/T", "text": "left open when the run closed"}])
        time.sleep(1.1); assert run("review", "--target", pj.dir)[0] == 0
        fourth = pj.latest()
        assert kinds(fourth)["delegated"] == 1 and next(f for f in fourth["findings"] if f["kind"] == "unchanged")["text"].startswith("1 observation(s)"), kinds(fourth)
        assert run("follow", "--target", pj.dir)[0] == 1, "the objection is still debt; observations never were"


def site_reviews(pj):
    """Reviews as 1.11.0 wrote them on guin-site (2026-10-05..06), trimmed: the first raises eight charges (four outside-run
    files, four runs' "no check decides this task") and three delegated relations; each of the four after it re-raises the
    eight as `undisposed` — its own wording, cut at 80 characters — with a `review-debt` line, one `unchanged` line per review
    that holds observations, and two delegated judgments of its own."""
    rids = ["review-20261005-01145%d-36b%d" % (n, n) for n in range(5)]
    since = "5fd9bb07ce7612d50a7a582a6f61fbd5c50b1f20"
    charges = [{"kind": "outside-run", "where": w, "layer": "objection", "first-seen": rids[0],
                "text": "1 file(s) changed since %s; no completed run recorded touching them" % since}
               for w in ("package.json", "scripts/setup-backup.mjs", "worker/backup.mjs", "tests/backup_harness.mjs, test_backup.py")]
    charges += [{"kind": "non-claim", "where": "run-20261004-1%d4130-9035" % n, "layer": "objection", "first-seen": rids[0],
                 "text": "no check decides this task  [x2]"} for n in range(4)]
    held = {rids[0]: [{"kind": "delegated", "where": "R-%d site.css realizes concept:page-regions" % n, "layer": "observation",
                       "text": "re-confirmed by delegation: judge kim: still the same region (%d)" % n} for n in range(3)]}
    for k, rid in enumerate(rids):
        findings = [dict(f) for f in held.get(rid, [])]
        if k == 0:
            findings += [dict(c) for c in charges]
        else:
            held[rid] = [{"kind": "delegated", "where": "R-%d%d test.py realizes concept:feed" % (k, n), "layer": "observation",
                          "text": "re-confirmed by delegation: judge kim: review %d, judgment %d" % (k, n)} for n in range(2)]
            findings = [dict(f) for f in held[rid]]
            findings.append({"kind": "review-debt", "where": rids[k - 1], "layer": "observation",
                             "text": "previous review %s still has 8 undisposed objection(s), carried here" % rids[k - 1]})
            for h in rids[:k]:
                findings.append({"kind": "unchanged", "layer": "observation", "where": h, "seen-in": h,
                                 "text": "%d observation(s) written in %s and unchanged since (delegated %d)" % (len(held[h]), h, len(held[h]))})
            findings += [{"kind": "undisposed", "where": c["where"], "layer": "objection",
                          "text": "%s (first seen %s): %s" % (c["kind"], rids[0], c["text"][:80]), "first-seen": rids[0],
                          "carries": list(dwitbuk.identity(c))} for c in charges]
        write(os.path.join(pj.dir, "reviews", rid + ".json"), {"artifact-type": "dwitbuk/review@1", "id": rid, "since": pj.base, "head": pj.base, "findings": findings})
    return rids, charges, [f for fs in held.values() for f in fs]


def test_a_carried_charge_stands_once_and_one_disposal_answers_it_once():
    """guin-site, 2026-10-05..06: eight charges stood in five reviews in a row — raised, then re-raised in each as `undisposed`
    in a wording of their own cut at 80 characters ("no completed r"), with a `review-debt` line restating the count and one
    `unchanged` line per holding review (12-15 lines at the head of each); disposing one copied the answer into every review
    ("the same charge answered in 5 other place(s)"), and the eight were closed at last by one blanket "as proposed". Now: the
    latest review holds each open charge once, whole, pointing at where it was raised; the observations already on record are
    one counted line; a disposal is written once; the earlier reviews stay as they were, and still read."""
    import time
    with Project() as pj:
        rids, charges, held = site_reviews(pj)
        before = {rid: open(os.path.join(pj.dir, "reviews", rid + ".json"), encoding="utf-8").read() for rid in rids}
        # the reporter reads the relations again: every judgment already on record, and two new ones since the last review
        new = [{"kind": "delegated", "where": "R-9%d site.css realizes concept:share" % n, "text": "re-confirmed by delegation: judge kim: new %d" % n} for n in range(2)]
        pj.reporter([{k: f[k] for k in ("kind", "where", "text")} for f in held] + new)
        code, out = run("review", "--target", pj.dir)
        assert code == 0, out
        r = pj.latest()
        assert kinds(r) == {"delegated": 2, "unchanged": 1, "undisposed": 8}, kinds(r)   # no review-debt; one unchanged line
        u = next(f for f in r["findings"] if f["kind"] == "unchanged")
        assert u["seen-in"] == rids and u["text"].startswith("11 observation(s) written in full in 5 earlier review(s)") and "delegated 11" in u["text"], u
        assert {f["where"] for f in r["findings"] if f["kind"] == "delegated"} == {f["where"] for f in new}, "only what is new is written"
        carried = [(i, f) for i, f in enumerate(r["findings"]) if f["kind"] == "undisposed"]
        first_review = load_review(pj, rids[0])
        for i, f in carried:
            src_rid, _, src_i = f["raised-in"].rpartition("/")
            src = first_review["findings"][int(src_i)]
            assert src_rid == rids[0] and dwitbuk.identity(src) == tuple(f["carries"]), f   # referenced, not re-raised
            assert f["text"] == dwitbuk.OLD_REPEAT.sub("", src["text"]) and "(first seen" not in f["text"] and f["first-seen"] == rids[0], f   # whole
            assert "[x" not in f["text"], f   # an old `[x2]` read as a count of tasks: struck from the carried text, not from the charge
        assert "carried from earlier reviews, each once: 8" in out, out
        code, out = run("follow", "--target", pj.dir)
        lines = out.splitlines()
        assert code == 1 and lines[-1] == "undisposed findings: 8" and "outside-run (4)" in lines and "non-claim (4)" in lines, out
        assert out.count("no completed run recorded touching them") == 4 and "no completed r\n" not in out and "raised in %s/" % rids[0] in out, out
        # one disposal, written once — the earlier reviews are not touched
        i0 = carried[0][0]
        code, out = run("dispose", "%s/%d" % (r["id"], i0), "--as", "dismissed", "--why", "adopted by hand in backup-setup", "--by", "kim", "--target", pj.dir)
        assert code == 0 and "other place" not in out and "first seen in %s" % rids[0] in out, out
        assert all(open(os.path.join(pj.dir, "reviews", rid + ".json"), encoding="utf-8").read() == before[rid] for rid in rids), "history stays as written"
        assert run("follow", "--target", pj.dir)[1].splitlines()[-1] == "undisposed findings: 7"
        # an earlier review's handle still works: the answer goes where the charge stands now, once
        old_i = next(i for i, f in enumerate(load_review(pj, rids[3])["findings"]) if f["kind"] == "undisposed" and f["where"] == carried[1][1]["where"])
        code, out = run("dispose", "%s/%d" % (rids[3], old_i), "--as", "accepted", "--why", "known", "--by", "kim", "--target", pj.dir)
        assert code == 0 and "recorded at %s/%d" % (r["id"], carried[1][0]) in out, out
        assert open(os.path.join(pj.dir, "reviews", rids[3] + ".json"), encoding="utf-8").read() == before[rids[3]]
        assert pj.latest()["findings"][carried[1][0]]["disposition"]["why"] == "known"
        # the next review: the six still open, carried once each, still pointing at the same raising; nothing restated
        time.sleep(1.1); code, out = run("review", "--target", pj.dir)
        nxt = pj.latest()
        again = [f for f in nxt["findings"] if f["kind"] == "undisposed"]
        assert len(again) == 6 and {f["raised-in"] for f in again} <= {f["raised-in"] for _, f in carried[2:]}, again
        assert kinds(nxt) == {"unchanged": 1, "undisposed": 6}, kinds(nxt)
        assert next(f for f in nxt["findings"] if f["kind"] == "unchanged")["text"].startswith("13 observation(s) written in full in 6 earlier review(s)")
        # a charge reported again while carried is one finding — the reporter's — not the carry beside it
        pj.reporter([{k: charges[4][k] for k in ("kind", "where", "text")}])
        time.sleep(1.1); run("review", "--target", pj.dir)
        latest = pj.latest()
        same = [f for f in latest["findings"] if dwitbuk.charge(f) == dwitbuk.identity(charges[4])]
        assert len(same) == 1 and same[0]["kind"] == "non-claim" and same[0]["first-seen"] == rids[0], same
        # the answers stand where they were written and are inherited: neither disposed charge comes back
        assert sum(1 for _, f in dwitbuk.open_charges(pj.dir)[1]) == 6


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
        write(os.path.join(out_dir, "eyes-response.json"), dict(EYES_RESPONSE, request=dwitbuk.fingerprint(packet)))
        code, out = run("eyes", "consume", "--dir", out_dir, "--target", pj.dir)
        assert code == 0 and "2 finding(s) added" in out and "2 rejected" in out, out
        r = pj.latest()
        added = [f for f in r["findings"] if f["kind"] == "contradiction"]
        assert len(added) == 1 and "proposals.json" in added[0]["where"] and "record: " in added[0]["text"] and "by" not in added[0]
        assert any(f["kind"] == "anomaly" and "bare constant" in f["text"] for f in r["findings"])
        # consuming the same answer again adds nothing; the finding carries into the next review like any other
        code, out = run("eyes", "consume", "--dir", out_dir, "--target", pj.dir)
        assert "0 finding(s) added" in out, out
        import time; time.sleep(1.1)
        run("review", "--target", pj.dir)
        assert any(f["kind"] == "undisposed" and f["carries"][0] == "contradiction" and "record: " in f["text"] for f in pj.latest()["findings"])
        assert any(f["kind"] == "undisposed" and f["carries"][0] == "anomaly" and "bare constant" in f["text"] for f in pj.latest()["findings"])


def eyes_answer(pj, folder, name="finding"):
    """A host-free answer to a real packed request, bound as eyes_worker writes it."""
    assert run("eyes", "request", "--out", folder, "--target", pj.dir)[0] == 0
    packet = dwitbuk.load(os.path.join(folder, "eyes-request.json"))
    answer = {"request": dwitbuk.fingerprint(packet), "findings": [
        {"kind": "anomaly", "where": "a.py", "tree_quote": name, "record_quote": "", "why": name}]}
    write(os.path.join(folder, "eyes-response.json"), answer)
    return packet, answer


def test_late_eyes_refuses_wrong_target_unbound_replaced_and_stale_answers():
    with Project() as pj, Project() as other:
        run("review", "--target", pj.dir)
        run("review", "--target", other.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, answer = eyes_answer(pj, folder)
        original = pj.latest()
        code, out = run("eyes", "consume", "--dir", folder, "--target", other.dir)
        assert code != 0 and "another target" in out, out
        request_path = os.path.join(folder, "eyes-request.json")
        os.unlink(request_path)
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "missing request/source" in out, out
        write(request_path, dict(packet, instructions="a replacement request"))
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "does not match" in out, out
        write(request_path, packet)
        write(os.path.join(pj.dir, "a.py"), "x = 9\n")
        for committed in (False, True):
            if committed:
                git(pj.dir, "add", "a.py"); git(pj.dir, "commit", "-qm", "changed source")
            code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
            assert code != 0 and "source changed" in out, (committed, out)
            assert pj.latest() == original
        # A fresh review succeeds, and source-neutral record commits do not stale it.
        eyes_answer(pj, folder)
        git(pj.dir, "add", "reviews"); git(pj.dir, "commit", "-qm", "record only")
        assert run("eyes", "consume", "--dir", folder, "--target", pj.dir)[0] == 0


def test_late_eyes_sees_nested_source_and_worker_refuses_changes_during_call():
    from unittest.mock import patch
    with Project() as pj:
        nested = os.path.join(pj.dir, "engine")
        os.makedirs(nested)
        git(nested, "init", "-q")
        write(os.path.join(nested, "code.py"), "old\n")
        git(nested, "add", "."); git(nested, "commit", "-qm", "nested base")
        write(os.path.join(pj.dir, ".gitignore"), "engine/\n")
        run("review", "--target", pj.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder)
        write(os.path.join(nested, "code.py"), "changed\n")
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "source changed" in out, out
        eyes_answer(pj, folder)
        response = os.path.join(folder, "eyes-response.json")
        os.unlink(response)
        def host(packet, schema, args):
            assert schema["properties"]["request"]["enum"] == [dwitbuk.fingerprint(packet)]
            write(os.path.join(pj.dir, "a.py"), "changed during worker\n")
            return {"findings": []}
        with patch.object(w, "claude", host), patch.object(sys, "argv", ["eyes_worker.py", "--request", os.path.join(folder, "eyes-request.json"), "--response", response]):
            try:
                w.main()
                raise AssertionError("a changed source cannot receive a fresh-looking answer")
            except SystemExit as err:
                assert "source changed" in str(err), err
        assert not os.path.exists(response)


def test_late_eyes_rejects_changed_run_record_inputs():
    with Project() as pj:
        pj.run_record("run-example", {"S1": {"status": "done", "touched": ["a.py"]}})
        run("review", "--target", pj.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder)
        original = pj.latest()
        pj.run_record("run-example", {"S1": {"status": "failed", "touched": ["a.py"]}})
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "source changed" in out and pj.latest() == original, out


def test_stop_hook_validates_before_displaying_even_without_a_review():
    from unittest.mock import patch
    from types import SimpleNamespace
    import stop_eyes
    real_run = subprocess.run
    for has_review, stale in ((False, True), (True, True), (True, False)):
        with Project() as pj:
            write(os.path.join(pj.dir, "hunsu.json"), {"settings": {"dwitbuk": {"stop-eyes": True}}})
            write(os.path.join(pj.dir, "a.py"), "x = 2\n")
            if has_review:
                run("review", "--target", pj.dir)
            def host(argv, **kwargs):
                if len(argv) > 1 and str(argv[1]).endswith("eyes_worker.py"):
                    request = dwitbuk.load(argv[argv.index("--request") + 1])
                    write(argv[argv.index("--response") + 1], {"request": dwitbuk.fingerprint(request), "findings": [
                        {"kind": "anomaly", "where": "a.py", "tree_quote": "x = 2", "why": "old finding", "record_quote": ""}]})
                    if stale:
                        write(os.path.join(pj.dir, "a.py"), "x = 3\n")
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                return real_run(argv, **kwargs)
            output = io.StringIO()
            with patch.dict(os.environ, {"AGENT_WORKER": ""}), patch.object(sys, "stdin", io.StringIO(json.dumps({"cwd": pj.dir}))), \
                    patch.object(subprocess, "run", host), contextlib.redirect_stderr(output), contextlib.redirect_stdout(io.StringIO()):
                code = stop_eyes.main()
            if stale:
                assert code == 0 and "source changed" in output.getvalue() and "address each" not in output.getvalue(), output.getvalue()
                if has_review:
                    assert not any(f["kind"] == "anomaly" for f in pj.latest()["findings"])
            else:
                assert code == 2 and any(f["kind"] == "anomaly" for f in pj.latest()["findings"]), output.getvalue()


def test_concurrent_consumers_refuse_busy_then_retain_both_findings_on_retry():
    with Project() as pj:
        run("review", "--target", pj.dir)
        first, second = [os.path.join(pj.dir, ".dwitbuk", name) for name in ("first", "second")]
        eyes_answer(pj, first, "first")
        eyes_answer(pj, second, "second")
        # Pause writer one after it read the review and before replacement. A second
        # process must not read that old review and later overwrite its new finding.
        script = """import sys
import dwitbuk
save = dwitbuk.save
def pause(path, doc):
    print('ready', flush=True)
    sys.stdin.readline()
    save(path, doc)
dwitbuk.save = pause
dwitbuk.main(sys.argv[1:])
"""
        proc = subprocess.Popen([sys.executable, "-c", script, "eyes", "consume", "--dir", first, "--target", pj.dir], cwd=HERE,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            assert proc.stdout.readline().strip() == "ready"
            attempt = subprocess.run([sys.executable, os.path.join(HERE, "dwitbuk.py"), "eyes", "consume", "--dir", second, "--target", pj.dir],
                                     capture_output=True, text=True, timeout=10)
            assert attempt.returncode == 4 and "retry" in attempt.stderr, attempt
            stdout, stderr = proc.communicate("\n", timeout=10)
            assert proc.returncode == 0, (stdout, stderr)
        finally:
            if proc.poll() is None:
                proc.kill(); proc.communicate()
        code, out = run("eyes", "consume", "--dir", second, "--target", pj.dir)
        assert code == 0, out
        findings = [f for f in pj.latest()["findings"] if f["kind"] == "anomaly"]
        assert len(findings) == 2 and all(any(name in f["text"] for f in findings) for name in ("first", "second")), findings


def test_a_standing_finding_that_stops_recurring_is_gone_not_owed():
    """A reporter that reads the state as it is now (environment drift, stale relations) says a finding is gone by no longer
    reporting it; carried as `undisposed`, a drift fixed an hour ago stayed a charge. Only when that reporter answered: a
    reporter that failed says nothing about what is gone."""
    import time
    with Project() as pj:
        drift = {"kind": "drift", "where": "plugin chongdae", "text": "installed 1.10.0, locked 1.9.0"}
        pj.reporter([drift], "env", standing=True)
        pj.reporter([{"kind": "unattributed", "where": "run-1/S1", "text": "no touched"}], "chongdae")
        run("review", "--since", pj.base, "--target", pj.dir)
        pj.reporter([], "env", standing=True)
        pj.reporter([], "chongdae")
        time.sleep(1.1); run("review", "--target", pj.dir)
        carried = [f for f in pj.latest()["findings"] if f["kind"] == "undisposed"]
        assert len(carried) == 1 and carried[0]["carries"][0] == "unattributed", carried   # the drift is gone; the event is still owed
        # a standing reporter that failed this time: nothing is known to be gone
        pj.reporter([drift], "env", standing=True)
        time.sleep(1.1); run("review", "--target", pj.dir)
        with io.open(os.path.join(pj.dir, "env.py"), "w", encoding="utf-8") as fh:
            fh.write("raise SystemExit(3)\n")
        time.sleep(1.1); run("review", "--target", pj.dir)
        assert any(f["kind"] == "undisposed" and f["carries"][0] == "drift" for f in pj.latest()["findings"]), pj.latest()["findings"]


def test_one_grounding_rule_for_eyes_findings_an_anomaly_stands_on_the_tree():
    """An anomaly has no record to quote by definition; the verify path once required a record quote of every finding and
    turned a verifier's true anomaly into "rejected without a quoted finding; counted as accept"."""
    anomaly = {"kind": "anomaly", "where": "mangsang/registry.json", "record_quote": "", "tree_quote": "\"path\": \"build.py\"", "why": "the file is gone"}
    assert dwitbuk.grounded(anomaly)
    assert not dwitbuk.grounded(dict(anomaly, kind="record-vs-tree")), "every other kind quotes the record too"
    assert not dwitbuk.grounded(dict(anomaly, tree_quote="")) and not dwitbuk.grounded(dict(anomaly, kind="made-up"))
    assert w.grounded is dwitbuk.grounded, "the verify path uses the same rule"


def test_verify_packet_diffs_from_where_the_task_started_in_each_repository():
    """sagoforce 10-26: every task's work was committed, six of them inside nested repositories the project's git ignores;
    `git diff HEAD` at the project showed nothing, so the eyes got empty diffs (or a file as new) and accepted. chongdae's
    `since` names the commit each repository started from: the diff runs there, in that repository, paths from the project."""
    with Project() as pj:
        write(os.path.join(pj.dir, ".gitignore"), "/engine/\n")
        eng = os.path.join(pj.dir, "engine")
        os.makedirs(eng)
        git(eng, "init", "-q")
        write(os.path.join(eng, "gate.py"), "limit = 1\n")
        git(eng, "add", "-A"); git(eng, "commit", "-q", "-m", "base")
        start = git(eng, "rev-parse", "HEAD")
        write(os.path.join(eng, "gate.py"), "limit = 2\n")
        git(eng, "commit", "-q", "-am", "the task's work, committed")
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        git(pj.dir, "commit", "-q", "-am", "and at the project")
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "run": "run-1", "task": "S1", "target": pj.dir,
               "touched": ["a.py", "engine/gate.py"], "since": {".": pj.base, "engine": start}}
        diff = dwitbuk.verify_packet(req)["diff"]
        assert "-limit = 1" in diff and "+limit = 2" in diff and "b/engine/gate.py" in diff, diff
        assert "+x = 2" in diff and "(new file)" not in diff, diff


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
        assert "recheck" not in p and "re-verification" not in p["instructions"]
        assert "excluded" not in p and "`excluded`" not in p["instructions"]   # nothing left out, nothing said
        # a task whose whole work is the environment: `touched` is empty by rule, and the packet says what was left out and shows it
        subprocess.run(["git", "init", "-q"], cwd=pj.dir, check=True)
        write(os.path.join(pj.dir, "hunsu.json"), '{"plugins": {}}\n')
        subprocess.run(["git", "add", "-A"], cwd=pj.dir, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"], cwd=pj.dir, check=True)
        write(os.path.join(pj.dir, "hunsu.json"), '{"plugins": {"mangsang": {}}}\n')
        env = dwitbuk.verify_packet(dict(req, touched=[], excluded={"record-paths": ["hunsu.json", ".chongdae/run-1/state.json"]}))
        assert env["touched"] == [] and env["excluded"] == ["hunsu.json"] and '+{"plugins": {"mangsang": {}}}' in env["excluded_diff"], env.get("excluded_diff")
        assert "by rule, not by omission" in env["instructions"] and "no record-vs-tree finding" in env["instructions"]
        # a re-verification: the last reject's findings and what changed since — the verifier checks those, not the whole slice again
        prior = [{"kind": "plan-vs-code", "where": "a.py", "record_quote": "prints one line", "tree_quote": "x = 2", "why": "two lines"}]
        p = dwitbuk.verify_packet(dict(req, recheck={"findings": prior, "changed_since": ["a.py"]}))
        assert p["recheck"]["changed_since"] == ["a.py"] and p["recheck"]["findings"] == prior
        assert "This is a re-verification" in p["instructions"] and "do not read it again for new findings" in p["instructions"]


def test_the_verifier_reads_the_hands_non_claims_and_what_chongdae_checked_itself():
    """guin-site, 10-10: the providers' non-claims reached the verifier only as `built` with nothing saying to read them, and
    the session's own full test run (exit 0) after a take reached it not at all. The packet carries the tests writer's
    non-claims and chongdae's checked commands, and says what each is."""
    with Project() as pj:
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "run": "run-1", "task": "S1", "target": pj.dir, "contract": {},
               "touched": ["a.py"], "built": {"summary": "s", "verified": [], "non-claims": ["nothing deployed"]}}
        p = dwitbuk.verify_packet(req)
        assert "`built.non-claims`" in p["instructions"] and "not charged again" in p["instructions"]
        assert "tests_non_claims" not in p and "checked" not in p and "chongdae itself ran" not in p["instructions"]
        assert "tests_non_claims" not in p["instructions"] and "are the builder's own" in p["instructions"]
        ck = [{"command": "python3 tests/run.py --all", "exit": 0, "tail": ["write 135 OK"], "changed_since": []}]
        p = dwitbuk.verify_packet(dict(req, tests_non_claims={"T": ['"the list is sorted" — three items only']}, checked=ck))
        # whose words they are is in the data, not only in the instructions (guin-site run a0ec)
        assert p["tests_non_claims"] == {"whose": dwitbuk.TESTS_NON_CLAIMS_WHOSE, "statements": {"T": ['"the list is sorted" — three items only']}} and p["checked"] == ck
        assert "not the builder's report" in p["tests_non_claims"]["whose"]
        assert "chongdae itself ran on the tree and saw exit 0" in p["instructions"] and "`tests_non_claims.statements` the tests writer's (T)" in p["instructions"]
        assert "`tests_non_claims` is never the builder's report" in p["instructions"] and "may not quote it as the builder's" in p["instructions"]
        # a passing check is not a finding that it fails — not a pass on whether it decides the sentence
        assert "is not a finding that it fails" in p["instructions"] and "whether it decides the sentence is still yours to judge" in p["instructions"]


def test_a_providers_non_claim_keeps_its_reason_and_chongdaes_own_repeats_still_group():
    """guin-site review ff52: a provider's non-claim leads with the contract sentence it could not decide and says why after
    the dash; cut at the first clause it read as a bare quote, the gap it named gone (36 such charges). Chongdae's own
    sentences still group by their first clause."""
    with Project() as pj:
        pj.run_record("run-20260101-000001-aaaa", {"S1": {"status": "done"}})
        pj.reporter([{"kind": "non-claim", "where": "run-20260101-000001-aaaa", "text": 'T1: (provider) "the list is sorted" — checked on three items only; no long list'},
                     {"kind": "non-claim", "where": "run-20260101-000001-aaaa", "text": "T2: no check decides this task; done means the agent said so"},
                     {"kind": "seen-non-claims", "layer": "observation", "where": "run-20260101-000001-aaaa/T3 (4)",
                      "text": "4 provider non-claim(s) went to the verifier with the work and it accepted — read there, said here, not charged"}], "chongdae")
        assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
        nc = {f["text"]: f["layer"] for f in pj.latest()["findings"] if f["kind"] in ("non-claim", "seen-non-claims")}
        assert nc == {'(provider) "the list is sorted" — checked on three items only; no long list  [task T1]': "objection",
                      "no check decides this task  [task T2]": "objection",
                      "4 provider non-claim(s) went to the verifier with the work and it accepted — read there, said here, not charged": "observation"}, nc
        # a disposal written before 1.13.0 answered the cut form, `(provider) "…"`: it answers the whole sentence now, and an
        # unanswered cut form is the same charge, not a second one carried beside it
        full = '(provider) "the list is sorted" — checked on three items only; no long list'
        import time
        for disposed in (False, True):   # unanswered first: an answer, once written, answers every later review
            r = pj.latest()
            path = os.path.join(pj.dir, dwitbuk.REVIEWS, r["id"] + ".json")
            for f in r["findings"]:
                if dwitbuk.identity(f)[2] in (full, '(provider) "the list is sorted"'):
                    f["text"] = '(provider) "the list is sorted"'
                    f.pop("disposition", None)
                    if disposed:
                        f["disposition"] = {"as": "accepted", "delegated": "three items decide sorting here", "by": None}
            write(path, r)
            time.sleep(1.1)
            assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
            same = [f for f in pj.latest()["findings"] if "the list is sorted" in f.get("text", "")]
            assert len(same) == 1 and dwitbuk.identity(same[0])[2] == full and same[0]["kind"] == "non-claim", same
            assert bool(same[0].get("disposition")) == disposed, same


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


def test_session_start_hook_says_what_the_placed_reviews_still_need_and_nothing_else():
    """Reviews are placed by the runner now (chongdae's `reviewer` role at a run's end), so nobody asks for them; what still
    needs a person is the disposition. The SessionStart hook says how many objections of the latest review are undisposed —
    a fact with the review's id, silent when there is nothing, silent in a worker session, never blocking."""
    hook = os.path.join(HERE, "hooks", "session_start.py")
    def run_hook(cwd, **env):
        done = subprocess.run([sys.executable, hook], input=json.dumps({"cwd": cwd}), capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, **env))
        return done.returncode, done.stdout
    with Project() as pj:
        assert run_hook(pj.dir) == (0, ""), "no reviews: silent"
        pj.reporter([{"kind": "outside-run", "where": "b.py", "files": ["b.py"], "text": "changed"},
                     {"kind": "left-open", "where": "run-1/T", "text": "left open when the run closed"},
                     {"kind": "delegated", "where": "run-1/T", "text": "gate passed by delegation: ok"}])
        assert run("review", "--target", pj.dir)[0] == 0
        code, out = run_hook(pj.dir)
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert code == 0 and ctx.startswith("dwitbuk: 2 undisposed objection(s) in review-") and "left-open 1, outside-run 1" in ctx and "follow" in ctx, ctx   # the observation is not counted
        assert run_hook(pj.dir, AGENT_WORKER="1") == (0, ""), "a worker session: silent"
        r = dwitbuk.reviews(pj.dir)[-1]
        objections = [i for i, f in enumerate(r["findings"]) if dwitbuk.layer(f) == "objection"]
        assert run("dispose", "%s/%d" % (r["id"], objections[0]), "--as", "accepted", "--why", "yes", "--by", "kim", "--target", pj.dir)[0] == 0
        code, out = run_hook(pj.dir)
        assert "1 undisposed objection(s)" in json.loads(out)["hookSpecificOutput"]["additionalContext"], out
        assert run("dispose", "%s/%d" % (r["id"], objections[1]), "--as", "dismissed", "--why", "no", "--by", "kim", "--target", pj.dir)[0] == 0
        assert run_hook(pj.dir) == (0, ""), "everything disposed: silent"
    # hunsu's probe (HUNSU_SURVEY=1) runs the hook in an empty temporary project: the standing text, the same everywhere
    empty = tempfile.mkdtemp(prefix="dwitbuk-survey-")
    try:
        code, out = run_hook(empty, HUNSU_SURVEY="1")
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert code == 0 and ctx == session_start.STANDING, ctx
        assert "undisposed objection(s) in <review>" in ctx and "follow" in ctx and "dispose" in ctx and "nothing" in ctx, ctx
        assert not re.search(r"review-\d|\d+ undisposed|" + re.escape(HERE), ctx), ctx   # no live id, count or path
        assert run_hook(empty, HUNSU_SURVEY="1", AGENT_WORKER="1") == (0, ""), "a worker session: silent even under the probe"
        assert os.listdir(empty) == [], "nothing written"
    finally:
        shutil.rmtree(empty, ignore_errors=True)


def test_stop_hook_steps_aside_inside_a_worker_session_and_without_the_switch():
    with Project() as pj:
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")   # dirty
        hook = os.path.join(HERE, "hooks", "stop_eyes.py")
        def run_hook(payload, **env):
            done = subprocess.run([sys.executable, hook], input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, **env))
            return done.returncode, done.stdout + done.stderr
        assert run_hook({"cwd": pj.dir})[0] == 0, "no switch in the project: nothing runs"
        write(os.path.join(pj.dir, "hunsu.json"), {"settings": {"dwitbuk": {"stop-eyes": True}}})   # read where a person writes it
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

def test_verify_packet_tells_the_eyes_when_the_slice_is_a_refactoring():
    """A refactoring's eyes accepted a split that lost eleven docstrings: the contract said tests and bytes, nothing about words.
    The packet now carries the request's domain, and for `refactor` the instructions say what else to reject."""
    with Project() as pj:
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [], "touched": []}
        plain = dwitbuk.verify_packet(req)
        assert "domain" not in plain and "refactoring" not in plain["instructions"]
        ref = dwitbuk.verify_packet(dict(req, domain="refactor"))
        assert ref["domain"] == "refactor" and "This slice is a refactoring" in ref["instructions"] and "docstring" in ref["instructions"], ref["instructions"][-400:]


def test_the_eyes_leave_out_the_records_the_lock_declares():
    """The verify packet's `touched` and the late eyes' diff left out `.chongdae/`, `reviews/`, `.mangsang/` by name; now the
    lock's `record-paths` says which paths are records — mangsang's relations stay in a late-eyes diff on purpose (a
    confirmed quote is a claim about the tree), and without a lock the old names stand."""
    with Project() as pj:
        assert dwitbuk.record_paths(pj.dir) == (".chongdae/", ".claude/", ".dwitbuk/", ".mangsang/", "hunsu-conflicts.md", "hunsu-judgments.json", "hunsu.json",
                                              "hunsu.local.json", "hunsu.lock.json", "reviews/"), dwitbuk.record_paths(pj.dir)
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"alpha": [".alpha/", "alpha.json"], "mangsang": ["mangsang/", ".mangsang/"]}})
        assert dwitbuk.record_paths(pj.dir) == (".alpha/", ".chongdae/", ".claude/", ".dwitbuk/", ".mangsang/", "alpha.json", "hunsu-conflicts.md", "hunsu-judgments.json",
                                              "hunsu.json", "hunsu.local.json", "hunsu.lock.json", "mangsang/", "reviews/"), dwitbuk.record_paths(pj.dir)
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": ["a.py", ".alpha/x.json", "alpha.json", ".chongdae/run-1/tasks/T.json", "mangsang/relations/R-1.json"]}
        assert dwitbuk.verify_packet(req)["touched"] == ["a.py"], dwitbuk.verify_packet(req)["touched"]


def test_a_verifier_finding_whose_quote_is_another_hands_or_nowhere_is_unfounded_and_a_reject_on_it_is_an_accept():
    """guin-site run a0ec, cache-build (10-15): the verifier rejected with claim-unverified, `where` "built.verified[0] and
    built.non-claims", quoting "`built.non-claims` says: `I did not run the whole suite.`" — a sentence only the tests writer
    said (`tests_non_claims.cache-tests[8]`); the builder had run the full suite and it passed. A quoted span is checked against
    the request: only in another hand's field while the finding charges the builder, or nowhere at all, is unfounded — kept
    beside the verdict, not under it. And a claim-unverified about a check chongdae itself saw pass is unfounded, unless it
    quotes the contract sentence the check is said not to decide."""
    with Project() as pj:
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "run": "run-1", "task": "cache-build", "target": pj.dir,
               "contract": {"Q1": "## Q1\n\nThe snapshot key carries the deployed version."}, "checks": [["python3", "tests/run.py", "--all"]],
               "touched": ["a.py"], "built": {"summary": "the full check passes", "verified": [{"check": "python3 tests/run.py --all", "exit": 0}],
                                              "non-claims": ["I didn't run the TypeScript type-check."]},
               "tests_non_claims": {"cache-tests": ["'tests/run.py --all passes' — I did not run the whole suite. I ran RevisionTests."]}}
        p = dwitbuk.verify_packet(req)
        mis = {"kind": "claim-unverified", "where": "built.verified[0] and built.non-claims",
               "record_quote": "`built.verified` claims `python3 tests/run.py --all` exited 0, while `built.non-claims` says: `I did not run the whole suite.`",
               "tree_quote": "`tests/run.py`: runs every group", "why": "the report contradicts itself"}
        assert dwitbuk.quoted_spans(mis, p) == ["python3 tests/run.py --all", "I did not run the whole suite"], "field names are where, not what"
        assert "only in tests_non_claims" in dwitbuk.unfounded(mis, p)
        out = dwitbuk.weigh({"verdict": "reject", "findings": [mis], "summary": "s"}, p)
        assert out["verdict"] == "accept" and out["findings"] == [] and out["unfounded"][0]["where"] == mis["where"], out
        assert "counted as accept" in out["summary"] and "the eyes said: s" in out["summary"], out["summary"]
        # the same sentence, quoted as the tests writer's in a finding that does not charge the builder, stands
        about_tests = dict(mis, where="tests_non_claims.cache-tests[0]", record_quote="the tests writer says `I did not run the whole suite.`")
        assert dwitbuk.unfounded(about_tests, p) is None
        # a span the request does not hold anywhere: unfounded; one the builder's report holds: founded
        assert "nowhere in the request" in dwitbuk.unfounded(dict(mis, record_quote="`I ran nothing at all`"), p)
        founded = {"kind": "plan-vs-code", "where": "contract.Q1; a.py", "record_quote": "`The snapshot key carries the deployed version.`",
                   "tree_quote": "x = 2", "why": "no version in the key"}
        assert dwitbuk.unfounded(founded, p) is None
        out = dwitbuk.weigh({"verdict": "reject", "findings": [founded, mis]}, p)
        assert out["verdict"] == "reject" and out["findings"] == [founded] and len(out["unfounded"]) == 1, "a founded finding still rejects"
        # a quote with no backticks is not checked: nothing says which words are the record's
        assert dwitbuk.unfounded(dict(founded, record_quote="the key carries the version"), p) is None
        # chongdae itself ran the check and saw exit 0, nothing changed since: whether it passed is not the eyes' to doubt
        ran = {"kind": "claim-unverified", "where": "built.verified[0]", "record_quote": "`python3 tests/run.py --all` exit 0",
               "tree_quote": "tests/run.py", "why": "cannot tell it ran"}
        ck = [{"command": "python3 tests/run.py --all", "exit": 0, "tail": ["OK"], "changed_since": []}]
        assert dwitbuk.unfounded(ran, p) is None, "without `checked` the claim is the builder's word"
        pc = dwitbuk.verify_packet(dict(req, checked=ck))
        assert "saw exit 0" in dwitbuk.unfounded(ran, pc)
        assert dwitbuk.unfounded(ran, dwitbuk.verify_packet(dict(req, checked=[dict(ck[0], changed_since=["a.py"])]))) is None, "changed since: it could break"
        assert dwitbuk.unfounded(ran, dwitbuk.verify_packet(dict(req, checked=[dict(ck[0], exit=1, expect="fail")]))) is None, "a red run is no pass"
        decides = dict(ran, record_quote="`python3 tests/run.py --all` is cited for `The snapshot key carries the deployed version.`")
        assert dwitbuk.unfounded(decides, pc) is None, "whether the check decides a contract sentence stays the eyes' to judge"
        # the worker applies it: a recorded reject on the misattributed quote comes out an accept, the finding kept beside it
        d = tempfile.mkdtemp(prefix="eyes-")
        try:
            reqf, resp = os.path.join(d, "req.json"), os.path.join(d, "resp.json")
            write(reqf, req)
            def fake(packet, schema, args):
                assert packet["tests_non_claims"]["whose"] == dwitbuk.TESTS_NON_CLAIMS_WHOSE
                return {"verdict": "reject", "findings": [mis], "summary": "s"}
            old_claude, old_argv = w.claude, sys.argv
            w.claude, sys.argv = fake, ["eyes_worker.py", "--request", reqf, "--response", resp]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    assert w.main() == 0
            finally:
                w.claude, sys.argv = old_claude, old_argv
            got = json.load(io.open(resp, encoding="utf-8"))
            assert got["verdict"] == "accept" and got["findings"] == [] and got["unfounded"][0]["unfounded"].startswith("quotes `I did not run"), got
        finally:
            shutil.rmtree(d, ignore_errors=True)


def test_a_documents_or_records_task_with_no_check_is_said_not_charged_and_its_old_carry_stops():
    """guin-site review a3c2 (10-13): of its twelve objections five were "no check decides this task" — four on tasks that
    wrote only documents or records (a first post's Done line in ATPROTO.md, `hunsu lock`, a Cirrus note, a contract and its
    quibble); three of those were carries from runs closed the day before. A task whose files are all documents or records,
    that declares itself so, or a quibble's, has nothing a check could run on: an observation. A carry raised before that was
    known stops; a session task that also touched code is still charged."""
    with Project() as pj:
        nc = "no check decides this task; done means the agent said so"
        def session_run(rid, tasks):
            root = os.path.join(pj.dir, ".chongdae", rid)
            write(os.path.join(root, "plan.json"), {"artifact-type": "chongdae/plan@1", "goal": rid, "kind": "session", "tasks": []})
            write(os.path.join(root, "state.json"), {"artifact-type": "chongdae/run@1", "status": "complete"})
            for tid, (extra, record) in tasks.items():
                write(os.path.join(root, "tasks", tid + ".json"), {"artifact-type": "chongdae/task@1", "status": "done", "non-claims": [nc],
                      "def": {"id": tid, "role": "session", "checks": [], **extra}, **record})
        session_run("run-20260101-000001-aaaa", {"first-post-done": ({"scope": ["plan/ATPROTO.md"]}, {"touched": ["plan/ATPROTO.md"]})})
        session_run("run-20260101-000002-bbbb", {"plugin-lock": ({"scope": ["hunsu.json", "hunsu.lock.json"]}, {"touched": []})})
        session_run("run-20260101-000003-cccc", {"ops": ({"scope": ["plan/ATPROTO.md"]}, {"touched": ["plan/ATPROTO.md", "scripts/setup.mjs"]}),
                                                 "decide": ({"domain": "doc"}, {"touched": []})})
        session_run("run-20260101-000004-dddd", {"q": ({"role": "quibble"}, {"touched": []})})
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"mangsang": ["mangsang/", ".mangsang/"]}})   # what the lock says is a record
        assert dwitbuk.documents_or_records(["plan/ATPROTO.md", "./README.md", "hunsu.lock.json", "mangsang/relations/R-1.json", "mangsang"], pj.dir)
        assert not dwitbuk.documents_or_records(["plan/ATPROTO.md", "scripts/setup.mjs"], pj.dir) and not dwitbuk.documents_or_records([], pj.dir)
        # the first review was written before 1.14.0: the first two runs' charges were objections, never disposed
        pj.reporter([{"kind": "non-claim", "where": "run-20260101-000001-aaaa", "text": "first-post-done: " + nc},
                     {"kind": "non-claim", "where": "run-20260101-000002-bbbb", "text": "plugin-lock: " + nc}], "chongdae")
        assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
        r = pj.latest()
        assert [dwitbuk.layer(f) for f in r["findings"]] == ["observation", "observation"], r["findings"]
        for f in r["findings"]:
            f["layer"] = "objection"
        write(os.path.join(pj.dir, dwitbuk.REVIEWS, r["id"] + ".json"), r)
        # the next review: those runs are closed (not reported again), two more are
        import time; time.sleep(1.1)
        pj.reporter([{"kind": "non-claim", "where": "run-20260101-000003-cccc", "text": "ops: " + nc},
                     {"kind": "non-claim", "where": "run-20260101-000003-cccc", "text": "decide: " + nc},
                     {"kind": "non-claim", "where": "run-20260101-000004-dddd", "text": "q: " + nc}], "chongdae")
        code, out = run("review", "--target", pj.dir)
        r2 = pj.latest()
        assert not any(f["kind"] == "undisposed" for f in r2["findings"]), "a documents-or-records task's old charge is not carried"
        layers = {f["where"]: dwitbuk.layer(f) for f in r2["findings"] if f["kind"] == "non-claim"}
        assert layers == {"run-20260101-000003-cccc": "objection", "run-20260101-000004-dddd": "observation"}, layers   # ops touched a script
        assert "1 objection(s) (non-claim 1)" in out, out


def test_review_and_the_session_start_line_count_each_open_charge_once_by_the_kind_it_makes():
    """guin-site review a3c2: chongdae's close said "cq-failed 2, non-claim 7, undisposed 3" and the next session start
    "cq-failed 2, non-claim 10" for the same twelve objections — review counted a carry as `undisposed`, the hook as the kind
    it carries. One rule, one text: each open objection once, under the kind of the charge it makes, then how many are carried."""
    open_ = [{"kind": "cq-failed", "where": "a", "text": "x"}, {"kind": "non-claim", "where": "r1", "text": "y"},
             {"kind": "undisposed", "where": "r2", "text": "z", "carries": ["non-claim", "r2", "z"]}]
    assert dwitbuk.count_text(open_) == "cq-failed 1, non-claim 2; 1 of them carried, already in the count"
    assert dwitbuk.count_text(open_[:2]) == "cq-failed 1, non-claim 1" and dwitbuk.count_text([]) == "none"
    hook = os.path.join(HERE, "hooks", "session_start.py")
    with Project() as pj:
        pj.reporter([{"kind": "left-open", "where": "run-1/T", "text": "left open"}, {"kind": "stale", "where": "R-1", "text": "stale"}])
        assert run("review", "--target", pj.dir)[0] == 0
        import time; time.sleep(1.1)
        pj.reporter([{"kind": "stale", "where": "R-1", "text": "stale"}])
        code, out = run("review", "--target", pj.dir)
        assert "2 objection(s) (left-open 1, stale 1; 1 of them carried, already in the count)" in out, out
        done = subprocess.run([sys.executable, hook], input=json.dumps({"cwd": pj.dir}), capture_output=True, text=True, encoding="utf-8",
                              env={k: v for k, v in os.environ.items() if k != "AGENT_WORKER"})
        ctx = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "2 undisposed objection(s) in %s (left-open 1, stale 1; 1 of them carried, already in the count)" % pj.latest()["id"] in ctx, ctx


def test_a_delegated_disposal_says_who_handed_it_off_and_where_they_agreed():
    """guin-site review a3c2: all twelve objections were accepted by delegation with `by: null` — the owner's "뒷북 검토
    진행" only in each reason's prose, because `--by` with `--delegated` was refused. No person read the finding, so `by`
    stays null; who handed it off is `delegated-by`, and where they said so `approved-in`."""
    with Project() as pj:
        pj.reporter([{"kind": "unattributed", "where": "run-1/S1", "text": "no touched"}])
        run("review", "--since", pj.base, "--target", pj.dir)
        r = pj.latest()
        code, out = run("dispose", "%s/0" % r["id"], "--as", "accepted", "--delegated", "the session read it", "--by", "lee",
                        "--approved-in", "source:at-65", "--target", pj.dir)
        d = pj.latest()["findings"][0]["disposition"]
        assert code == 0 and d["by"] is None and d["delegated-by"] == "lee" and d["approved-in"] == "source:at-65", d
        assert "(delegated by lee; approved in source:at-65)" in out, out
        assert run("dispose", "%s/0" % r["id"], "--as", "accepted", "--delegated", "x", "--approved-in", "yes", "--target", pj.dir)[0] != 0, "a source, not a word"


def test_an_accept_says_what_the_eyes_read_and_one_that_read_nothing_of_the_tree_says_so():
    """guin-site run a0ec, cache-build: the second verifier's first output was `{"verdict":"accept","findings":[]}`, then one
    `git diff`, then the same verdict — 607 output tokens on exactly the input the first verifier rejected. What the eyes read
    is kept beside the verdict (`read`, from the stream the worker keeps); an accept that read nothing of the tree, or only the
    diff while the contract names behaviour, stays an accept and says so in `non-claims`. A reject is not touched."""
    with Project() as pj:
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "run": "run-1", "task": "cache-build",
               "brief": "key the cache by version", "contract": {"Q-cache": "the snapshot key carries the deployed version"},
               "checks": [["python3", "tests/run.py"]], "tests": ["tests/test_read.py"], "touched": [], "touched_since": ["a.py"],
               "built": {"summary": "built", "verified": [], "non-claims": []}}
        reqf, resp = os.path.join(pj.dir, "local", "req.json"), os.path.join(pj.dir, "local", "resp.json")
        write(reqf, req)
        verdict = '{"verdict":"accept","findings":[]}'
        def codex_item(n, kind, **kw):
            return json.dumps({"type": "item.completed", "item": dict(id="item_%d" % n, type=kind, **kw)})
        def shell(cmd):
            return "/bin/zsh -lc %s" % json.dumps(cmd).replace('"', "'")
        streams = {
            "a0ec": [codex_item(0, "agent_message", text=verdict),
                     codex_item(1, "command_execution", command=shell("git status --short && git diff -- a.py && git diff --stat"), aggregated_output="+x = 2", exit_code=0),
                     codex_item(2, "agent_message", text=verdict)],
            "nothing": [codex_item(0, "agent_message", text=verdict)],
            "read": [codex_item(0, "command_execution", command=shell("sed -n '1,80p' a.py && rg -n key tests"), aggregated_output="x = 2", exit_code=0),
                     codex_item(1, "agent_message", text=verdict)],
            "failed": [codex_item(0, "command_execution", command=shell("sed -n '1,80p' a.py"), aggregated_output="", exit_code=1),
                       codex_item(1, "agent_message", text=verdict)],
            "claude": [json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Let me read the file."},
                                                                                 {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": pj.dir + "/a.py"}}]}}),
                       json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": verdict}]}})],
        }
        def answer(case, verdict_="accept", findings=()):
            def fake(packet, schema, args):
                path = os.path.join(os.path.dirname(args.response), "resp.transcript.jsonl")
                write(path, "\n".join(streams[case]) + "\n")
                return {"verdict": verdict_, "findings": list(findings), "worker": {"host": "codex", "model": "m", "transcript": "resp.transcript.jsonl"}}
            old_codex, old_argv = w.codex, sys.argv
            w.codex, sys.argv = fake, ["eyes_worker.py", "--request", reqf, "--response", resp, "--host", "codex"]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    assert w.main() == 0
            finally:
                w.codex, sys.argv = old_codex, old_argv
            return json.load(io.open(resp, encoding="utf-8"))
        got = answer("a0ec")
        assert got["verdict"] == "accept" and got["findings"] == [], got   # kept as accept: what was read is said, not judged
        assert got["read"]["commands"] == [{"command": "git status --short && git diff -- a.py && git diff --stat", "exit": 0}] and got["read"]["files"] == [], got["read"]
        assert got["read"].get("answered-before-reading") is True, got["read"]
        assert len(got["non-claims"]) == 1 and got["non-claims"][0].startswith("accepted without reading the touched files or the tests: the eyes read the diff only"), got
        assert "contract names behaviour" in got["non-claims"][0] and "gave the verdict before reading anything" in got["non-claims"][0], got
        got = answer("nothing")
        assert got["verdict"] == "accept" and got["non-claims"][0].startswith("accepted without reading the tree: the eyes opened no file and ran no command"), got
        got = answer("failed")   # a command that failed read nothing
        assert got["non-claims"][0].startswith("accepted without reading the tree"), got
        got = answer("read")
        assert "non-claims" not in got and got["read"]["commands"][0]["command"].startswith("sed -n"), got
        got = answer("claude")   # "Let me read the file." is a word on the way, not the verdict
        assert "non-claims" not in got and got["read"] == {"files": ["Read %s/a.py" % pj.dir], "commands": []}, got
        # the diff only, on a slice of documents with no tests: the diff is the whole of what the contract names
        write(reqf, dict(req, tests=[], touched_since=["plan/A.md"]))
        got = answer("a0ec")
        assert "non-claims" not in got and got["read"]["answered-before-reading"] is True, got
        write(reqf, req)
        anomaly = {"kind": "anomaly", "where": "a.py", "record_quote": "", "tree_quote": "x = 2", "why": "odd"}
        got = answer("nothing", "reject", [anomaly])
        assert got["verdict"] == "reject" and "non-claims" not in got and "read" not in got, got   # a reject stands on its quotes
        assert w.unread_accept(None, {}).startswith("accepted, and what the eyes read is not on record"), "no stream: not on record, not 'nothing'"


def test_a_grouped_non_claim_names_its_tasks_and_runs_and_the_count_is_of_distinct_charges():
    """guin-site 10-15: "no check decides this task [x2]" stood for eight tasks across two runs (a0ec) and again for one task
    (b3f0); the session told the owner "5건" when three charges were open (reviews 666e, 4a23). The tasks and the runs are
    said in words, struck from the charge's identity like `[x2]` was — an `[x2]` review's answer still answers it — and the
    count is of distinct charges, carries said as already included."""
    with Project() as pj:
        nc = "no check decides this task; done means the agent said so"
        a0ec, b3f0 = "run-20261015-054352-a0ec", "run-20261015-064403-b3f0"
        pj.run_record(a0ec, {t: {"status": "done"} for t in ("cache-contract", "cache-tests", "cache-build")})
        pj.run_record(b3f0, {"deploy": {"status": "done"}})
        # a review 1.13.0 wrote: the a0ec charge as `[x2]`, answered
        old = {"artifact-type": "dwitbuk/review@1", "id": "review-20261015-154243-666e", "since": pj.base, "head": pj.base,
               "findings": [{"kind": "non-claim", "where": a0ec, "layer": "objection", "text": "no check decides this task  [x2]",
                             "disposition": {"as": "accepted", "why": "the owner read them", "by": "lee"}}]}
        write(os.path.join(pj.dir, dwitbuk.REVIEWS, old["id"] + ".json"), old)
        pj.reporter([{"kind": "non-claim", "where": a0ec, "text": "%s: %s" % (t, nc)} for t in ("cache-contract", "cache-tests", "cache-build")]
                    + [{"kind": "non-claim", "where": b3f0, "text": "deploy: " + nc}], "chongdae")
        code, out = run("review", "--target", pj.dir)
        r = pj.latest()
        texts = {f["where"]: f["text"] for f in r["findings"] if f["kind"] == "non-claim"}
        assert texts == {a0ec: "no check decides this task  [tasks: cache-contract (%s), cache-tests (%s), cache-build (%s); also in other runs: deploy (%s)]"
                               % (a0ec, a0ec, a0ec, b3f0),
                         b3f0: "no check decides this task  [tasks: deploy (%s); also in other runs: cache-contract (%s), cache-tests (%s), cache-build (%s)]"
                               % (b3f0, a0ec, a0ec, a0ec)}, texts
        assert not any("[x" in t for t in texts.values()), texts
        mine = next(f for f in r["findings"] if f["where"] == a0ec)
        assert dwitbuk.identity(mine) == dwitbuk.identity(old["findings"][0]) == ("non-claim", a0ec, "no check decides this task"), mine
        assert mine["disposition"]["why"] == "the owner read them", mine   # the `[x2]` answer answers the reworded charge
        assert "1 objection(s) (non-claim 1)" in out, out   # one open: b3f0's — not 2+2+1
        # the next review: b3f0's charge is carried; one more charge is new — two open, the carry counted once, said as included
        import time; time.sleep(1.1)
        pj.reporter([{"kind": "stale", "where": "R-1", "text": "stale"}], "chongdae")
        code, out = run("review", "--target", pj.dir)
        assert "2 objection(s) (non-claim 1, stale 1; 1 of them carried, already in the count)" in out, out
        carry = next(f for f in pj.latest()["findings"] if f["kind"] == "undisposed")
        assert dwitbuk.charge(carry) == ("non-claim", b3f0, "no check decides this task"), carry
    # two copies of one charge are one thing owed
    a = {"kind": "non-claim", "where": "run-1", "text": "no check decides this task  [task T1]"}
    b = {"kind": "undisposed", "where": "run-1", "text": "no check decides this task  [x2]", "carries": ["non-claim", "run-1", "no check decides this task"]}
    assert dwitbuk.count_text([a, b]) == "non-claim 1", dwitbuk.count_text([a, b])
    assert len(dwitbuk.distinct([a, b])) == 1


def test_a_grouped_non_claim_names_each_task_beside_its_own_run():
    """guin-site 10-16: review f614 said `[task lexicon-descriptions; in 2 runs: run-…de3e, run-…ddee]` of a task only ddee
    has, and ee97 listed b3f0 beside de3e's tasks — 1.14.0 listed the runs sharing the clause text, and the line read as the
    task in each. Each task is now named with its own run; 1.14.0's form and `[xN]` stay struck from the charge, so their
    answers still answer it, and a carry of the 1.14.0 form keeps none of its misleading list."""
    with Project() as pj:
        nc = "no check decides this task; done means the agent said so"
        b3f0, de3e, ddee = "run-20261015-064403-b3f0", "run-20261015-094800-de3e", "run-20261016-022709-ddee"
        pj.run_record(b3f0, {"deploy": {"status": "done"}})
        pj.run_record(de3e, {t: {"status": "done"} for t in ("plugins-lock", "site-build-stale")})
        pj.run_record(ddee, {"lexicon-descriptions": {"status": "done"}})
        # the shapes 1.14.0 wrote (f614's and ee97's text, verbatim): ddee's answered, b3f0's open
        old = {"artifact-type": "dwitbuk/review@1", "id": "review-20261016-113225-f614", "since": pj.base, "head": pj.base,
               "findings": [{"kind": "non-claim", "where": ddee, "layer": "objection", "text": "no check decides this task  [task "
                             "lexicon-descriptions; in 2 runs: %s, %s]" % (de3e, ddee),
                             "disposition": {"as": "accepted", "why": "a lexicon entry is prose", "by": "lee"}},
                            {"kind": "non-claim", "where": b3f0, "layer": "objection",
                             "text": "no check decides this task  [task deploy; in 2 runs: %s, %s]" % (b3f0, de3e)}]}
        write(os.path.join(pj.dir, dwitbuk.REVIEWS, old["id"] + ".json"), old)
        ee97 = {"kind": "non-claim", "where": de3e, "text": "no check decides this task  [tasks plugins-lock, site-build-stale; in 2 runs: %s, %s]" % (b3f0, de3e)}
        pj.reporter([{"kind": "non-claim", "where": de3e, "text": "%s: %s" % (t, nc)} for t in ("plugins-lock", "site-build-stale")]
                    + [{"kind": "non-claim", "where": ddee, "text": "lexicon-descriptions: " + nc}], "chongdae")
        code, out = run("review", "--target", pj.dir)
        r = pj.latest()
        texts = {f["where"]: f["text"] for f in r["findings"] if f["kind"] == "non-claim"}
        assert texts == {ddee: "no check decides this task  [tasks: lexicon-descriptions (%s); also in other runs: plugins-lock (%s), site-build-stale (%s)]"
                               % (ddee, de3e, de3e),
                         de3e: "no check decides this task  [tasks: plugins-lock (%s), site-build-stale (%s); also in other runs: lexicon-descriptions (%s)]"
                               % (de3e, de3e, ddee)}, texts
        # every task is named beside the run that has it, and no other
        defs = dwitbuk.run_tasks(pj.dir)
        for text in texts.values():
            pairs = re.findall(r"([\w-]+) \((run-[\w-]+)\)", text)
            assert len(pairs) == 3 and all(task in defs[run_] for task, run_ in pairs), (text, pairs)
        mine = next(f for f in r["findings"] if f["kind"] == "non-claim" and f["where"] == ddee)
        assert dwitbuk.identity(mine) == dwitbuk.identity(old["findings"][0]) == ("non-claim", ddee, "no check decides this task"), mine
        assert mine["disposition"]["why"] == "a lexicon entry is prose", mine   # f614's answer answers the reworded charge
        assert dwitbuk.identity(next(f for f in r["findings"] if f["where"] == de3e and f["kind"] == "non-claim")) == dwitbuk.identity(ee97)
        carry = next(f for f in r["findings"] if f["kind"] == "undisposed")
        assert carry["where"] == b3f0 and carry["text"] == "no check decides this task", carry   # 1.14.0's list struck from the carry
        assert dwitbuk.charge(carry) == dwitbuk.identity(old["findings"][1]), carry
        assert "2 objection(s) (non-claim 2; 1 of them carried, already in the count)" in out, out
    # one run alone: its tasks, no run named
    one = {"run-1": [{"text": "T1: x"}, {"text": "T2: x"}]}
    assert dwitbuk.bearing(one["run-1"], one, "run-1") == "  [tasks T1, T2]"


HUNSU_FILES = ("hunsu-conflicts.md", "hunsu-judgments.json", "hunsu.json", "hunsu.local.json", "hunsu.lock.json")
HUNSU_LOOKALIKES = ("hunsu.py", "hunsu_helper.py", "hunsu-notes.md")


def test_Q_match_a_directory_entry_matches_itself_and_what_is_under_it_and_nothing_beside_it():
    assert hasattr(dwitbuk, "is_record"), "dwitbuk.is_record(path, entries) is the one rule"
    for path in ("mangsang", "mangsang/", "mangsang/relations/R-1.json", "./mangsang/relations/R-1.json", "mangsang\\relations\\R-1.json"):
        assert dwitbuk.is_record(path, ["mangsang/"]), path
    for path, entry in (("mangsang-extra/x.py", "mangsang/"), ("mangsangx", "mangsang/"), (".alpha-extra/y.py", ".alpha/"),
                        ("reviews2/a.json", "reviews/"), (".chongdae-notes.md", ".chongdae/"), ("x/mangsang/R.json", "mangsang/")):
        assert not dwitbuk.is_record(path, [entry]), (path, entry)
    assert dwitbuk.is_record(".alpha/x.json", [".alpha/"]) and dwitbuk.is_record(".chongdae/run-1/state.json", (".chongdae/",))


def test_Q_match_an_exact_entry_matches_that_path_and_paths_under_it_only():
    assert dwitbuk.is_record("alpha.json", ["alpha.json"]) and dwitbuk.is_record("./alpha.json", ["alpha.json"])
    assert dwitbuk.is_record("alpha.json/", ["alpha.json"]), "a trailing / on the path is ignored"
    assert dwitbuk.is_record("alpha.json/inner.txt", ["alpha.json"]), "an exact entry that is a directory: what is under it"
    assert dwitbuk.is_record("mangsang/relations/R-1.json", ["mangsang"]) and dwitbuk.is_record("mangsang", ["mangsang"])
    for path in ("alpha.jsonl", "alpha.json.py", "alpha.json~", "alpha", "beta/alpha.json"):
        assert not dwitbuk.is_record(path, ["alpha.json"]), path
    assert not dwitbuk.is_record("mangsang-extra/x.py", ["mangsang"])


def test_Q_match_a_hunsu_lookalike_is_never_a_record_of_any_hunsu_entry():
    for entry in HUNSU_FILES + ("hunsu",):
        for path in HUNSU_LOOKALIKES:
            assert not dwitbuk.is_record(path, [entry]), (path, entry)
    for path in HUNSU_LOOKALIKES:
        assert not dwitbuk.is_record(path, HUNSU_FILES), path
    for path in HUNSU_FILES:
        assert dwitbuk.is_record(path, HUNSU_FILES) and dwitbuk.is_record("./" + path, HUNSU_FILES), path


def test_Q_match_an_empty_entry_or_path_matches_nothing_and_entries_may_be_any_iterable():
    assert not dwitbuk.is_record("a.py", [""]) and not dwitbuk.is_record("", ["a.py", "mangsang/", ""]) and not dwitbuk.is_record("a.py", [])
    assert not dwitbuk.is_record("anything/at/all.py", [""])
    assert dwitbuk.is_record("reviews/r.json", (e for e in ["x/", "reviews/"])), "a generator of entries"
    assert dwitbuk.is_record("reviews/r.json", ("reviews/",)) is True and dwitbuk.is_record("a.py", ("reviews/",)) is False


def test_Q_hunsu_record_paths_names_hunsus_files_exactly_with_and_without_a_lock():
    with Project() as pj:
        rp = dwitbuk.record_paths(pj.dir)
        assert rp == (".chongdae/", ".claude/", ".dwitbuk/", ".mangsang/", "hunsu-conflicts.md", "hunsu-judgments.json", "hunsu.json",
                      "hunsu.local.json", "hunsu.lock.json", "reviews/"), rp
        assert isinstance(rp, tuple) and "hunsu" not in rp
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"alpha": [".alpha/", "alpha.json", "alpha.json"], "other": ["reviews/"]}})
        rp = dwitbuk.record_paths(pj.dir)
        assert rp == (".alpha/", ".chongdae/", ".claude/", ".dwitbuk/", "alpha.json") + HUNSU_FILES + ("reviews/",), rp
        assert rp == tuple(sorted(set(rp))) and "hunsu" not in rp
        for f in HUNSU_FILES:
            assert dwitbuk.is_record(f, rp), f
        for f in HUNSU_LOOKALIKES:
            assert not dwitbuk.is_record(f, rp), f


def test_Q_sites_documents_or_records_decides_records_by_the_one_rule():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"mangsang": ["mangsang/", ".mangsang/"]}})
        assert dwitbuk.documents_or_records(["hunsu.lock.json", "mangsang", "mangsang/relations/R-1.json"], pj.dir)
        assert dwitbuk.documents_or_records(["hunsu-notes.md", "hunsu.json"], pj.dir), "hunsu-notes.md is a document by its suffix"
        for code in ("hunsu.py", "hunsu_helper.py", "mangsang-extra/x.py"):
            assert not dwitbuk.documents_or_records(["hunsu.lock.json", code], pj.dir), code
            assert not dwitbuk.documents_or_records([code], pj.dir), code


def test_Q_sites_verify_packet_keeps_lookalikes_and_siblings_in_touched_with_their_diff():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 1\n")
        write(os.path.join(pj.dir, "alpha.jsonl"), "{}\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "lookalikes")
        since = git(pj.dir, "rev-parse", "HEAD")
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"alpha": [".alpha/", "alpha.json"]}})
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 2\n")
        write(os.path.join(pj.dir, "hunsu_helper.py"), "helper = 1\n")
        write(os.path.join(pj.dir, "hunsu-notes.md"), "notes line\n")
        write(os.path.join(pj.dir, "alpha.jsonl"), '{"l": 2}\n')
        write(os.path.join(pj.dir, ".alpha-extra", "y.py"), "sibling = 1\n")
        write(os.path.join(pj.dir, "alpha.json"), "{}\n")
        write(os.path.join(pj.dir, ".alpha", "x.json"), "{}\n")
        write(os.path.join(pj.dir, "hunsu.json"), "{}\n")
        kept = ["hunsu.py", "hunsu_helper.py", "hunsu-notes.md", "alpha.jsonl", ".alpha-extra/y.py"]
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": kept + ["alpha.json", ".alpha/x.json", ".chongdae/run-1/tasks/T.json", "hunsu.json"], "since": {".": since}}
        p = dwitbuk.verify_packet(req)
        assert sorted(p["touched"]) == sorted(kept), p["touched"]
        d = p["diff"]
        assert "-hp = 1" in d and "+hp = 2" in d, d
        assert "helper = 1" in d and "notes line" in d and '{"l": 2}' in d and "sibling = 1" in d, d
        # the request's excluded record-paths: chongdae's own runs go, everything else is kept, by the same rule
        env = dwitbuk.verify_packet(dict(req, touched=[], excluded={"record-paths": ["hunsu.json", ".chongdae/run-1/state.json", ".chongdae", ".chongdae-notes.md"]}))
        assert sorted(env["excluded"]) == [".chongdae-notes.md", "hunsu.json"], env.get("excluded")


def late_packet(pj, folder):
    assert run("eyes", "request", "--out", folder, "--target", pj.dir)[0] == 0
    return dwitbuk.load(os.path.join(folder, "eyes-request.json"))


def test_Q_sites_eyes_request_diff_and_new_files_leave_out_only_exact_records():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 1\n")
        for name in ("alpha.jsonl", "alpha.json", "x1.json"):
            write(os.path.join(pj.dir, name), '"old"\n')
        write(os.path.join(pj.dir, ".alpha-extra", "y.py"), "s = 1\n")
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"alpha": [".alpha/", "alpha.json", "x[1].json"], "mangsang": ["mangsang/", ".mangsang/"]}})
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base two")
        run("review", "--target", pj.dir)
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 2\n")
        write(os.path.join(pj.dir, "hunsu_helper.py"), "helper = 1\n")
        write(os.path.join(pj.dir, "hunsu-notes.md"), "notes\n")
        write(os.path.join(pj.dir, "hunsu.json"), "{}\n")
        write(os.path.join(pj.dir, "alpha.jsonl"), '"new jsonl"\n')
        write(os.path.join(pj.dir, "alpha.json"), '"new json"\n')
        write(os.path.join(pj.dir, "x1.json"), '"new x1"\n')
        write(os.path.join(pj.dir, ".alpha-extra", "y.py"), "s = 2\n")
        write(os.path.join(pj.dir, ".alpha", "z.json"), "{}\n")
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet = late_packet(pj, folder)
        d, new = packet["diff"], packet["new_files"]
        assert "+hp = 2" in d, "a committed-then-changed hunsu.py is in the diff: " + d
        assert "hunsu_helper.py" in new and "hunsu-notes.md" in new, list(new)
        assert "hunsu.json" not in new and "b/hunsu.json" not in d, (list(new), d)
        assert '"new jsonl"' in d and "+s = 2" in d, "a same-prefix neighbour and a sibling directory are source: " + d
        assert '"new x1"' in d, "an entry is literal, never a glob: x[1].json does not leave out x1.json: " + d
        assert '"new json"' not in d and ".alpha/z.json" not in new, (d, list(new))
        assert not any(k.startswith(".dwitbuk/") for k in new)
        leaves = packet["diff_leaves_out"]
        assert "hunsu*" not in leaves and "hunsu" not in leaves, leaves
        assert set(leaves) == {".alpha", ".chongdae", ".claude", ".dwitbuk", ".mangsang", "alpha.json", "x[1].json", "reviews", ".dwitbuk/packet"} | set(HUNSU_FILES), leaves
    with Project() as pj:
        run("review", "--target", pj.dir)
        for name in HUNSU_LOOKALIKES:
            write(os.path.join(pj.dir, name), "fresh %s\n" % name)
        packet = late_packet(pj, os.path.join(pj.dir, ".dwitbuk", "packet"))
        for name in HUNSU_LOOKALIKES:
            assert name in packet["new_files"], (name, list(packet["new_files"]))


def test_Q_sites_source_state_changes_with_a_hunsu_lookalike_and_not_with_hunsus_own_files():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"pin": 1})
        write(os.path.join(pj.dir, "hunsu.json"), {"plugins": {}})
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "env")
        run("review", "--target", pj.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        for name in HUNSU_LOOKALIKES:
            eyes_answer(pj, folder)
            write(os.path.join(pj.dir, name), "changed %s\n" % name)
            code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
            assert code != 0 and "source changed" in out, (name, out)
        eyes_answer(pj, folder)
        write(os.path.join(pj.dir, "hunsu.json"), {"plugins": {"x": {}}})
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"pin": 2})
        write(os.path.join(pj.dir, "reviews", "note.json"), {"x": 1})
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code == 0, out


def test_Q_sites_source_state_in_a_non_git_project_prunes_only_record_directories():
    d = tempfile.mkdtemp(prefix="dwitbuk-nogit-")
    try:
        class P:
            dir = d
        write(os.path.join(d, "a.py"), "x = 1\n")
        for rel in ("hunsu_lib/x.py", ".claude-extra/y.py", "reviews2/a.py", "mangsang-extra/m.py", "hunsu.py"):
            write(os.path.join(d, rel), "old\n")
        run("review", "--target", d)
        folder = os.path.join(d, ".dwitbuk", "packet")
        for rel in ("hunsu_lib/x.py", ".claude-extra/y.py", "reviews2/a.py", "mangsang-extra/m.py", "hunsu.py"):
            eyes_answer(P, folder)
            write(os.path.join(d, rel), "changed\n")
            code, out = run("eyes", "consume", "--dir", folder, "--target", d)
            assert code != 0 and "source changed" in out, (rel, out)
        eyes_answer(P, folder)
        write(os.path.join(d, ".claude", "settings.json"), "{}\n")
        write(os.path.join(d, "hunsu.json"), "{}\n")
        code, out = run("eyes", "consume", "--dir", folder, "--target", d)
        assert code == 0, out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def stop_hook_touched(pj):
    """Run the stop hook in-process with a host-free worker; return (the touched the hook asked about, the packet it bound)."""
    from unittest.mock import patch
    from types import SimpleNamespace
    import stop_eyes
    real_run, real_packet = subprocess.run, dwitbuk.verify_packet
    seen = {}
    def packet(request):
        seen["touched"] = list(request["touched"])
        return real_packet(request)
    def host(argv, **kwargs):
        if len(argv) > 1 and str(argv[1]).endswith("eyes_worker.py"):
            request = dwitbuk.load(argv[argv.index("--request") + 1])
            seen["packet"] = request
            write(argv[argv.index("--response") + 1], {"request": dwitbuk.fingerprint(request), "findings": []})
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return real_run(argv, **kwargs)
    with patch.dict(os.environ, {"AGENT_WORKER": ""}), patch.object(sys, "stdin", io.StringIO(json.dumps({"cwd": pj.dir}))), \
            patch.object(subprocess, "run", host), patch.object(dwitbuk, "verify_packet", packet), \
            contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        stop_eyes.main()
    return seen.get("touched"), seen.get("packet")


def test_Q_sites_stop_hook_hands_a_dirty_hunsu_lookalike_to_the_eyes():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 1\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "hunsu.py")
        write(os.path.join(pj.dir, "hunsu.json"), {"settings": {"dwitbuk": {"stop-eyes": True}}})
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 2\n")
        write(os.path.join(pj.dir, "hunsu_helper.py"), "helper = 1\n")
        write(os.path.join(pj.dir, "hunsu-notes.md"), "notes\n")
        write(os.path.join(pj.dir, "hunsu-judgments.json"), "{}\n")
        write(os.path.join(pj.dir, "reviews2", "a.py"), "r = 1\n")
        touched, packet = stop_hook_touched(pj)
        assert touched is not None and packet is not None, "the hook reached the eyes"
        assert set(touched) == {"hunsu.py", "hunsu_helper.py", "hunsu-notes.md", "reviews2/a.py"}, touched
        assert set(HUNSU_LOOKALIKES) <= set(packet["touched"]), packet["touched"]
        leaves = [e.rstrip("/") for e in packet["diff_leaves_out"]]
        assert "hunsu" not in leaves and "hunsu*" not in leaves and set(HUNSU_FILES) <= set(leaves), packet["diff_leaves_out"]


def test_Q_sites_documents_or_records_a_neighbour_of_a_declared_file_is_not_a_record():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"alpha": ["alpha.json"]}})
        assert dwitbuk.documents_or_records(["alpha.json", "hunsu.json"], pj.dir), "the declared file and hunsu's own are records"
        for code in ("alpha.jsonl", "hunsu.json.bak"):
            assert not dwitbuk.documents_or_records([code], pj.dir), code
            assert not dwitbuk.documents_or_records(["alpha.json", code], pj.dir), code


def test_Q_sites_source_state_changes_with_a_neighbour_of_a_declared_file():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"alpha": ["alpha.json"]}})
        write(os.path.join(pj.dir, "alpha.json"), '"declared"\n')
        for name in ("alpha.jsonl", "hunsu.json.bak"):
            write(os.path.join(pj.dir, name), '"old"\n')
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "neighbours")
        run("review", "--target", pj.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        for name in ("alpha.jsonl", "hunsu.json.bak"):
            eyes_answer(pj, folder)
            write(os.path.join(pj.dir, name), '"changed %s"\n' % name)
            code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
            assert code != 0 and "source changed" in out, (name, out)
        eyes_answer(pj, folder)
        write(os.path.join(pj.dir, "alpha.json"), '"declared, changed"\n')
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code == 0, "the declared file itself is a record: " + out


def test_Q_sites_eyes_request_untracked_neighbours_of_record_entries_are_new_files():
    with Project() as pj:
        run("review", "--target", pj.dir)
        neighbours = ("reviews2/a.json", ".claude-extra/x.py", ".chongdae-notes.md", "hunsu.json.bak")
        for rel in neighbours:
            write(os.path.join(pj.dir, rel), '"fresh %s"\n' % rel)
        write(os.path.join(pj.dir, "hunsu.json"), "{}\n")
        packet = late_packet(pj, os.path.join(pj.dir, ".dwitbuk", "packet"))
        for rel in neighbours:
            assert rel in packet["new_files"], (rel, list(packet["new_files"]))
        assert "hunsu.json" not in packet["new_files"], list(packet["new_files"])


def test_Q_sites_stop_hook_hands_dirty_neighbours_of_record_entries_to_the_eyes():
    with Project() as pj:
        write(os.path.join(pj.dir, "alpha.json"), '"declared"\n')
        write(os.path.join(pj.dir, "alpha.jsonl"), '"old"\n')
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "alpha")
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"alpha": ["alpha.json"]}})
        write(os.path.join(pj.dir, "hunsu.json"), {"settings": {"dwitbuk": {"stop-eyes": True}}})
        write(os.path.join(pj.dir, "alpha.json"), '"declared, changed"\n')
        write(os.path.join(pj.dir, "alpha.jsonl"), '"new"\n')
        write(os.path.join(pj.dir, "hunsu.json.bak"), "{}\n")
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        touched, packet = stop_hook_touched(pj)
        assert touched is not None and packet is not None, "the hook reached the eyes"
        assert set(touched) == {"a.py", "alpha.jsonl", "hunsu.json.bak"}, touched


def test_Q_sites_stop_hook_hands_a_dirty_mangsang_record_to_verify_packet():
    with Project() as pj:
        write(os.path.join(pj.dir, "mangsang", "relations", "R-1.json"), {"id": "R-1", "v": 1})
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "relations")
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"mangsang": ["mangsang/", ".mangsang/"]}})
        write(os.path.join(pj.dir, "hunsu.json"), {"settings": {"dwitbuk": {"stop-eyes": True}}})
        write(os.path.join(pj.dir, "mangsang", "relations", "R-1.json"), {"id": "R-1", "v": 2})
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        touched, _ = stop_hook_touched(pj)
        assert touched is not None, "the hook reached the eyes"
        assert set(touched) == {"a.py", "mangsang/relations/R-1.json"}, touched


def test_Q_keep_a_change_under_mangsang_still_stales_a_late_eyes_answer_and_is_read():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"mangsang": ["mangsang/", ".mangsang/"]}})
        write(os.path.join(pj.dir, "mangsang", "relations", "R-1.json"), {"id": "R-1", "v": 1})
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "relations")
        run("review", "--target", pj.dir)
        write(os.path.join(pj.dir, "mangsang", "relations", "R-1.json"), {"id": "R-1", "v": 2})
        write(os.path.join(pj.dir, "mangsang", "relations", "R-2.json"), {"id": "R-2"})
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder)
        assert "b/mangsang/relations/R-1.json" in packet["diff"] and "mangsang/relations/R-2.json" in packet["new_files"], (packet["diff"], list(packet["new_files"]))
        assert set(packet["diff_leaves_out"]) == {".chongdae", ".claude", ".dwitbuk", ".mangsang", "reviews", ".dwitbuk/packet"} | set(HUNSU_FILES), packet["diff_leaves_out"]
        write(os.path.join(pj.dir, "mangsang", "relations", "R-3.json"), {"id": "R-3"})
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "source changed" in out, out
        # and the verify packet and documents_or_records still count mangsang/ a record
        assert dwitbuk.documents_or_records(["mangsang/relations/R-3.json"], pj.dir)
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": ["mangsang/relations/R-3.json", "hunsu.py"]}
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 1\n")
        assert dwitbuk.verify_packet(req)["touched"] == ["hunsu.py"]


def test_Q_keep_run_records_count_reviews_commits_do_not_and_the_packet_directory_is_left_out():
    with Project() as pj:
        pj.run_record("run-example", {"S1": {"status": "done", "touched": ["a.py"]}})
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 1\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "with run")
        run("review", "--target", pj.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder)
        write(os.path.join(folder, "scratch.txt"), "the packet directory's own files\n")
        git(pj.dir, "add", "reviews"); git(pj.dir, "commit", "-qm", "record only")
        assert run("eyes", "consume", "--dir", folder, "--target", pj.dir)[0] == 0
        eyes_answer(pj, folder)
        pj.run_record("run-example", {"S1": {"status": "failed", "touched": ["a.py"]}})
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "source changed" in out, out
        eyes_answer(pj, folder)
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 2\n")
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "source changed" in out, "hunsu.py beside the run records is source: " + out


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
