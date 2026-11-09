"""Self-check for dwitbuk. A temp git project with hand-written run records; every kind of finding fires once, dispositions carry.

  python test_dwitbuk.py
"""
import argparse
import contextlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))   # the source checkout: these tests, the project's records
PLUGIN = os.path.join(HERE, "plugin")   # the installed payload: what the tests exercise
sys.dont_write_bytecode = True   # running the self-check leaves no bytecode in the payload (a directory install copies what is there)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"   # nor do the hooks, engines and workers it starts
sys.path.insert(0, PLUGIN)
import dwitbuk  # noqa: E402
import eyes_worker as w  # noqa: E402
sys.path.insert(0, os.path.join(PLUGIN, "hooks"))
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



class Skip(unittest.SkipTest):
    """Raised by a test that cannot run on this host; the runner reports it as SKIP, never as PASS."""


@contextlib.contextmanager
def environ(**kv):
    """Set (a value) or unset (None) os.environ variables for the block, and put back exactly what was there."""
    saved = {k: os.environ.get(k) for k in kv}
    try:
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def made(path):
    os.makedirs(path, exist_ok=True)
    return path


def same(a, b):
    """Two paths name the same directory (normalized, real): a temp dir under /var is /private/var on macOS."""
    return a is not None and b is not None and os.path.realpath(os.path.normpath(a)) == os.path.realpath(os.path.normpath(b))


def stream(*events):
    return "".join(json.dumps(e) + "\n" for e in events)

def test_a_reporters_plugin_is_the_copy_from_the_marketplace_the_project_declares():
    """Matched by name alone, the first install record belonged to another project, and a review ran its 1.1.0 reporters."""
    home = tempfile.mkdtemp(prefix="dwitbuk-home-")
    codex = tempfile.mkdtemp(prefix="dwitbuk-codex-")
    old = os.environ.get("HUNSU_CLAUDE_DIR")
    try:
        with Project() as p, environ(AGENT_HOST="claude-code", HUNSU_CODEX_DIR=codex):
            os.environ["HUNSU_CLAUDE_DIR"] = home
            cache = {k: made(os.path.join(home, "cache", k)) for k in ("other/1.1.0", "mangsang/1.4.0", "mangsang/1.5.0")}   # installPaths that exist
            write(os.path.join(home, "plugins", "installed_plugins.json"), {"plugins": {
                "mangsang@other": [{"scope": "project", "projectPath": "/elsewhere", "installPath": cache["other/1.1.0"]}],
                "mangsang@mangsang": [{"scope": "project", "projectPath": "/third", "installPath": cache["mangsang/1.4.0"]},
                                      {"scope": "project", "projectPath": p.dir, "installPath": cache["mangsang/1.5.0"]}]}})
            write(os.path.join(p.dir, "hunsu.json"), {"plugins": {"mangsang": {"marketplace": "mangsang"}}})
            assert same(dwitbuk.plugin_root(p.dir, "mangsang"), cache["mangsang/1.5.0"])
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
        shutil.rmtree(codex, ignore_errors=True)


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
        reads = dwitbuk.load(os.path.join(PLUGIN, manifest))["reads"]
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
        assert ".chongdae/" in packet["diff_leaves_out"] and ".chongdae" not in packet["diff_leaves_out"] and packet["runs"][0]["tasks"][0]["state"]["touched"] == ["a.py", "proposals.json"]
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
        proc = subprocess.Popen([sys.executable, "-c", script, "eyes", "consume", "--dir", first, "--target", pj.dir], cwd=PLUGIN,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            assert proc.stdout.readline().strip() == "ready"
            attempt = subprocess.run([sys.executable, os.path.join(PLUGIN, "dwitbuk.py"), "eyes", "consume", "--dir", second, "--target", pj.dir],
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
        # (11-09, D2: the packet names what was left out and holds none of its changes — another open task's, maybe)
        env = dwitbuk.verify_packet(dict(req, touched=[], excluded={"record-paths": ["hunsu.json", ".chongdae/run-1/state.json"]}))
        assert env["touched"] == [] and env["excluded"] == ["hunsu.json"], env.get("excluded")
        assert "excluded_diff" not in env and '{"mangsang": {}}' not in json.dumps(env), sorted(env)
        assert "by rule" in env["instructions"] and "no record-vs-tree finding" in env["instructions"]
        assert "not this task's changes" in env["instructions"] and "none of their changes" in env["instructions"], env["instructions"]
        assert "excluded_diff" not in env["instructions"], env["instructions"]
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
    hook = os.path.join(PLUGIN, "hooks", "session_start.py")
    def run_hook(cwd, **env):
        # a normal session unless the call says AGENT_WORKER itself: the parent may be a worker session
        child = {k: v for k, v in os.environ.items() if k != "AGENT_WORKER"}
        done = subprocess.run([sys.executable, hook], input=json.dumps({"cwd": cwd}), capture_output=True, text=True, encoding="utf-8", env=dict(child, **env))
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
        hook = os.path.join(PLUGIN, "hooks", "stop_eyes.py")
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
        # 11-06 (D1): a record path a task's scope names is the task's work; only chongdae's runs and the host's settings go
        assert dwitbuk.verify_packet(req)["touched"] == ["a.py", ".alpha/x.json", "alpha.json", "mangsang/relations/R-1.json"], dwitbuk.verify_packet(req)["touched"]


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
            # (11-09, D1-3: a.py is modified, so in must_open; the eyes' session Read it, else the accept would not stand)
            opened = json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": pj.dir + "/a.py"}}]}})
            def fake(packet, schema, args):
                assert packet["tests_non_claims"]["whose"] == dwitbuk.TESTS_NON_CLAIMS_WHOSE
                assert packet.get("must_open") == ["a.py"], packet.get("must_open")
                write(os.path.join(os.path.dirname(args.response), "resp.transcript.jsonl"), opened + "\n")
                return {"verdict": "reject", "findings": [mis], "summary": "s", "worker": {"host": "claude-code", "model": "m", "transcript": "resp.transcript.jsonl"}}
            def unrecorded(packet, schema, args):
                return {"verdict": "reject", "findings": [mis], "summary": "s"}
            def worker(host):
                old_claude, old_argv = w.claude, sys.argv
                w.claude, sys.argv = host, ["eyes_worker.py", "--request", reqf, "--response", resp]
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        assert w.main() == 0
                finally:
                    w.claude, sys.argv = old_claude, old_argv
                return json.load(io.open(resp, encoding="utf-8"))
            got = worker(fake)
            assert got["verdict"] == "accept" and got["findings"] == [] and got["unfounded"][0]["unfounded"].startswith("quotes `I did not run"), got
            assert got["read"]["files"] == ["Read %s/a.py" % pj.dir] and "unread" not in got and "answered" not in got, got
            # with no transcript what the eyes opened is not on record: the reject-on-unfounded, counted as accept, is not an accept
            got = worker(unrecorded)
            assert "verdict" in got and got["verdict"] is None and got["answered"] == "accept" and got["unread"] == ["a.py"] and got["findings"] == [], got
            assert got["unfounded"][0]["unfounded"].startswith("quotes `I did not run") and "read" not in got, got
            assert got["summary"].startswith("not an accept:") and "`a.py`" in got["summary"] and "not on record" in got["summary"], got["summary"]
            assert "counted as accept" in got["summary"], got["summary"]
            assert not [n for n in got.get("non-claims") or [] if n.startswith("accepted")], got.get("non-claims")
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


OBS = {"layer": "observation"}


def layered_run(pj, rid, tasks):
    """A session run's records as chongdae 2.0.0 writes them: one task file each, `def` with its role, `status`, `touched`,
    the non-claims on the task (and the lock's provider for a hired role, `performed_by`)."""
    root = os.path.join(pj.dir, ".chongdae", rid)
    write(os.path.join(root, "plan.json"), {"artifact-type": "chongdae/plan@1", "goal": rid, "kind": "session", "tasks": []})
    write(os.path.join(root, "state.json"), {"artifact-type": "chongdae/run@1", "status": "complete"})
    for tid, (role, touched, ncs) in tasks.items():
        write(os.path.join(root, "tasks", tid + ".json"),
              {"artifact-type": "chongdae/task@1", "status": "done", "non-claims": list(ncs), "touched": list(touched),
               "def": {"id": tid, "role": role, "checks": [], "closes": ["Q-" + tid]},
               **({"performed_by": {"provider": "command", "as": role}} if role not in ("session", "subagent") else {})})


def test_a_reporters_explicit_observation_goes_through_non_claim_grouping_only_when_every_constituent_says_so():
    """Before 2.0.2, collect() kept a reporter's `"layer": "observation"` and grouping non-claims by clause rebuilt each one
    without it: in a temp project (2026-11-03) a typed `stale` stayed an observation and a typed `non-claim` came out a charge.
    The reporter's layer goes through grouping only when every non-claim a grouped one stands for carries an explicit
    observation; a constituent with no layer, an unknown one, or an explicit objection leaves the group an objection — one run
    at a time, so a run whose copy of the clause is typed lends nothing to a run whose copy is not."""
    with Project() as pj:
        pj.reporter([
            {"kind": "stale", "where": "R-1", "text": "typed stale", **OBS},
            {"kind": "non-claim", "where": "run-a", "text": "T1: (provider) typed limit", **OBS},
            {"kind": "non-claim", "where": "run-a", "text": "T2: (provider) typed limit", **OBS},
            {"kind": "non-claim", "where": "run-b", "text": "T3: (provider) typed limit"},                       # same clause, untyped
            {"kind": "non-claim", "where": "run-c", "text": "T4: (provider) half typed", **OBS},
            {"kind": "non-claim", "where": "run-c", "text": "T5: (provider) half typed"},                        # mixed: one unknown
            {"kind": "non-claim", "where": "run-d", "text": "T6: (provider) disputed", **OBS},
            {"kind": "non-claim", "where": "run-d", "text": "T7: (provider) disputed", "layer": "objection"},    # mixed: one objection
            {"kind": "non-claim", "where": "run-e", "text": "no long list was tried — 2 task(s): T8, T9", **OBS},  # the reporter's own grouping
            {"kind": "non-claim", "where": "run-f", "text": "T10: (provider) odd", "layer": "info"},             # not a layer: unknown
            {"kind": "non-claim", "where": "run-g", "text": "T11: (provider) said a charge", "layer": "objection"},
        ], "chongdae")
        code, out = run("review", "--since", pj.base, "--target", pj.dir)
        r = pj.latest()
        got = {f["where"]: dwitbuk.layer(f) for f in r["findings"]}
        assert got == {"R-1": "observation", "run-a": "observation", "run-b": "objection", "run-c": "objection", "run-d": "objection",
                       "run-e": "observation", "run-f": "objection", "run-g": "objection"}, got
        texts = {f["where"]: f["text"] for f in r["findings"]}
        # grouping is unchanged: the same text, the tasks borne in words — only the layer is the reporter's now
        assert texts["run-a"] == "(provider) typed limit  [tasks: T1 (run-a), T2 (run-a); also in other runs: T3 (run-b)]", texts
        assert texts["run-e"] == "no long list was tried  [tasks T8, T9]", texts
        assert "5 objection(s) (non-claim 5), 3 observation(s)" in out, out
        i_a = next(i for i, f in enumerate(r["findings"]) if f["where"] == "run-a")
        code, said = run("dispose", "%s/%d" % (r["id"], i_a), "--as", "dismissed", "--why", "x", "--by", "lee", "--target", pj.dir)
        assert code != 0 and "is an observation" in said, said
        code, followed = run("follow", "--target", pj.dir)
        assert "typed limit  [tasks: T1" not in followed and "undisposed findings: 5" in followed, followed


def test_no_check_by_nature_stays_but_never_lifts_a_constituents_explicit_objection():
    """The NO_CHECK rule (a quibble's, a documents task's "no check decides this task" is said, not charged) stays for
    non-claims no reporter typed; a constituent the reporter calls an objection keeps the group one, and the reporter's
    explicit observation on a code task's no-check line is the reporter's word, trusted like any kind's."""
    with Project() as pj:
        nc = "no check decides this task; done means the agent said so"
        layered_run(pj, "run-1", {"q": ("quibble", [], [nc])})
        layered_run(pj, "run-2", {"q": ("quibble", [], [nc]), "p": ("quibble", [], [nc])})
        layered_run(pj, "run-3", {"s": ("session", ["a.py"], [nc])})
        layered_run(pj, "run-4", {"s": ("session", ["a.py"], [nc])})
        pj.reporter([{"kind": "non-claim", "where": "run-1", "text": "q: " + nc},
                     {"kind": "non-claim", "where": "run-2", "text": "q: " + nc},
                     {"kind": "non-claim", "where": "run-2", "text": "p: " + nc, "layer": "objection"},
                     {"kind": "non-claim", "where": "run-3", "text": "s: " + nc, **OBS},
                     {"kind": "non-claim", "where": "run-4", "text": "s: " + nc}], "chongdae")
        assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
        got = {f["where"]: dwitbuk.layer(f) for f in pj.latest()["findings"]}
        assert got == {"run-1": "observation", "run-2": "objection", "run-3": "observation", "run-4": "objection"}, got


def test_a_layer_a_reporter_gave_that_is_no_layer_is_a_charge_and_never_left_to_the_by_nature_rule():
    """Reproduced on 2.0.2's first draft (a review of it, 2026-11-03): collect() dropped a `layer` that was neither word, so a
    quibble's "no check decides this task" a reporter typed `info` read as untyped and the by-nature rule lifted it to an
    observation. A layer given and invalid — unknown, null, not a string — is a charge, grouped or not; only a layer left
    out keeps the kinds' rules (the by-nature rule for a quibble's no-check line; `delegated`)."""
    with Project() as pj:
        nc = "no check decides this task; done means the agent said so"
        for rid in ("run-1", "run-2", "run-3", "run-4"):
            layered_run(pj, rid, {"q": ("quibble", [], [nc])})
        pj.reporter([{"kind": "non-claim", "where": "run-1", "text": "q: " + nc, "layer": "info"},
                     {"kind": "non-claim", "where": "run-2", "text": "q: " + nc, "layer": None},
                     {"kind": "non-claim", "where": "run-3", "text": "q: " + nc, "layer": ["observation"]},
                     {"kind": "non-claim", "where": "run-4", "text": "q: " + nc},
                     {"kind": "delegated", "where": "run-4/q", "text": "typed oddly", "layer": "info"},
                     {"kind": "delegated", "where": "run-4/p", "text": "untyped"}], "chongdae")
        code, out = run("review", "--since", pj.base, "--target", pj.dir)
        got = {f["where"]: dwitbuk.layer(f) for f in pj.latest()["findings"]}
        assert got == {"run-1": "objection", "run-2": "objection", "run-3": "objection", "run-4": "observation",
                       "run-4/q": "objection", "run-4/p": "observation"}, got
        assert all(f["layer"] in ("observation", "objection") for f in pj.latest()["findings"]), "the review writes only the two words"
        assert "4 objection(s) (delegated 1, non-claim 3), 2 observation(s)" in out, out


def test_an_untyped_quibble_non_claim_stays_a_charge_whatever_it_says_and_whoever_said_it():
    """Deferred, not fixed by heuristics: whether a contract reader's own non-claim is a limit its role sets ("I did not read
    the tree") or work it left undone ("I did not inspect the clause I was sent") is not in the record as a type. A hired
    quibble that answered, touched nothing and had no checks still says both in free text, and the second need not name the
    clause's anchor — so no role, provenance or wording lifts an untyped one: guin-site review 6257's role-limit sentences
    stay charges until a producer types them, and the admission beside them stays one too."""
    with Project() as pj:
        said = ["(provider) I did not read the tree or other plan sections (Q-read, Q-lexicon, Q-patch-view, Q-meta). Anything they decide may already settle a finding.",
                "(provider) I did not propose answers or rate the contract.",
                "(provider) 트리(코드)는 읽지 않았다. 지금 코드가 이 일들을 어떻게 하는지는 말하지 않는다",
                "(provider) I did not inspect the acceptance clause about retries; the turns ran out"]   # missing work, no anchor named
        nc = "no check decides this task; done means the agent said so"
        layered_run(pj, "run-1", {"thread-quibble": ("quibble", [], [nc] + said)})
        pj.reporter([{"kind": "non-claim", "where": "run-1", "text": "thread-quibble: " + n} for n in [nc] + said], "chongdae")
        code, out = run("review", "--since", pj.base, "--target", pj.dir)
        got = {f["text"]: dwitbuk.layer(f) for f in pj.latest()["findings"]}
        assert got == {**{n + "  [task thread-quibble]": "objection" for n in said}, nc.split(";")[0] + "  [task thread-quibble]": "observation"}, got
        assert "4 objection(s) (non-claim 4)" in out, out


def test_a_typed_observation_across_reviews_keeps_identity_disposition_and_history_and_an_untyped_old_charge_still_carries():
    """Reviews in a row while a reporter starts, keeps and stops typing its non-claims. A charge the last review held is the
    same finding when typed (its identity has no layer): it inherits that charge's disposition and first-seen, and since that
    review held it as a charge, not an observation, it is written in full once — counted as `unchanged` from the next review,
    which then holds it. An untyped charge that stopped being reported is carried as before (nothing absolves it), a review
    already written is not rewritten, and a non-claim the reporter stops typing is a charge again — answered if it was."""
    import time
    with Project() as pj:
        def report(typed, extra=()):
            pj.reporter([{"kind": "non-claim", "where": "run-1", "text": "%s: (provider) limit %s" % (t, t), **(OBS if t in typed else {})}
                         for t in ("A", "B") + tuple(extra)], "chongdae")
        def review():
            time.sleep(1.1)
            code, out = run("review", "--target", pj.dir)
            assert code == 0, out
            return pj.latest(), out
        def by_task(r):
            return {re.search(r"limit (\w)", f["text"]).group(1) if "limit" in f["text"] else f["kind"]: f for f in r["findings"]}
        report((), extra=("C",))
        assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
        r1 = pj.latest()
        f1 = by_task(r1)
        assert all(dwitbuk.layer(f1[t]) == "objection" for t in "ABC"), f1
        i_a = r1["findings"].index(f1["A"])
        assert run("dispose", "%s/%d" % (r1["id"], i_a), "--as", "accepted", "--why", "the role sets it", "--by", "lee", "--target", pj.dir)[0] == 0
        r1_path = os.path.join(pj.dir, dwitbuk.REVIEWS, r1["id"] + ".json")
        r1_bytes = open(r1_path, "rb").read()
        answer = pj.latest()["findings"][i_a]["disposition"]

        report(("A", "B", "D"), extra=("D",))   # A and B typed now, C no longer reported, D new and typed
        r2, out2 = review()
        f2 = by_task(r2)
        assert open(r1_path, "rb").read() == r1_bytes, "a written review is history: not rewritten"
        assert [dwitbuk.layer(f2[t]) for t in "ABD"] == ["observation"] * 3, f2
        assert "unchanged" not in f2, "the last review held A and B as charges, not observations: written in full, not counted"
        assert dwitbuk.identity(f2["A"]) == dwitbuk.identity(f1["A"]) and f2["A"]["disposition"] == answer, f2["A"]
        assert f2["A"]["first-seen"] == r1["id"] == f2["B"]["first-seen"] and "disposition" not in f2["B"], f2
        carried = [f for f in r2["findings"] if f["kind"] == "undisposed"]
        assert len(carried) == 1 and carried[0]["raised-in"] == "%s/%d" % (r1["id"], r1["findings"].index(f1["C"])), carried
        assert "1 objection(s) (non-claim 1; 1 of them carried, already in the count), 3 observation(s)" in out2, out2
        i_b = r2["findings"].index(f2["B"])
        assert "is an observation" in run("dispose", "%s/%d" % (r2["id"], i_b), "--as", "accepted", "--why", "x", "--by", "lee", "--target", pj.dir)[1]

        r2_bytes = open(os.path.join(pj.dir, dwitbuk.REVIEWS, r2["id"] + ".json"), "rb").read()
        r3, out3 = review()   # the same report: now held in full by r2, counted
        f3 = by_task(r3)
        assert open(os.path.join(pj.dir, dwitbuk.REVIEWS, r2["id"] + ".json"), "rb").read() == r2_bytes
        assert not any(t in f3 for t in "ABD") and f3["unchanged"]["seen-in"] == [r2["id"]], f3
        assert "3 observation(s) written in full in 1 earlier review(s) and unchanged since (non-claim 3)" == f3["unchanged"]["text"], f3
        carried = [f for f in r3["findings"] if f["kind"] == "undisposed"]
        assert len(carried) == 1 and carried[0]["raised-in"].startswith(r1["id"] + "/"), carried

        report(())   # the reporter stops typing: A and B are charges again, A answered in r1, B open; C still carried
        r4, out4 = review()
        f4 = by_task(r4)
        assert dwitbuk.layer(f4["A"]) == dwitbuk.layer(f4["B"]) == "objection", f4
        assert f4["A"]["disposition"] == answer and "disposition" not in f4["B"], f4
        assert "2 objection(s) (non-claim 2; 1 of them carried, already in the count)" in out4, out4
        code, followed = run("follow", "--target", pj.dir)   # B, counted as unchanged in r3, is owed a disposal again
        assert code == 1 and "limit B  [task B]" in followed and "limit A" not in followed and "undisposed findings: 2" in followed, followed


def test_review_and_the_session_start_line_count_each_open_charge_once_by_the_kind_it_makes():
    """guin-site review a3c2: chongdae's close said "cq-failed 2, non-claim 7, undisposed 3" and the next session start
    "cq-failed 2, non-claim 10" for the same twelve objections — review counted a carry as `undisposed`, the hook as the kind
    it carries. One rule, one text: each open objection once, under the kind of the charge it makes, then how many are carried."""
    open_ = [{"kind": "cq-failed", "where": "a", "text": "x"}, {"kind": "non-claim", "where": "r1", "text": "y"},
             {"kind": "undisposed", "where": "r2", "text": "z", "carries": ["non-claim", "r2", "z"]}]
    assert dwitbuk.count_text(open_) == "cq-failed 1, non-claim 2; 1 of them carried, already in the count"
    assert dwitbuk.count_text(open_[:2]) == "cq-failed 1, non-claim 1" and dwitbuk.count_text([]) == "none"
    hook = os.path.join(PLUGIN, "hooks", "session_start.py")
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


def test_Q_match_an_exact_entry_matches_that_path_only():
    # amended to Q-strict: a bare entry is an exact FILE path; a trailing / on the path names a directory, nothing is under a file
    assert dwitbuk.is_record("alpha.json", ["alpha.json"]) and dwitbuk.is_record("./alpha.json", ["alpha.json"])
    assert not dwitbuk.is_record("alpha.json/", ["alpha.json"]), "a path with a trailing / is a directory, never the file alpha.json"
    assert not dwitbuk.is_record("alpha.json/inner.txt", ["alpha.json"]), "a bare entry is a file: nothing is under it"
    assert not dwitbuk.is_record("mangsang/relations/R-1.json", ["mangsang"]) and dwitbuk.is_record("mangsang", ["mangsang"])
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
        write(os.path.join(pj.dir, "alpha.json"), '{"alpha": "declared file"}\n')
        write(os.path.join(pj.dir, ".alpha", "x.json"), '{"alpha": "declared directory"}\n')
        write(os.path.join(pj.dir, "hunsu.json"), '{"hunsu": "own file"}\n')
        write(os.path.join(pj.dir, ".chongdae", "run-1", "tasks", "T.json"), '{"chongdae": "run bookkeeping"}\n')
        kept = ["hunsu.py", "hunsu_helper.py", "hunsu-notes.md", "alpha.jsonl", ".alpha-extra/y.py"]
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": kept + ["alpha.json", ".alpha/x.json", ".chongdae/run-1/tasks/T.json", "hunsu.json"], "since": {".": since}}
        p = dwitbuk.verify_packet(req)
        assert p["touched"] == kept + ["alpha.json", ".alpha/x.json", "hunsu.json"], p["touched"]
        d = p["diff"]
        assert "-hp = 1" in d and "+hp = 2" in d, d
        assert "helper = 1" in d and "notes line" in d and '{"l": 2}' in d and "sibling = 1" in d, d
        assert "declared file" in d and "declared directory" in d and '"own file"' in d, d
        assert "run bookkeeping" not in d and ".chongdae/run-1/tasks/T.json" not in d, d
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
        assert set(leaves) == {".alpha/", ".chongdae/", ".claude/", ".dwitbuk/", ".mangsang/", "alpha.json", "x[1].json", "reviews/", ".dwitbuk/packet/"} | set(HUNSU_FILES), leaves
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
        assert set(packet["diff_leaves_out"]) == {".chongdae/", ".claude/", ".dwitbuk/", ".mangsang/", "reviews/", ".dwitbuk/packet/"} | set(HUNSU_FILES), packet["diff_leaves_out"]
        write(os.path.join(pj.dir, "mangsang", "relations", "R-3.json"), {"id": "R-3"})
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "source changed" in out, out
        # and the verify packet and documents_or_records still count mangsang/ a record
        assert dwitbuk.documents_or_records(["mangsang/relations/R-3.json"], pj.dir)
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": ["mangsang/relations/R-3.json", "hunsu.py"]}
        write(os.path.join(pj.dir, "hunsu.py"), "hp = 1\n")
        p = dwitbuk.verify_packet(req)
        assert p["touched"] == ["mangsang/relations/R-3.json", "hunsu.py"], p["touched"]   # D1: the scope named it, the verifier sees it
        assert "mangsang/relations/R-3.json" in p["diff"] and '"R-3"' in p["diff"] and "hp = 1" in p["diff"], p["diff"]


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


STRICT_LOCK = {"record-paths": {"custom": ["custom-record.json"]}}


def strict_project(pj, lock=None):
    """hunsu.json and a lock-declared bare custom-record.json, each committed as a file, then each replaced by a directory
    holding a committed child.py. Returns (the commit with the files, the commit with the directories)."""
    write(os.path.join(pj.dir, "hunsu.lock.json"), lock or STRICT_LOCK)
    write(os.path.join(pj.dir, "hunsu.json"), {"plugins": {}})
    write(os.path.join(pj.dir, "custom-record.json"), {"r": 1})
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "records as files")
    files_base = git(pj.dir, "rev-parse", "HEAD")
    os.unlink(os.path.join(pj.dir, "hunsu.json"))
    os.unlink(os.path.join(pj.dir, "custom-record.json"))
    write(os.path.join(pj.dir, "hunsu.json", "child.py"), "hchild = 1\n")
    write(os.path.join(pj.dir, "custom-record.json", "child.py"), "cchild = 1\n")
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "records replaced by directories")
    assert git(pj.dir, "ls-files", "hunsu.json", "custom-record.json") == "custom-record.json/child.py\nhunsu.json/child.py"
    return files_base, git(pj.dir, "rev-parse", "HEAD")


def test_Q_strict_a_bare_entry_is_an_exact_file_and_a_trailing_slash_entry_a_directory():
    for path in ("hunsu.json/child.py", "hunsu.json/", "./hunsu.json/child.py", "hunsu.json\\child.py", "hunsu.json/a/b.py", ".\\hunsu.json\\child.py"):
        assert not dwitbuk.is_record(path, ["hunsu.json"]), path
        assert not dwitbuk.is_record(path, HUNSU_FILES), path
    assert dwitbuk.is_record("hunsu.json", ["hunsu.json"]) and dwitbuk.is_record("./hunsu.json", ["hunsu.json"])
    assert not dwitbuk.is_record("alpha.json/", ["alpha.json"]) and not dwitbuk.is_record("alpha.json/inner.txt", ["alpha.json"])
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), STRICT_LOCK)
        rp = dwitbuk.record_paths(pj.dir)
        assert "custom-record.json" in rp and "custom-record.json/" not in rp, rp
        assert dwitbuk.is_record("custom-record.json", rp) and dwitbuk.is_record("./custom-record.json", rp)
        for path in ("custom-record.json/child.py", "custom-record.json/", "hunsu.json/child.py", "custom-record.json\\child.py"):
            assert not dwitbuk.is_record(path, rp), path
    # directory entries as before, beside file entries in the same declaration
    mixed = ["hunsu.json", "custom-record.json", "mangsang/", "x[1].json", ""]
    for path in ("mangsang", "mangsang/", "mangsang/relations/R-1.json", "./mangsang/relations/R-1.json", "mangsang\\relations\\R-1.json", "x[1].json"):
        assert dwitbuk.is_record(path, mixed), path
    for path in ("mangsang-extra/x.py", "x1.json", "x[1].json/child.py", "hunsu.json.bak", "", "custom-record.jsonl"):
        assert not dwitbuk.is_record(path, mixed), path


def test_Q_strict_is_record_never_looks_at_the_disk():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.json", "child.py"), "x = 1\n")
        write(os.path.join(pj.dir, "alpha.json", "inner.txt"), "x\n")
        here = os.getcwd()
        os.chdir(pj.dir)
        try:
            assert os.path.isdir("hunsu.json")
            assert not dwitbuk.is_record("hunsu.json/child.py", ["hunsu.json"]), "a declared file replaced by a directory: what it holds is source"
            assert not dwitbuk.is_record("alpha.json/inner.txt", ["alpha.json"]) and not dwitbuk.is_record("alpha.json/", ["alpha.json"])
            assert dwitbuk.is_record("nowhere/x.json", ["nowhere/"]), "a directory entry needs no directory on disk"
        finally:
            os.chdir(here)


def test_Q_strict_sites_documents_or_records_a_replaced_file_holds_source():
    with Project() as pj:
        strict_project(pj)
        for code in ("hunsu.json/child.py", "custom-record.json/child.py"):
            assert not dwitbuk.documents_or_records([code], pj.dir), code
            assert not dwitbuk.documents_or_records(["hunsu.lock.json", code], pj.dir), code
        assert dwitbuk.documents_or_records(["custom-record.json", "hunsu.json", "hunsu.lock.json"], pj.dir), "the declared files themselves are records"


def test_Q_strict_sites_verify_packet_keeps_children_of_a_replaced_file_in_touched_with_their_diff():
    with Project() as pj:
        files_base, dirs_base = strict_project(pj)
        write(os.path.join(pj.dir, "hunsu.json", "child.py"), "hchild = 2\n")
        write(os.path.join(pj.dir, "custom-record.json", "child.py"), "cchild = 2\n")
        write(os.path.join(pj.dir, "hunsu.json", "new_mod.py"), "hnew = 1\n")
        kept = ["hunsu.json/child.py", "custom-record.json/child.py", "hunsu.json/new_mod.py"]
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": kept + ["hunsu.lock.json", "custom-record.json", "hunsu.json"], "since": {".": dirs_base}}
        p = dwitbuk.verify_packet(req)
        # 11-06 (D1): the records the request lists in touched stay too, each with its diff — only chongdae's runs and the
        # host's settings go
        assert p["touched"] == kept + ["hunsu.lock.json", "custom-record.json", "hunsu.json"], p["touched"]
        d = p["diff"]
        assert "-hchild = 1" in d and "+hchild = 2" in d and "b/hunsu.json/child.py" in d, d
        assert "-cchild = 1" in d and "+cchild = 2" in d and "b/custom-record.json/child.py" in d, d
        assert "hunsu.json/new_mod.py (new file)" in d and "hnew = 1" in d, d
        # from where the files were: the children are new, and the replaced records' own deletions — touched, so the task's
        # work — reach the verifier too
        d = dwitbuk.verify_packet(dict(req, since={".": files_base}))["diff"]
        assert "+hchild = 2" in d and "+cchild = 2" in d, d
        assert '- "plugins": {}' in d, d
        assert '- "r": 1' in d, d


def test_Q_strict_sites_verify_packet_gives_touched_and_excluded_to_git_literally():
    with Project() as pj:
        write(os.path.join(pj.dir, "x[1].json"), '"old bracket"\n')
        write(os.path.join(pj.dir, "x1.json"), '"old one"\n')
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "brackets")
        since = git(pj.dir, "rev-parse", "HEAD")
        write(os.path.join(pj.dir, "x[1].json"), '"new bracket"\n')
        write(os.path.join(pj.dir, "x1.json"), '"new one"\n')
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": ["x[1].json"], "since": {".": since}}
        p = dwitbuk.verify_packet(req)
        assert p["touched"] == ["x[1].json"] and '+"new bracket"' in p["diff"], p["diff"]
        assert '"new one"' not in p["diff"] and "x1.json" not in p["diff"], "x[1].json is literal, never the glob that selects x1.json: " + p["diff"]
        env = dwitbuk.verify_packet(dict(req, touched=[], excluded={"record-paths": ["x[1].json"]}))
        assert env["excluded"] == ["x[1].json"] and "excluded_diff" not in env, sorted(env)   # 11-09, D2: the name, none of its changes
        text = json.dumps(env)
        assert '"new bracket"' not in text and '"new one"' not in text and "x1.json" not in text, text
        # path_diff (the late-eyes request's) still takes the excluded name literally
        pd = dwitbuk.path_diff(pj.dir, ["x[1].json"], ("HEAD",), cut=40000)
        assert '+"new bracket"' in pd and '"new one"' not in pd and "x1.json" not in pd, pd


def test_Q_strict_sites_source_state_changes_with_children_of_a_replaced_file():
    with Project() as pj:
        strict_project(pj)
        run("review", "--target", pj.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        for rel in ("hunsu.json/child.py", "custom-record.json/child.py", "hunsu.json/new_mod.py", "custom-record.json/new_mod.py"):
            eyes_answer(pj, folder)
            write(os.path.join(pj.dir, rel), "changed %s\n" % rel)
            code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
            assert code != 0 and "source changed" in out, (rel, out)
        eyes_answer(pj, folder)
        write(os.path.join(pj.dir, "reviews", "note.json"), {"x": 1})
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code == 0, "a record change alone does not stale the answer: " + out


def test_Q_strict_sites_source_state_tests_an_untracked_or_ignored_directory_as_a_directory():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), STRICT_LOCK)
        write(os.path.join(pj.dir, ".gitignore"), "/custom-record.json/\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "lock")
        write(os.path.join(pj.dir, "hunsu.json", "child.py"), "hchild = 1\n")
        nested = os.path.join(pj.dir, "custom-record.json")
        write(os.path.join(nested, "child.py"), "cchild = 1\n")
        git(nested, "init", "-q")
        git(nested, "add", "-A"); git(nested, "commit", "-qm", "nested")
        assert git(nested, "ls-files") == "child.py", "custom-record.json/ is an ignored nested repository"
        status = git(pj.dir, "status", "--porcelain", "--ignored")
        assert "?? hunsu.json/" in status and "!! custom-record.json/" in status, status
        run("review", "--target", pj.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        for rel in ("hunsu.json/child.py", "custom-record.json/child.py"):
            eyes_answer(pj, folder)
            write(os.path.join(pj.dir, rel), "changed %s\n" % rel)
            code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
            assert code != 0 and "source changed" in out, (rel, out)


def test_Q_strict_sites_source_state_in_a_non_git_project_walks_into_a_replaced_file():
    d = tempfile.mkdtemp(prefix="dwitbuk-nogit-")
    try:
        class P:
            dir = d
        write(os.path.join(d, "a.py"), "x = 1\n")
        write(os.path.join(d, "hunsu.lock.json"), STRICT_LOCK)
        write(os.path.join(d, "hunsu.json", "child.py"), "hchild = 1\n")
        write(os.path.join(d, "custom-record.json", "child.py"), "cchild = 1\n")
        run("review", "--target", d)
        folder = os.path.join(d, ".dwitbuk", "packet")
        for rel in ("hunsu.json/child.py", "custom-record.json/child.py"):
            eyes_answer(P, folder)
            write(os.path.join(d, rel), "changed %s\n" % rel)
            code, out = run("eyes", "consume", "--dir", folder, "--target", d)
            assert code != 0 and "source changed" in out, (rel, out)
        eyes_answer(P, folder)
        write(os.path.join(d, "reviews", "note.json"), "{}\n")
        code, out = run("eyes", "consume", "--dir", folder, "--target", d)
        assert code == 0, out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_Q_strict_sites_eyes_request_diff_holds_children_of_a_replaced_file_on_real_git_output():
    with Project() as pj:
        files_base, dirs_base = strict_project(pj)
        run("review", "--target", pj.dir)
        write(os.path.join(pj.dir, "hunsu.json", "child.py"), "hchild = 2\n")
        write(os.path.join(pj.dir, "custom-record.json", "child.py"), "cchild = 2\n")
        write(os.path.join(pj.dir, "hunsu.json", "new_mod.py"), "hnew = 1\n")
        write(os.path.join(pj.dir, "custom-record.json", "new_mod.py"), "cnew = 1\n")
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        code, out = run("eyes", "request", "--out", folder, "--since", dirs_base, "--target", pj.dir)
        assert code == 0, out
        packet = dwitbuk.load(os.path.join(folder, "eyes-request.json"))
        d, new = packet["diff"], packet["new_files"]
        assert "-hchild = 1" in d and "+hchild = 2" in d and "b/hunsu.json/child.py" in d, d
        assert "-cchild = 1" in d and "+cchild = 2" in d and "b/custom-record.json/child.py" in d, d
        assert "hunsu.json/new_mod.py" in new and "custom-record.json/new_mod.py" in new, list(new)
        code, out = run("eyes", "request", "--out", folder, "--since", files_base, "--target", pj.dir)
        assert code == 0, out
        d = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]
        assert "+hchild = 2" in d and "+cchild = 2" in d, "from the files' commit the children are new: " + d
        assert '"plugins"' not in d and '"r": 1' not in d, "the declared files' own deletions stay left out: " + d


def test_Q_strict_sites_eyes_request_in_a_subdirectory_of_a_larger_repository_diffs_by_target_relative_names():
    with Project() as pj:
        sub = os.path.join(pj.dir, "proj")
        write(os.path.join(pj.dir, "outer.py"), "outer = 1\n")
        write(os.path.join(sub, "hunsu.lock.json"), STRICT_LOCK)
        write(os.path.join(sub, "a.py"), "suba = 1\n")
        write(os.path.join(sub, "hunsu.json", "child.py"), "hchild = 1\n")
        write(os.path.join(sub, "custom-record.json"), '{"r": 1}\n')
        write(os.path.join(sub, "reviews", "note.md"), "note one\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "outer file and a subdirectory project")
        assert git(sub, "rev-parse", "--show-prefix") == "proj/", "the target is a subdirectory of the repository"
        run("review", "--target", sub)
        write(os.path.join(pj.dir, "outer.py"), "outer = 2\n")
        write(os.path.join(sub, "a.py"), "suba = 2\n")
        write(os.path.join(sub, "hunsu.json", "child.py"), "hchild = 2\n")
        write(os.path.join(sub, "custom-record.json"), '{"r": 2}\n')
        write(os.path.join(sub, "reviews", "note.md"), "note two\n")
        packet = late_packet(type("Sub", (), {"dir": sub}), os.path.join(sub, ".dwitbuk", "packet"))
        d = packet["diff"]
        assert "-suba = 1" in d and "+suba = 2" in d, "git names changes from the repository root; the target's own a.py is kept: " + d
        assert "-hchild = 1" in d and "+hchild = 2" in d and "hunsu.json/child.py" in d, d
        assert '"r": 2' not in d and '"r": 1' not in d, "the declared custom-record.json stays left out: " + d
        assert "note two" not in d and "reviews/" not in d, "reviews/ stays left out: " + d
        assert "outer" not in d, "a file outside the target is not the target's diff: " + d


def test_Q_strict_sites_eyes_request_leaves_out_entries_as_declared_and_only_records_make_an_empty_diff():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"custom": ["custom-record.json", ".custom/"]}})
        write(os.path.join(pj.dir, "hunsu.json"), {"plugins": {}})
        write(os.path.join(pj.dir, "custom-record.json"), {"r": 1})
        write(os.path.join(pj.dir, ".custom", "x.json"), {"c": 1})
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "records")
        run("review", "--target", pj.dir)
        write(os.path.join(pj.dir, "hunsu.json"), {"plugins": {"x": {}}})
        write(os.path.join(pj.dir, "custom-record.json"), {"r": 2})
        write(os.path.join(pj.dir, ".custom", "x.json"), {"c": 2})
        write(os.path.join(pj.dir, ".claude", "settings.json"), "{}\n")
        packet = late_packet(pj, os.path.join(pj.dir, ".dwitbuk", "packet"))
        assert packet["diff"] == "", "only records changed: the diff is empty, never an unrestricted git diff: " + packet["diff"]
        assert not packet["new_files"], "untracked records are not new files: %r" % (list(packet["new_files"]),)
        declared = {".chongdae/", ".claude/", ".dwitbuk/", ".custom/", "custom-record.json", "reviews/"} | set(HUNSU_FILES)
        assert set(packet["diff_leaves_out"]) == declared | {".dwitbuk/packet/"}, packet["diff_leaves_out"]
        outside = tempfile.mkdtemp(prefix="dwitbuk-out-")
        try:
            assert run("eyes", "request", "--out", outside, "--target", pj.dir)[0] == 0
            leaves = dwitbuk.load(os.path.join(outside, "eyes-request.json"))["diff_leaves_out"]
            assert set(leaves) == declared, "a packet directory outside the target is not named: %r" % (leaves,)
        finally:
            shutil.rmtree(outside, ignore_errors=True)


def test_Q_strict_sites_stop_hook_hands_children_of_a_replaced_file_to_the_eyes():
    with Project() as pj:
        strict_project(pj, lock=dict(STRICT_LOCK, settings={"dwitbuk": {"stop-eyes": True}}))
        write(os.path.join(pj.dir, "hunsu.local.json"), {"settings": {"dwitbuk": {"stop-eyes": True}}})
        write(os.path.join(pj.dir, "hunsu.json", "child.py"), "hchild = 2\n")
        write(os.path.join(pj.dir, "custom-record.json", "child.py"), "cchild = 2\n")
        touched, packet = stop_hook_touched(pj)
        assert touched is not None and packet is not None, "the hook reached the eyes"
        assert set(touched) == {"hunsu.json/child.py", "custom-record.json/child.py"}, touched
        assert "+hchild = 2" in packet["diff"] and "+cchild = 2" in packet["diff"], packet["diff"]
        leaves = set(packet["diff_leaves_out"])
        assert {".chongdae/", ".claude/", ".dwitbuk/", "reviews/", "custom-record.json"} | set(HUNSU_FILES) <= leaves, leaves
        assert not leaves & {".chongdae", ".claude", ".dwitbuk", "reviews", "custom-record.json/", "hunsu.json/"}, leaves


def test_Q_strict_keep_mangsang_stays_in_late_eyes_and_a_record_for_verify():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"mangsang": ["mangsang/", ".mangsang/"]}})
        write(os.path.join(pj.dir, "mangsang", "relations", "R-1.json"), {"id": "R-1", "v": 1})
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "relations")
        run("review", "--target", pj.dir)
        write(os.path.join(pj.dir, "mangsang", "relations", "R-1.json"), {"id": "R-1", "v": 2})
        write(os.path.join(pj.dir, "mangsang", "relations", "R-2.json"), {"id": "R-2"})
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder)
        assert "b/mangsang/relations/R-1.json" in packet["diff"] and "mangsang/relations/R-2.json" in packet["new_files"], packet["diff"]
        leaves = set(packet["diff_leaves_out"])
        assert ".mangsang/" in leaves and "mangsang/" not in leaves and "mangsang" not in leaves and ".mangsang" not in leaves, leaves
        write(os.path.join(pj.dir, "mangsang", "relations", "R-3.json"), {"id": "R-3"})
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "source changed" in out, out
        assert dwitbuk.documents_or_records(["mangsang/relations/R-3.json"], pj.dir)
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": ["mangsang/relations/R-3.json", "mangsang", "a.py"]}
        p = dwitbuk.verify_packet(req)
        assert p["touched"] == ["mangsang/relations/R-3.json", "mangsang", "a.py"], p["touched"]   # D1: a record for documents_or_records, work for verify
        assert '"R-3"' in p["diff"], p["diff"]


def test_Q_strict_keep_environment_records_stay_out_and_same_prefix_neighbours_stay_in():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"alpha": [".alpha/", "alpha.json", "x[1].json"]}})
        for name in HUNSU_FILES[:-1] + ("hunsu.py", "alpha.json", "alpha.jsonl", "x[1].json", "x1.json", ".alpha/z.json", ".alpha-extra/y.py"):
            write(os.path.join(pj.dir, name), '"old %s"\n' % name)
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base two")
        since = git(pj.dir, "rev-parse", "HEAD")
        run("review", "--target", pj.dir)
        for name in HUNSU_FILES[:-1] + ("hunsu.py", "alpha.json", "alpha.jsonl", "x[1].json", "x1.json", ".alpha/z.json", ".alpha-extra/y.py"):
            write(os.path.join(pj.dir, name), '"new %s"\n' % name)
        for rel in (".claude/settings.json", ".chongdae/run-1/state.json", "reviews/r.json", ".alpha/new.json"):
            write(os.path.join(pj.dir, rel), "{}\n")
        sources = ("hunsu.py", "alpha.jsonl", "x1.json", ".alpha-extra/y.py")
        records = HUNSU_FILES[:-1] + ("alpha.json", "x[1].json", ".alpha/z.json")
        packet = late_packet(pj, os.path.join(pj.dir, ".dwitbuk", "packet"))
        d = packet["diff"]
        for name in sources:
            assert '"new %s"' % name in d, (name, d)
        for name in records:
            assert '"new %s"' % name not in d, (name, d)
        assert not [k for k in packet["new_files"] if k.startswith((".claude/", ".chongdae/", "reviews/", ".alpha/", ".dwitbuk/"))], list(packet["new_files"])
        assert {".alpha/", ".claude/", "alpha.json", "x[1].json"} <= set(packet["diff_leaves_out"]) and ".alpha" not in packet["diff_leaves_out"], packet["diff_leaves_out"]
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": list(sources) + list(records) + [".claude/settings.json", "reviews/r.json"], "since": {".": since}}
        p = dwitbuk.verify_packet(req)
        assert p["touched"] == list(sources) + list(records) + ["reviews/r.json"], p["touched"]   # D1: only the host's settings go
        for name in sources + records:
            assert '"new %s"' % name in p["diff"], (name, p["diff"])
        assert "reviews/r.json" in p["diff"] and ".claude/settings.json" not in p["diff"], p["diff"]
        for name in sources:
            assert not dwitbuk.documents_or_records([name], pj.dir), name
        assert dwitbuk.documents_or_records(list(records), pj.dir)



HOSTCALL_DROPPED = ("CODEX_THREAD_ID", "CODEX_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CHONGDAE_SESSION", "AI_AGENT", "CLAUDE_PROJECT_DIR", "CODEX_VERSION")
HOSTCALL_KEPT = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CLAUDECODE", "AGENT_CODEX_SANDBOX", "PATH")
HOSTCALL_HOSTS = {"claude": "claude-code", "codex": "codex"}
HOSTCALL_SESSION_MARKER = "synthetic-codex-session-id-parent-0000"
HOSTCALL_NEAR_MISS = ("CODEX_SESSION_ID_NOTE", "synthetic near-miss, not the session id")


def hostcall_parent(adapter, sandbox="workspace-write"):
    """A parent environment that is the *other* host's session, with every identity, metadata, config and auth key set."""
    env = {"AGENT_HOST": "codex" if adapter == "claude" else "claude-code",
           "CODEX_THREAD_ID": "thread-parent", "CODEX_SESSION_ID": HOSTCALL_SESSION_MARKER,
           HOSTCALL_NEAR_MISS[0]: HOSTCALL_NEAR_MISS[1], "CLAUDE_CODE_SESSION_ID": "session-parent", "CHONGDAE_SESSION": "chongdae-parent",
           "AI_AGENT": "parent-agent", "CLAUDE_PROJECT_DIR": "/parent/project", "CODEX_VERSION": "0.0.parent",
           "CLAUDE_CONFIG_DIR": "/dummy/claude-config", "CODEX_HOME": "/dummy/codex-home", "ANTHROPIC_API_KEY": "sk-ant-dummy",
           "OPENAI_API_KEY": "sk-openai-dummy", "CLAUDECODE": "1", "AGENT_CODEX_SANDBOX": sandbox}
    if sandbox is None:
        del env["AGENT_CODEX_SANDBOX"]
    return env


def hostcall_call(adapter, parent):
    """Call eyes_worker.<adapter>(packet, schema, args) inside `parent` (laid over this process's env, AGENT_WORKER and
    CLAUDE_CODE_DISABLE_AUTO_MEMORY taken out) with subprocess.run replaced by a recorder that answers exit 1, so no host
    process starts and the adapter stops with SystemExit after the call. Returns (host call, os.environ before, after):
    the call is {"argv": [...], "env": {...}} — the env as the child would get it (os.environ when none is passed)."""
    calls, saved, real_run = [], dict(os.environ), subprocess.run
    d = tempfile.mkdtemp(prefix="dwitbuk-hostcall-")
    def recorder(cmd, *a, **kw):
        env = kw.get("env")
        calls.append({"argv": [str(x) for x in (cmd if isinstance(cmd, (list, tuple)) else [cmd])],
                      "env": dict(os.environ if env is None else env)})
        text = kw.get("text") or kw.get("universal_newlines") or kw.get("encoding")
        return subprocess.CompletedProcess(cmd, 1, "" if text else b"", "recorded, not run" if text else b"recorded, not run")
    try:
        for k in ("AGENT_WORKER", "CLAUDE_CODE_DISABLE_AUTO_MEMORY", "AGENT_CODEX_SANDBOX"):
            os.environ.pop(k, None)
        os.environ.update(parent)
        before = dict(os.environ)
        args = argparse.Namespace(model=None, effort=None, max_turns=3, response=os.path.join(d, "resp.json"),
                                  request=os.path.join(d, "req.json"), host=adapter)
        packet = {"target": d, "instructions": "x"}
        subprocess.run = recorder
        try:
            getattr(w, adapter)(packet, dwitbuk.EYES_SCHEMA, args)
        except SystemExit:
            pass
        finally:
            subprocess.run = real_run
        after = dict(os.environ)
    finally:
        os.environ.clear()
        os.environ.update(saved)
        shutil.rmtree(d, ignore_errors=True)
    host = [c for c in calls if os.path.basename(c["argv"][0]) == adapter] if calls else []
    assert len(host) == 1, ("exactly one %s call recorded" % adapter, [c["argv"][:2] for c in calls])
    return host[0], before, after


def hostcall_child_env_is_the_workers(adapter, call, parent):
    env = call["env"]
    assert env.get("AGENT_HOST") == HOSTCALL_HOSTS[adapter], (adapter, env.get("AGENT_HOST"), "parent says", parent["AGENT_HOST"])
    assert env.get("AGENT_WORKER") == "1", env.get("AGENT_WORKER")
    leaked = [k for k in HOSTCALL_DROPPED if k in env]
    assert not leaked, ("parent identity/metadata reached the %s child" % adapter, leaked)
    for k in HOSTCALL_KEPT:
        want = parent.get(k, os.environ.get(k))
        if want is not None:
            assert env.get(k) == want, (adapter, k, env.get(k), want)


def test_Q_hostcall_claude_child_names_claude_code_whatever_the_parent_host_and_is_a_worker():
    parent = hostcall_parent("claude")
    call, _, _ = hostcall_call("claude", parent)
    assert call["env"].get("AGENT_HOST") == "claude-code", call["env"].get("AGENT_HOST")
    assert call["env"].get("AGENT_WORKER") == "1"


def test_Q_hostcall_codex_child_names_codex_whatever_the_parent_host_and_is_a_worker():
    parent = hostcall_parent("codex")
    call, _, _ = hostcall_call("codex", parent)
    assert call["env"].get("AGENT_HOST") == "codex", call["env"].get("AGENT_HOST")
    assert call["env"].get("AGENT_WORKER") == "1"


def test_Q_hostcall_claude_child_carries_none_of_the_parents_identity_or_project_metadata():
    call, _, _ = hostcall_call("claude", hostcall_parent("claude"))
    assert not [k for k in HOSTCALL_DROPPED if k in call["env"]], [k for k in HOSTCALL_DROPPED if k in call["env"]]


def test_Q_hostcall_codex_child_carries_none_of_the_parents_identity_or_project_metadata():
    call, _, _ = hostcall_call("codex", hostcall_parent("codex"))
    assert not [k for k in HOSTCALL_DROPPED if k in call["env"]], [k for k in HOSTCALL_DROPPED if k in call["env"]]


def test_Q_hostcall_claude_child_keeps_config_auth_and_markers_and_turns_auto_memory_off():
    parent = hostcall_parent("claude")
    call, _, _ = hostcall_call("claude", parent)
    hostcall_child_env_is_the_workers("claude", call, parent)
    assert call["env"].get("CLAUDE_CODE_DISABLE_AUTO_MEMORY") == "1", call["env"].get("CLAUDE_CODE_DISABLE_AUTO_MEMORY")
    assert call["env"].get("PATH") == os.environ.get("PATH")


def test_Q_hostcall_codex_child_keeps_config_auth_and_markers():
    parent = hostcall_parent("codex")
    call, _, _ = hostcall_call("codex", parent)
    hostcall_child_env_is_the_workers("codex", call, parent)
    assert call["env"].get("PATH") == os.environ.get("PATH")


def test_Q_hostcall_codex_sandbox_is_the_parents_AGENT_CODEX_SANDBOX_when_set():
    for sandbox in ("workspace-write", "danger-full-access"):
        parent = hostcall_parent("codex", sandbox)
        call, _, _ = hostcall_call("codex", parent)
        argv = call["argv"]
        assert argv.count("-s") == 1 and argv[argv.index("-s") + 1] == sandbox, argv
        hostcall_child_env_is_the_workers("codex", call, parent)


def test_Q_hostcall_codex_sandbox_is_read_only_when_the_parent_sets_none():
    parent = hostcall_parent("codex", None)
    call, _, _ = hostcall_call("codex", parent)
    argv = call["argv"]
    assert argv.count("-s") == 1 and argv[argv.index("-s") + 1] == "read-only", argv
    assert "AGENT_CODEX_SANDBOX" not in call["env"], call["env"].get("AGENT_CODEX_SANDBOX")
    hostcall_child_env_is_the_workers("codex", call, parent)


def test_Q_hostcall_parent_environ_is_the_same_after_each_call_as_before():
    for adapter in ("claude", "codex", "claude"):   # the second claude call: nothing the first left behind
        parent = hostcall_parent(adapter)
        call, before, after = hostcall_call(adapter, parent)
        assert before == after, (adapter, {k: (before.get(k), after.get(k)) for k in set(before) | set(after) if before.get(k) != after.get(k)})
        assert before.get("AGENT_HOST") == parent["AGENT_HOST"] and "AGENT_WORKER" not in after
        hostcall_child_env_is_the_workers(adapter, call, parent)
        assert before.get("CODEX_SESSION_ID") == after.get("CODEX_SESSION_ID") == HOSTCALL_SESSION_MARKER, \
            (adapter, before.get("CODEX_SESSION_ID"), after.get("CODEX_SESSION_ID"))


def hostcall_session_id_is_dropped_by_name(adapter):
    assert HOSTCALL_DROPPED[HOSTCALL_DROPPED.index("CODEX_THREAD_ID") + 1] == "CODEX_SESSION_ID" and len(HOSTCALL_DROPPED) == 7, HOSTCALL_DROPPED
    parent = hostcall_parent(adapter)
    assert parent.get("CODEX_SESSION_ID") == HOSTCALL_SESSION_MARKER and parent.get(HOSTCALL_NEAR_MISS[0]) == HOSTCALL_NEAR_MISS[1], parent
    call, before, after = hostcall_call(adapter, parent)
    env = call["env"]
    assert "CODEX_SESSION_ID" not in env, ("the parent's CODEX_SESSION_ID reached the %s child" % adapter, env.get("CODEX_SESSION_ID"))
    assert env.get(HOSTCALL_NEAR_MISS[0]) == HOSTCALL_NEAR_MISS[1], (adapter, "near-miss", env.get(HOSTCALL_NEAR_MISS[0]))
    assert env.get("AGENT_HOST") == HOSTCALL_HOSTS[adapter] and env.get("AGENT_WORKER") == "1", (adapter, env.get("AGENT_HOST"), env.get("AGENT_WORKER"))
    assert before == after and after.get("CODEX_SESSION_ID") == HOSTCALL_SESSION_MARKER, (adapter, after.get("CODEX_SESSION_ID"))


def test_Q_session_id_claude_child_lacks_CODEX_SESSION_ID_by_name_and_keeps_the_near_miss():
    hostcall_session_id_is_dropped_by_name("claude")


def test_Q_session_id_codex_child_lacks_CODEX_SESSION_ID_by_name_and_keeps_the_near_miss():
    hostcall_session_id_is_dropped_by_name("codex")


def diff_files(d, lead=""):
    """{path: "deleted" | "new" | "modified" | "renamed"} by each `diff --git` header in `d`, paths with `lead` taken off."""
    out, cur = {}, None
    for line in d.splitlines():
        m = re.match(r"^diff --git a/(.*) b/(.*)$", line)
        if m:
            a, b = (p[len(lead):] if lead and p.startswith(lead) else p for p in m.groups())
            cur = b
            out[cur] = "modified" if a == b else "renamed"
            out.setdefault("a:" + a, "a-side")
        elif cur and line.startswith("deleted file mode"):
            out[cur] = "deleted"
        elif cur and line.startswith("new file mode"):
            out[cur] = "new"
        elif cur and line.startswith(("rename from", "rename to", "similarity index")):
            out[cur] = "renamed"
    return out


def rename_project(root, sub=None):
    """Three committed files under `root/sub`, a reviews/ record and a lock-declared custom-record.json, then (after a
    review) three `git mv`s: a source file into reviews/, a source file to another source path, the record to a source path.
    Returns (target, the commit before the moves)."""
    t = os.path.join(root, sub) if sub else root
    write(os.path.join(t, "hunsu.lock.json"), STRICT_LOCK)
    write(os.path.join(t, "src.py"), "srcmark = 1\nsrcmark_two = 2\n")
    write(os.path.join(t, "old.py"), "oldmark = 1\noldmark_two = 2\n")
    write(os.path.join(t, "custom-record.json"), '{"recmark": 1, "recmark_two": 2}\n')
    if sub:
        write(os.path.join(root, "outer.py"), "outer = 1\n")
    git(root, "add", "-A"); git(root, "commit", "-qm", "before the moves")
    base = git(root, "rev-parse", "HEAD")
    run("review", "--target", t)
    os.makedirs(os.path.join(t, "reviews"), exist_ok=True)
    git(t, "mv", "src.py", "reviews/src.py")
    git(t, "mv", "old.py", "new.py")
    git(t, "mv", "custom-record.json", "moved.json")
    status = git(t, "status", "--porcelain", "--", ".")
    assert "src.py -> " in status and "old.py -> " in status and "custom-record.json -> " in status, "git pairs these as renames: " + status
    return t, base


def renames_are_split(packet, lead=""):
    d, new = packet["diff"], packet["new_files"]
    files = diff_files(d, lead)
    assert "rename from" not in d and "rename to" not in d, "renames are not paired (--no-renames): " + d
    assert files.get("src.py") == "deleted" and "-srcmark = 1" in d, "a source file moved into reviews/ shows its deletion: %r\n%s" % (files, d)
    assert not [k for k in files if k.endswith("reviews/src.py")] and "+srcmark = 1" not in d, "nothing of reviews/src.py: " + d
    assert not [k for k in new if k.endswith("reviews/src.py")], list(new)
    assert files.get("old.py") == "deleted" and "-oldmark = 1" in d, "the old path's deletion: %r\n%s" % (files, d)
    assert files.get("new.py") == "new" and "+oldmark = 1" in d, "the new path as a new file: %r\n%s" % (files, d)
    assert files.get("moved.json") == "new" and '+{"recmark": 1' in d, "a record moved to a source path shows the new file: %r\n%s" % (files, d)
    assert "custom-record.json" not in files and "a:custom-record.json" not in files and '-{"recmark"' not in d, \
        "and not the record's deletion: %r\n%s" % (files, d)


def test_Q_review_fixes_renames_from_the_latest_reviews_base_are_split_and_judged_side_by_side():
    with Project() as pj:
        t, _ = rename_project(pj.dir)
        renames_are_split(late_packet(pj, os.path.join(t, ".dwitbuk", "packet")))


def test_Q_review_fixes_renames_with_since_are_split_and_judged_side_by_side():
    with Project() as pj:
        t, base = rename_project(pj.dir)
        folder = os.path.join(t, ".dwitbuk", "packet")
        code, out = run("eyes", "request", "--out", folder, "--since", base, "--target", t)
        assert code == 0, out
        renames_are_split(dwitbuk.load(os.path.join(folder, "eyes-request.json")))


def test_Q_review_fixes_renames_for_a_target_inside_a_larger_repository_are_split_and_judged_side_by_side():
    with Project() as pj:
        t, base = rename_project(pj.dir, "proj")
        assert git(t, "rev-parse", "--show-prefix") == "proj/"
        packet = late_packet(type("Sub", (), {"dir": t}), os.path.join(t, ".dwitbuk", "packet"))
        renames_are_split(packet, "proj/")
        assert "outer" not in packet["diff"], packet["diff"]
        folder = os.path.join(t, ".dwitbuk", "packet2")
        code, out = run("eyes", "request", "--out", folder, "--since", base, "--target", t)
        assert code == 0, out
        renames_are_split(dwitbuk.load(os.path.join(folder, "eyes-request.json")), "proj/")


@contextlib.contextmanager
def recorded_git():
    """dwitbuk.git and dwitbuk.git_patch, the seam path_diff's content diff calls go through, wrapped: every call's argv
    recorded, the real call made."""
    assert callable(getattr(dwitbuk, "git_patch", None)), "dwitbuk.git_patch(target, *args) is the patch seam"
    calls, real, real_patch = [], dwitbuk.git, dwitbuk.git_patch
    def recorder(target, *a):
        calls.append(list(a))
        return real(target, *a)
    def patch_recorder(target, *a):
        calls.append(list(a))
        return real_patch(target, *a)
    dwitbuk.git, dwitbuk.git_patch = recorder, patch_recorder
    try:
        yield calls
    finally:
        dwitbuk.git, dwitbuk.git_patch = real, real_patch


@contextlib.contextmanager
def batch_bytes(n):
    assert hasattr(dwitbuk, "PATHSPEC_BATCH_BYTES"), "dwitbuk.PATHSPEC_BATCH_BYTES is a module-level int"
    old = dwitbuk.PATHSPEC_BATCH_BYTES
    assert isinstance(old, int) and not isinstance(old, bool) and 0 < old < 1048576, old
    dwitbuk.PATHSPEC_BATCH_BYTES = n
    try:
        yield
    finally:
        dwitbuk.PATHSPEC_BATCH_BYTES = old


def pathspec_bytes(argv):
    """The bytes of a git call's pathspec arguments: everything after `--`."""
    if "--" not in argv:
        return 0
    return sum(len(x.encode("utf-8")) for x in argv[argv.index("--") + 1:])


def test_Q_review_fixes_batching_diffs_every_changed_file_in_gits_order_within_the_limit():
    limit = 200
    with Project() as pj:
        names = ["pkg/zz_%02d.py" % i for i in range(30, 0, -1)] + ["aa/m%02d.py" % i for i in range(30)] + ["mid.py"]
        for n in names:
            write(os.path.join(pj.dir, n), "old %s\n" % n)
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "many")
        run("review", "--target", pj.dir)
        for n in names:
            write(os.path.join(pj.dir, n), "new %s\n" % n)
        listed = git(pj.dir, "diff", "--no-renames", "--name-only", "HEAD").splitlines()
        assert sorted(listed) == sorted(names) and len(listed) == len(names), listed
        one = subprocess.run(["git", "diff", "--no-renames", "HEAD", "--", *listed], cwd=pj.dir, capture_output=True,
                             text=True, encoding="utf-8").stdout
        assert len(one) < 80000 and sum(len(n.encode()) for n in listed) > 3 * limit, "the change set needs several batches"
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        with batch_bytes(limit), recorded_git() as calls:
            code, out = run("eyes", "request", "--out", folder, "--target", pj.dir)
            assert dwitbuk.PATHSPEC_BATCH_BYTES == limit
        assert code == 0, out
        packet = dwitbuk.load(os.path.join(folder, "eyes-request.json"))
        diffs = [c for c in calls if c and c[0] == "diff"]
        over = [(pathspec_bytes(c), c[:6]) for c in diffs if pathspec_bytes(c) > limit]
        assert not over, "every git diff call keeps its pathspec arguments within PATHSPEC_BATCH_BYTES=%d: %r" % (limit, over)
        content = [c for c in diffs if "--name-only" not in c and "--name-status" not in c and "--stat" not in c]
        assert len(content) >= 3, "the kept pathspecs are given to git in batches: %r" % ([c[:4] for c in content],)
        d = packet["diff"]
        order = [m for m in re.findall(r"^diff --git a/(\S+) b/", d, re.M)]
        assert order == listed, "every changed file, in the order git listed them: %r" % (order,)
        assert d == one, "the batched diff is the text one unbatched git diff gives"
        assert not packet.get("diff_truncated"), packet.get("diff_truncated")


def test_Q_review_fixes_batching_the_limit_is_restored_and_defaults_well_under_the_argument_limit():
    assert hasattr(dwitbuk, "PATHSPEC_BATCH_BYTES"), "dwitbuk.PATHSPEC_BATCH_BYTES is a module-level int"
    v = dwitbuk.PATHSPEC_BATCH_BYTES
    assert isinstance(v, int) and not isinstance(v, bool) and 1024 <= v <= 262144, v
    with batch_bytes(17):
        assert dwitbuk.PATHSPEC_BATCH_BYTES == 17
    assert dwitbuk.PATHSPEC_BATCH_BYTES == v


def test_Q_review_fixes_batching_a_change_set_whose_names_exceed_the_argument_limit_no_longer_fails():
    with Project() as pj:
        deep = os.path.join(*["d%d_" % i + "x" * 200 for i in range(4)])   # ~820 bytes of directories per path
        names = [os.path.join(deep, "f%04d.py" % i).replace(os.sep, "/") for i in range(1400)]
        assert sum(len(n.encode()) + 1 for n in names) > 1048576 + 65536, "the names alone pass the platform's ARG_MAX"
        for n in names:
            write(os.path.join(pj.dir, n), "o\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "long names")
        run("review", "--target", pj.dir)
        for n in names:
            write(os.path.join(pj.dir, n), "n\n")
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        code, out = run("eyes", "request", "--out", folder, "--target", pj.dir)
        assert code == 0, out
        packet = dwitbuk.load(os.path.join(folder, "eyes-request.json"))
        assert packet.get("diff_truncated") is True, "past the 80000-character cut: %r" % (packet.get("diff_truncated"),)
        assert packet["diff"].startswith("diff --git a/" + names[0] + " "), packet["diff"][:300]


def test_Q_review_fixes_excluded_diff_of_a_bare_entry_holds_nothing_under_a_directory_that_took_its_name():
    with Project() as pj:
        files_base, dirs_base = strict_project(pj)
        write(os.path.join(pj.dir, "hunsu.json", "child.py"), "hchild = 2\n")
        write(os.path.join(pj.dir, "custom-record.json", "child.py"), "cchild = 2\n")
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": [], "since": {".": dirs_base}, "excluded": {"record-paths": ["hunsu.json", "custom-record.json"]}}
        env = dwitbuk.verify_packet(req)
        assert sorted(env["excluded"]) == ["custom-record.json", "hunsu.json"], env.get("excluded")
        assert "excluded_diff" not in env, sorted(env)   # 11-09, D2: the packet holds no diff of the excluded paths
        assert "hchild" not in json.dumps(env) and "cchild" not in json.dumps(env), json.dumps(env)
        ed = dwitbuk.path_diff(pj.dir, ["hunsu.json", "custom-record.json"], ("HEAD",), cut=40000)
        assert "child.py" not in ed and "hchild" not in ed and "cchild" not in ed, \
            "a bare entry names only that file, never files under a directory that took its name: " + ed
        both = dwitbuk.verify_packet(dict(req, touched=["hunsu.json/child.py", "custom-record.json/child.py"]))
        assert "+hchild = 2" in both["diff"] and "+cchild = 2" in both["diff"], "they are source, in diff when touched: " + both["diff"]
        assert "excluded_diff" not in both, sorted(both)


def test_Q_review_fixes_excluded_diff_of_a_trailing_slash_entry_shows_its_files_and_a_bare_file_its_own():
    with Project() as pj:
        write(os.path.join(pj.dir, "alpha", "x.json"), '"old ax"\n')
        write(os.path.join(pj.dir, "alpha", "deep", "y.json"), '"old ay"\n')
        write(os.path.join(pj.dir, "notes.json"), '"old notes"\n')
        write(os.path.join(pj.dir, "notes.json.bak"), '"old bak"\n')
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "records")
        since = git(pj.dir, "rev-parse", "HEAD")
        for rel in ("alpha/x.json", "alpha/deep/y.json", "notes.json", "notes.json.bak"):
            write(os.path.join(pj.dir, rel), '"new %s"\n' % rel)
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": [], "since": {".": since}, "excluded": {"record-paths": ["alpha/", "notes.json"]}}
        env = dwitbuk.verify_packet(req)
        assert env["excluded"] == ["alpha/", "notes.json"] and "excluded_diff" not in env, sorted(env)   # 11-09, D2
        assert "new alpha" not in json.dumps(env) and "new notes" not in json.dumps(env), json.dumps(env)
        ed = dwitbuk.path_diff(pj.dir, ["alpha/x.json", "alpha/deep/y.json", "notes.json"], ("HEAD",), cut=40000)
        assert '+"new alpha/x.json"' in ed and '+"new alpha/deep/y.json"' in ed, "the directory's files, each its own section: " + ed
        assert '+"new notes.json"' in ed, "a bare entry that is a file shows that file: " + ed
        assert "notes.json.bak" not in ed, "and nothing beside it: " + ed


def nested_repo(at):
    os.makedirs(at, exist_ok=True)
    subprocess.run(["git", "init", "-q", at], capture_output=True)
    write(os.path.join(at, "inside.py"), "inside = 1\n")


def test_Q_review_fixes_an_untracked_nested_repository_is_not_a_new_file_and_the_eyes_request_completes():
    with Project() as pj:
        run("review", "--target", pj.dir)
        nested_repo(os.path.join(pj.dir, "vendored"))
        write(os.path.join(pj.dir, "fresh.py"), "fresh = 1\n")
        assert "vendored/" in git(pj.dir, "ls-files", "--others", "--exclude-standard").splitlines(), "git lists it as a directory"
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        code, out = run("eyes", "request", "--out", folder, "--target", pj.dir)
        assert code == 0, out
        new = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["new_files"]
        assert not [k for k in new if k.rstrip("/") == "vendored" or k.startswith("vendored/")], list(new)
        assert "fresh.py" in new, list(new)


def test_Q_review_fixes_an_untracked_nested_repository_at_a_declared_files_name_is_not_a_new_file_and_the_eyes_request_completes():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), STRICT_LOCK)
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "lock")
        run("review", "--target", pj.dir)
        nested_repo(os.path.join(pj.dir, "custom-record.json"))
        nested_repo(os.path.join(pj.dir, "hunsu.json"))
        write(os.path.join(pj.dir, "fresh.py"), "fresh = 1\n")
        others = git(pj.dir, "ls-files", "--others", "--exclude-standard").splitlines()
        assert "custom-record.json/" in others and "hunsu.json/" in others, others
        for since in ((), ("--since", pj.base)):
            folder = os.path.join(pj.dir, ".dwitbuk", "packet")
            code, out = run("eyes", "request", "--out", folder, *since, "--target", pj.dir)
            assert code == 0, (since, out)
            new = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["new_files"]
            assert not [k for k in new if k.startswith(("custom-record.json", "hunsu.json"))], list(new)
            assert "fresh.py" in new, list(new)


HOSTCALL_REST = {"HOME": "/dummy/home-parent", "LANG": "ko_KR.UTF-8", "XDG_CONFIG_HOME": "/dummy/xdg-config",
                 "SSH_AUTH_SOCK": "/dummy/ssh-agent.sock", "CLAUDE_CODE_USE_BEDROCK": "1", "DWITBUK_TEST_MARKER_Q7": "marker value"}


def hostcall_rest_of_the_parent(adapter):
    parent = dict(hostcall_parent(adapter), **HOSTCALL_REST)
    call, before, _ = hostcall_call(adapter, parent)
    want = {k: v for k, v in before.items() if k not in HOSTCALL_DROPPED}
    want.update(AGENT_HOST=HOSTCALL_HOSTS[adapter], AGENT_WORKER="1")
    if adapter == "claude":
        want["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    env = call["env"]
    for k, v in HOSTCALL_REST.items():
        assert env.get(k) == v, (adapter, k, env.get(k), v)
    assert env.get(HOSTCALL_NEAR_MISS[0]) == HOSTCALL_NEAR_MISS[1], (adapter, "near-miss", env.get(HOSTCALL_NEAR_MISS[0]))
    missing = sorted(set(want) - set(env))
    extra = sorted(set(env) - set(want))
    differ = sorted(k for k in set(want) & set(env) if want[k] != env[k])
    assert env == want, ("the child's env is the parent's minus exactly the seven keys", adapter, missing, extra, differ)


def test_Q_review_fixes_hostcall_claude_child_env_is_the_parents_minus_exactly_the_seven_keys():
    hostcall_rest_of_the_parent("claude")


def test_Q_review_fixes_hostcall_codex_child_env_is_the_parents_minus_exactly_the_seven_keys():
    hostcall_rest_of_the_parent("codex")


GITLINK_LOCK = {"record-paths": {"custom": ["custom-record.json", "custom-dir/"]}}


def gitlink(pj, rel):
    """A nested repository at rel with child.py committed, added to the parent as a gitlink (index mode 160000)."""
    nested = os.path.join(pj.dir, rel)
    write(os.path.join(nested, "child.py"), "child = 1\n")
    git(nested, "init", "-q")
    git(nested, "add", "-A"); git(nested, "commit", "-qm", "nested")
    git(pj.dir, "add", rel)
    entry = git(pj.dir, "ls-files", "-s", "--", rel)
    assert entry.startswith("160000 ") and entry.endswith("\t" + rel), (rel, entry)
    return nested


def gitlink_stales(pj, rel, n=2):
    """Bind a late eyes answer, edit rel/child.py to child = n, and return consume's (code, out)."""
    folder = os.path.join(pj.dir, ".dwitbuk", "packet")
    eyes_answer(pj, folder)
    write(os.path.join(pj.dir, rel, "child.py"), "child = %d  # edited in %s\n" % (n, rel))
    return run("eyes", "consume", "--dir", folder, "--target", pj.dir)


def test_Q_gitlink_a_gitlink_at_a_bare_declaration_is_source_like_one_at_an_undeclared_path():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), GITLINK_LOCK)
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "lock")
        for rel in ("lib", "custom-dir/engine", "custom-record.json"):
            gitlink(pj, rel)
        git(pj.dir, "commit", "-qm", "gitlinks")
        assert git(pj.dir, "status", "--porcelain") == "", git(pj.dir, "status", "--porcelain")
        # is_record is unchanged: the bare declaration is still an exact path, whatever the disk holds there
        rp = dwitbuk.record_paths(pj.dir)
        assert dwitbuk.is_record("custom-record.json", rp) and not dwitbuk.is_record("custom-record.json/child.py", rp), rp
        run("review", "--target", pj.dir)
        code, out = gitlink_stales(pj, "lib")
        assert code != 0 and "source changed" in out, ("control: a gitlink at undeclared lib is source", out)
        code, out = gitlink_stales(pj, "custom-dir/engine")
        assert code == 0, ("a gitlink under the directory declaration custom-dir/ stays excluded", out)
        code, out = gitlink_stales(pj, "custom-record.json")
        assert code != 0 and "source changed" in out, ("a gitlink at the bare declaration custom-record.json is source", out)
        # the second time, too: a fresh answer then another edit (new contents) inside the declared gitlink
        code, out = gitlink_stales(pj, "custom-record.json", 3)
        assert code != 0 and "source changed" in out, ("again", out)


def test_Q_gitlink_a_regular_tracked_file_at_the_bare_declaration_stays_excluded():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), GITLINK_LOCK)
        write(os.path.join(pj.dir, "custom-record.json"), {"r": 1})
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "record as a file")
        entry = git(pj.dir, "ls-files", "-s", "--", "custom-record.json")
        assert entry.startswith("100644 "), entry
        gitlink(pj, "custom-dir")
        git(pj.dir, "commit", "-qm", "a gitlink at the directory declaration itself")
        run("review", "--target", pj.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder)
        write(os.path.join(pj.dir, "custom-record.json"), {"r": 2})
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code == 0, ("custom-record.json as a file is a record", out)
        code, out = gitlink_stales(pj, "custom-dir")
        assert code == 0, ("a gitlink at custom-dir, marked custom-dir/, is the directory declaration's own", out)
        eyes_answer(pj, folder)
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "source changed" in out, ("source beside the record still counts", out)


def diff_sections(d):
    """[(b-side path, the section's text)] for each `diff --git` header in `d`, in order."""
    out = []
    for part in re.split(r"(?m)^(?=diff --git )", d):
        m = re.match(r"diff --git a/(.*) b/(.*)$", part, re.M)
        if m:
            out.append((m.group(2), part))
    return out


# git's plain per-file form whatever a global configuration says: what the comparisons below ask git for
PLAIN_DIFF = ("--no-color", "--no-ext-diff", "--no-relative", "--submodule=short", "--src-prefix=a/", "--dst-prefix=b/")


def unbatched(cwd, base, names):
    """One `git diff --no-renames` over literal pathspecs for every name, as the batching would have it if it never split.
    Read as git wrote it: decoded, never newline-translated, so a lone CR in a file's content stays where it is."""
    return subprocess.run(["git", "diff", *PLAIN_DIFF, "--no-renames", *base, "--", *(":(literal)" + n for n in names)], cwd=cwd,
                          capture_output=True).stdout.decode("utf-8")


def file_became_directory(pj, lock, child, child_text="childmark = 1\n"):
    """A committed source file `foo` (and a.py, z.py), then foo replaced by a directory holding `child`, committed with a
    change to z.py. Returns (the commit with the file, the commit with the directory)."""
    write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
    write(os.path.join(pj.dir, "foo"), "foomark = 1\n")
    write(os.path.join(pj.dir, "z.py"), "zmark = 1\n")
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "foo as a file")
    file_base = git(pj.dir, "rev-parse", "HEAD")
    os.unlink(os.path.join(pj.dir, "foo"))
    write(os.path.join(pj.dir, "foo", child), child_text)
    write(os.path.join(pj.dir, "z.py"), "zmark = 2\n")
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "foo replaced by a directory")
    assert git(pj.dir, "ls-files", "foo") == "foo/" + child, git(pj.dir, "ls-files", "foo")
    listed = git(pj.dir, "diff", "--no-renames", "--name-only", file_base).splitlines()
    assert "foo" in listed and "foo/" + child in listed, "git lists both the file and the child: %r" % listed
    return file_base, git(pj.dir, "rev-parse", "HEAD")


def test_Q_exact_sections_eyes_request_diff_holds_the_replaced_files_deletion_and_nothing_of_a_declared_record_under_it():
    with Project() as pj:
        file_base, _ = file_became_directory(pj, {"record-paths": {"custom": ["foo/rec.json"]}}, "rec.json", '{"recmark": 1}\n')
        run("review", "--target", pj.dir)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        code, out = run("eyes", "request", "--out", folder, "--since", file_base, "--target", pj.dir)
        assert code == 0, out
        packet = dwitbuk.load(os.path.join(folder, "eyes-request.json"))
        d = packet["diff"]
        files = diff_files(d)
        assert files.get("foo") == "deleted" and "-foomark = 1" in d, "the source file foo's deletion: %r\n%s" % (files, d)
        assert files.get("z.py") == "modified" and "+zmark = 2" in d, "control: other source is diffed: %r\n%s" % (files, d)
        assert not [k for k in files if "rec.json" in k], "no section of the declared record foo/rec.json: %r\n%s" % (files, d)
        assert "recmark" not in d and "rec.json" not in d, "nothing of the record's content or name: " + d
        assert [p for p, _ in diff_sections(d)].count("foo") == 1, d
        assert not [k for k in packet["new_files"] if "rec.json" in k], list(packet["new_files"])


def test_Q_exact_sections_excluded_diff_of_a_bare_entry_replaced_by_a_directory_with_a_staged_child_is_the_files_deletion_only():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), STRICT_LOCK)
        write(os.path.join(pj.dir, "custom-record.json"), '{"recmark": 1}\n')
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "the record as a file")
        head = git(pj.dir, "rev-parse", "HEAD")
        os.unlink(os.path.join(pj.dir, "custom-record.json"))
        write(os.path.join(pj.dir, "custom-record.json", "child.py"), "cchild = 1\n")
        git(pj.dir, "add", "custom-record.json/child.py")
        status = git(pj.dir, "status", "--porcelain").splitlines()
        assert "D  custom-record.json" in status and "A  custom-record.json/child.py" in status, "staged, not committed: %r" % status
        assert git(pj.dir, "rev-parse", "HEAD") == head
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": [], "since": {".": head}, "excluded": {"record-paths": ["custom-record.json"]}}
        env = dwitbuk.verify_packet(req)
        assert env.get("excluded") == ["custom-record.json"], env.get("excluded")
        assert "excluded_diff" not in env and "recmark" not in json.dumps(env) and "cchild" not in json.dumps(env), json.dumps(env)   # 11-09, D2
        ed = dwitbuk.path_diff(pj.dir, ["custom-record.json"], ("HEAD",), cut=40000)
        files = diff_files(ed)
        assert files.get("custom-record.json") == "deleted" and '-{"recmark": 1}' in ed, "the file's deletion: %r\n%s" % (files, ed)
        assert list(files) == ["custom-record.json", "a:custom-record.json"], "that path's section only: %r\n%s" % (files, ed)
        assert "child.py" not in ed and "cchild" not in ed, "nothing of the staged child.py: " + ed
        # the second call gives the same text
        assert dwitbuk.path_diff(pj.dir, ["custom-record.json"], ("HEAD",), cut=40000) == ed


def test_Q_exact_sections_a_batch_boundary_between_foo_and_foo_child_gives_each_section_once():
    with Project() as pj:
        file_base, dir_base = file_became_directory(pj, {"record-paths": {}}, "a.py", "famark = 1\n")
        run("review", "--target", pj.dir)
        listed = git(pj.dir, "diff", "--no-renames", "--name-only", file_base).splitlines()
        assert listed[:2] == ["foo", "foo/a.py"], listed
        # ":(literal)foo" and ":(literal)foo/a.py" cannot share a batch of 20 bytes; foo is first in its own
        limit = len(":(literal)foo/a.py") + 1
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        with batch_bytes(limit), recorded_git() as calls:
            code, out = run("eyes", "request", "--out", folder, "--since", file_base, "--target", pj.dir)
        assert code == 0, out
        content = [c for c in calls if c and c[0] == "diff" and "--name-only" not in c and "--name-status" not in c and "--stat" not in c]
        assert len(content) >= 2, "a boundary falls in the change set: %r" % (content,)
        d = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]
        headers = re.findall(r"^diff --git a/(.*) b/", d, re.M)
        assert len(headers) == len(set(headers)), "every diff --git header once: %r\n%s" % (headers, d)
        assert headers == listed, "each kept path, in git's order: %r vs %r" % (headers, listed)
        assert d.count("+famark = 1") == 1 and d.count("-foomark = 1") == 1, d
        want = "".join(t for p, t in diff_sections(unbatched(pj.dir, [file_base], listed)) if p in listed)
        assert d == want, "one unbatched call's text, filtered to the kept paths:\n%s\n---\n%s" % (d, want)
        # without a file/directory change in the range the text is one unbatched call over the kept paths
        write(os.path.join(pj.dir, "foo", "a.py"), "famark = 2\n")
        write(os.path.join(pj.dir, "z.py"), "zmark = 3\n")
        with batch_bytes(limit):
            code, out = run("eyes", "request", "--out", folder, "--since", dir_base, "--target", pj.dir)
        assert code == 0, out
        d = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]
        kept = git(pj.dir, "diff", "--no-renames", "--name-only", dir_base).splitlines()
        assert kept == ["foo/a.py", "z.py"], kept
        assert d == unbatched(pj.dir, [dir_base], kept), d


def test_Q_exact_sections_a_single_path_longer_than_the_batch_limit_is_diffed_beside_short_ones_in_gits_order():
    with Project() as pj:
        long_name = "m_" + "x" * 120 + ".py"
        names = ["aa.py", long_name, "zz.py"]
        for n in names:
            write(os.path.join(pj.dir, n), "old %s\n" % n[:8])
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "short and long")
        run("review", "--target", pj.dir)
        for n in names:
            write(os.path.join(pj.dir, n), "new %s\n" % n[:8])
        listed = git(pj.dir, "diff", "--no-renames", "--name-only", "HEAD").splitlines()
        assert listed == ["a.py", "aa.py", long_name, "zz.py"] or listed == ["aa.py", long_name, "zz.py"], listed
        limit = 40
        assert len((":(literal)" + long_name).encode()) > limit
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        with batch_bytes(limit), recorded_git() as calls:
            code, out = run("eyes", "request", "--out", folder, "--target", pj.dir)
        assert code == 0, ("an oversized path is not refused", out)
        d = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]
        headers = re.findall(r"^diff --git a/(.*) b/", d, re.M)
        assert headers == listed, "every path, the long one in its place: %r" % (headers,)
        assert "+new m_xxxxx" in d and "-old m_xxxxx" in d, d
        assert d == unbatched(pj.dir, ["HEAD"], listed), d
        alone = [c for c in calls if c and c[0] == "diff" and ":(literal)" + long_name in c]
        assert alone and all(c[c.index("--") + 1:] == [":(literal)" + long_name] for c in alone), "the long path travels alone: %r" % alone


def test_Q_exact_sections_a_gitlink_inside_a_walked_nested_repository_is_marked_like_one_at_the_top_level():
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"custom": ["vendor/rec.json"]}})
        vendor = os.path.join(pj.dir, "vendor")
        inner = os.path.join(vendor, "rec.json")
        write(os.path.join(vendor, "v.py"), "v = 1\n")
        git(vendor, "init", "-q")
        write(os.path.join(inner, "child.py"), "child = 1\n")
        git(inner, "init", "-q")
        git(inner, "add", "-A"); git(inner, "commit", "-qm", "innermost")
        git(vendor, "add", "v.py", "rec.json"); git(vendor, "commit", "-qm", "vendor")
        entry = git(vendor, "ls-files", "-s", "--", "rec.json")
        assert entry.startswith("160000 ") and entry.endswith("\trec.json"), entry
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "vendor as a gitlink")
        entry = git(pj.dir, "ls-files", "-s", "--", "vendor")
        assert entry.startswith("160000 ") and entry.endswith("\tvendor"), entry
        rp = dwitbuk.record_paths(pj.dir)
        assert dwitbuk.is_record("vendor/rec.json", rp) and not dwitbuk.is_record("vendor/rec.json/child.py", rp), rp
        run("review", "--target", pj.dir)
        code, out = gitlink_stales(pj, "vendor/rec.json")
        assert code != 0 and "source changed" in out, ("a gitlink at vendor/rec.json inside vendor is source, as at the top level", out)
        code, out = gitlink_stales(pj, "vendor/rec.json", 3)
        assert code != 0 and "source changed" in out, ("again", out)
        code, out = gitlink_stales(pj, "vendor", 4)   # control: writes vendor/child.py, a new file in vendor
        assert code != 0 and "source changed" in out, ("control: vendor itself is walked", out)


HOSTILE_GIT_CONFIG = ("[color]\n\tui = always\n[diff]\n\trelative = true\n\tsubmodule = log\n"
                      "\tnoprefix = true\n\tmnemonicPrefix = true\n")


@contextlib.contextmanager
def global_git_config(text):
    """GIT_CONFIG_GLOBAL pointed at a temporary file holding `text` (no system configuration), restored afterwards."""
    d = tempfile.mkdtemp(prefix="dwitbuk-gitconfig-")
    path = os.path.join(d, "gitconfig")
    write(path, text)
    old = {k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")}
    os.environ["GIT_CONFIG_GLOBAL"], os.environ["GIT_CONFIG_NOSYSTEM"] = path, "1"
    try:
        yield path
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(d, ignore_errors=True)


def changed_gitlink(nested):
    """A new commit in the nested repository: its gitlink in the parent now differs from the committed one."""
    write(os.path.join(nested, "child.py"), "child = 2\n")
    git(nested, "add", "-A"); git(nested, "commit", "-qm", "nested moves")


def plain_and_configured(produce):
    """produce() under an empty global configuration, then under the hostile one; both texts."""
    with global_git_config(""):
        plain = produce()
    with global_git_config(HOSTILE_GIT_CONFIG):
        assert git(os.getcwd(), "config", "--global", "--get", "diff.relative") == "true", "the hostile configuration is read"
        configured = produce()
    return plain, configured


def sections_once(d, must):
    headers = re.findall(r"^diff --git a/(.*) b/", d, re.M)
    assert len(headers) == len(set(headers)), "each kept path's section once: %r\n%s" % (headers, d)
    for path in must:
        assert headers.count(path) == 1, "%s's section, once: %r\n%s" % (path, headers, d)
    return headers


def gitconfig_project(pj, root):
    """Under `root` (pj.dir or a subdirectory): a source file, a lock-declared record, and a committed gitlink lib; a review;
    then the source file, the record and the gitlink all change. Returns (target, the nested repository)."""
    write(os.path.join(root, "hunsu.lock.json"), STRICT_LOCK)
    write(os.path.join(root, "src.py"), "srcmark = 1\n")
    write(os.path.join(root, "custom-record.json"), '{"r": 1}\n')
    if root != pj.dir:
        write(os.path.join(pj.dir, "outer.py"), "outer = 1\n")
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "before")
    nested = os.path.join(root, "lib")
    write(os.path.join(nested, "child.py"), "child = 1\n")
    git(nested, "init", "-q"); git(nested, "add", "-A"); git(nested, "commit", "-qm", "nested")
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "gitlink")
    rel = os.path.relpath(nested, pj.dir).replace(os.sep, "/")
    assert git(pj.dir, "ls-files", "-s", "--", rel).startswith("160000 "), "lib is a gitlink"
    run("review", "--target", root)
    write(os.path.join(root, "src.py"), "srcmark = 2\n")
    write(os.path.join(root, "custom-record.json"), '{"r": 2}\n')
    if root != pj.dir:
        write(os.path.join(pj.dir, "outer.py"), "outer = 2\n")
    changed_gitlink(nested)
    return root, nested


def eyes_diff_under_both(target, since=()):
    folder = os.path.join(target, ".dwitbuk", "packet")
    def produce():
        code, out = run("eyes", "request", "--out", folder, *since, "--target", target)
        assert code == 0, out
        return dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]
    return plain_and_configured(produce)


def test_Q_git_config_eyes_request_diff_of_a_top_level_target_is_the_same_text_whatever_the_global_configuration():
    with global_git_config(""), Project() as pj:
        target, _ = gitconfig_project(pj, pj.dir)
        plain, configured = eyes_diff_under_both(target)
        assert plain, "the diff is not empty"
        headers = sections_once(plain, ("src.py", "lib"))
        assert "+srcmark = 2" in plain and "Subproject commit" in plain, plain
        assert "custom-record.json" not in headers, plain
        assert "\x1b[" not in configured, "no colour: %r" % configured
        assert configured == plain, "the same text as with an empty global configuration:\n%s\n---\n%s" % (configured, plain)
        sections_once(configured, ("src.py", "lib"))
        # from the commit holding the gitlink: the gitlink is modified, not new
        plain, configured = eyes_diff_under_both(target, ("--since", git(pj.dir, "rev-parse", "HEAD")))
        assert "-Subproject commit" in plain and "+Subproject commit" in plain, plain
        sections_once(plain, ("src.py", "lib"))
        assert configured == plain, "a modified gitlink, the same text:\n%s\n---\n%s" % (configured, plain)


def test_Q_git_config_eyes_request_diff_of_a_target_inside_a_larger_repository_is_the_same_text_whatever_the_global_configuration():
    with global_git_config(""), Project() as pj:
        target, _ = gitconfig_project(pj, os.path.join(pj.dir, "proj"))
        assert git(target, "rev-parse", "--show-prefix") == "proj/"
        plain, configured = eyes_diff_under_both(target)
        assert plain, "the diff is not empty"
        assert "+srcmark = 2" in plain and "Subproject commit" in plain and "outer" not in plain, plain
        headers = re.findall(r"^diff --git a/(.*) b/", plain, re.M)
        assert len(headers) == len(set(headers)) and len(headers) == 2, headers
        assert all(h.endswith(("src.py", "lib")) for h in headers), headers
        assert "\x1b[" not in configured, "no colour: %r" % configured
        assert configured == plain, "the same text as with an empty global configuration:\n%s\n---\n%s" % (configured, plain)


def test_Q_git_config_eyes_request_diff_is_the_same_on_the_second_call_under_the_configuration():
    with global_git_config(""), Project() as pj:
        target, nested = gitconfig_project(pj, pj.dir)
        plain, first = eyes_diff_under_both(target)
        _, second = eyes_diff_under_both(target)
        assert first == second == plain, "again:\n%s\n---\n%s" % (second, plain)


def test_Q_git_config_verify_packet_excluded_diff_is_the_same_text_whatever_the_global_configuration():
    with global_git_config(""), Project() as pj:
        write(os.path.join(pj.dir, "notes.json"), '"old notes"\n')
        write(os.path.join(pj.dir, "recs", "x.json"), '"old x"\n')
        write(os.path.join(pj.dir, "recs", "deep", "y.json"), '"old y"\n')
        write(os.path.join(pj.dir, "src.py"), "srcmark = 1\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "records")
        nested = os.path.join(pj.dir, "lib")
        write(os.path.join(nested, "child.py"), "child = 1\n")
        git(nested, "init", "-q"); git(nested, "add", "-A"); git(nested, "commit", "-qm", "nested")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "gitlink")
        since = git(pj.dir, "rev-parse", "HEAD")
        for rel in ("notes.json", "recs/x.json", "recs/deep/y.json"):
            write(os.path.join(pj.dir, rel), '"new %s"\n' % rel)
        write(os.path.join(pj.dir, "src.py"), "srcmark = 2\n")
        changed_gitlink(nested)
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": ["src.py", "lib"], "since": {".": since}, "excluded": {"record-paths": ["recs/", "notes.json"]}}
        env = dwitbuk.verify_packet(req)
        assert env["excluded"] == ["recs/", "notes.json"] and "excluded_diff" not in env, sorted(env)   # 11-09, D2: no diff of the excluded paths
        assert "new notes" not in json.dumps(env) and "new recs" not in json.dumps(env), json.dumps(env)
        def produce():   # the diff the late-eyes request takes of these records, through path_diff
            return dwitbuk.path_diff(pj.dir, ["notes.json", "recs/x.json", "recs/deep/y.json"], ("HEAD",), cut=40000)
        old_cwd = os.getcwd()
        os.chdir(os.path.join(pj.dir, "recs"))   # a caller standing in a subdirectory: diff.relative has something to bite on
        try:
            plain, configured = plain_and_configured(produce)
        finally:
            os.chdir(old_cwd)
        assert plain, "the records' diff is not empty"
        sections_once(plain, ("notes.json", "recs/x.json", "recs/deep/y.json"))
        assert '+"new notes.json"' in plain and "srcmark" not in plain, plain
        assert "\x1b[" not in configured, "no colour: %r" % configured
        assert configured == plain, "the same text as with an empty global configuration:\n%s\n---\n%s" % (configured, plain)
        sections_once(configured, ("notes.json", "recs/x.json", "recs/deep/y.json"))


def test_Q_git_config_the_tests_unbatched_comparison_asks_git_for_the_pinned_plain_form():
    with global_git_config(""), Project() as pj:
        target, _ = gitconfig_project(pj, os.path.join(pj.dir, "proj"))
        names = git(pj.dir, "diff", "--no-renames", "--name-only", "HEAD").splitlines()
        assert names, names
        with global_git_config(""):
            plain = unbatched(pj.dir, ["HEAD"], names)
        with global_git_config(HOSTILE_GIT_CONFIG):
            configured = unbatched(pj.dir, ["HEAD"], names)
        assert plain and "diff --git a/proj/src.py b/proj/src.py" in plain and "Subproject commit" in plain, plain
        assert configured == plain, configured
        assert "\x1b[" not in configured, configured


def conflict_project(pj, lock=None):
    """c.py changed on two branches and merged: `UU c.py` is left unresolved; a committed d.py is modified in the work tree.
    No review is taken, so the eyes request's diff is the index against the work tree."""
    if lock is not None:
        write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
    write(os.path.join(pj.dir, "c.py"), "head = 1\nside = base\ntail = 1\n")
    write(os.path.join(pj.dir, "d.py"), "dmark = 1\n")
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "c and d")
    git(pj.dir, "checkout", "-q", "-b", "other")
    write(os.path.join(pj.dir, "c.py"), "head = 1\nside = other\ntail = 1\n")
    git(pj.dir, "commit", "-qam", "other side")
    git(pj.dir, "checkout", "-q", "main")
    write(os.path.join(pj.dir, "c.py"), "head = 1\nside = main\ntail = 1\n")
    git(pj.dir, "commit", "-qam", "main side")
    git(pj.dir, "merge", "-q", "other")
    write(os.path.join(pj.dir, "d.py"), "dmark = 2\n")
    status = git(pj.dir, "status", "--porcelain").splitlines()
    assert "UU c.py" in status and " M d.py" in status, "an unresolved conflict and a modified file: %r" % status
    listed = git(pj.dir, "diff", "--no-renames", "--name-only").splitlines()
    assert listed == ["c.py", "c.py", "d.py"], "git lists c.py once per stage: %r" % listed
    assert not dwitbuk.reviews(pj.dir), "no prior review"
    return listed


def run_all(*argv):
    """run(), with stderr kept beside stdout: an error said on either is said."""
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code, out = run(*argv)
    return code, out + err.getvalue()


def cc_headers(d):
    return re.findall(r"^diff (?:--git a/(.*) b/.*|--cc (.*))$", d, re.M)


def conflict_packet_diff(pj, folder):
    if os.path.exists(os.path.join(folder, "eyes-request.json")):
        os.unlink(os.path.join(folder, "eyes-request.json"))
    code, out = run_all("eyes", "request", "--out", folder, "--target", pj.dir)
    assert code == 0, out
    return dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]


def assert_conflict_kept(d, want):
    heads = cc_headers(d)
    assert heads == [("", "c.py"), ("d.py", "")], "c.py's diff --cc section once, then d.py's: %r\n%s" % (heads, d)
    assert d.count("diff --cc c.py") == 1, d
    assert "side = main" in d and "side = other" in d and "<<<<<<<" in d and ">>>>>>>" in d, "both sides' conflicting text: " + d
    assert d.count("side = other") == 1 and d.count("+dmark = 2") == 1 and "-dmark = 1" in d, d
    assert d == want, "the text one plain git diff gives over c.py and d.py:\n%s\n---\n%s" % (d, want)


def test_Q_conflict_eyes_request_without_a_base_keeps_the_conflicted_paths_diff_cc_section_once():
    with Project() as pj:
        conflict_project(pj)
        want = unbatched(pj.dir, [], ["c.py", "d.py"])
        assert want.count("diff --cc c.py") == 1 and "diff --git a/d.py b/d.py" in want, want
        d = conflict_packet_diff(pj, os.path.join(pj.dir, ".dwitbuk", "packet"))
        assert_conflict_kept(d, want)
        assert conflict_packet_diff(pj, os.path.join(pj.dir, ".dwitbuk", "packet")) == d, "the second call gives the same text"


def test_Q_conflict_eyes_request_keeps_the_diff_cc_section_once_wherever_batch_boundaries_fall():
    with Project() as pj:
        conflict_project(pj)
        want = unbatched(pj.dir, [], ["c.py", "d.py"])
        one = len(":(literal)c.py".encode())
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        for limit in sorted({1, one - 1, one, one + 1, 2 * one - 1, 2 * one, 2 * one + 1, 2 * one + 2, 3 * one, 3 * one + 3}):
            with batch_bytes(limit):
                d = conflict_packet_diff(pj, folder)
            try:
                assert_conflict_kept(d, want)
            except AssertionError as err:
                raise AssertionError("PATHSPEC_BATCH_BYTES=%d: %s" % (limit, err))


def test_Q_conflict_a_conflicted_path_that_is_a_declared_record_is_left_out_and_the_rest_stays():
    with Project() as pj:
        conflict_project(pj, {"record-paths": {"custom": ["c.py"]}})
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        for limit in (None, len(":(literal)c.py"), 2 * len(":(literal)c.py") + 1):
            with (batch_bytes(limit) if limit else contextlib.nullcontext()):
                d = conflict_packet_diff(pj, folder)
            assert cc_headers(d) == [("d.py", "")], "only d.py's section (limit %r): %r\n%s" % (limit, cc_headers(d), d)
            assert "c.py" not in d and "side = " not in d and "<<<<<<<" not in d, "nothing of the record c.py: " + d
            assert "+dmark = 2" in d and d == unbatched(pj.dir, [], ["d.py"]), d


UNATTRIBUTABLE = {
    # what diff.submodule=log printed for a gitlink first in a batch: text before the call's first section header
    "before the first header": ("Submodule x 1111111..2222222:\n  > a commit no candidate owns\n", ""),
    # a header starting `diff ` of another kind, after the last readable section
    "a header of another kind": ("", "diff --unknown x\n+a line no candidate owns\n"),
}


@contextlib.contextmanager
def unattributable_git(case):
    """dwitbuk.git_patch, the seam path_diff's content diff calls go through, wrapped: each real content diff call's
    output also carries text outside any section header the filter reads — the UNATTRIBUTABLE case named."""
    assert callable(getattr(dwitbuk, "git_patch", None)), "dwitbuk.git_patch(target, *args) is the patch seam"
    real, (before, after) = dwitbuk.git_patch, UNATTRIBUTABLE[case]
    seen = []
    def wrapped(target, *a):
        out = real(target, *a)
        listing = {"--name-only", "--name-status", "--stat", "--numstat", "--raw", "--summary", "--shortstat"}
        if a and a[0] == "diff" and not listing & set(a) and out and re.search(r"^diff --(git|cc) ", out, re.M):
            seen.append(list(a))
            return before + out + after
        return out
    dwitbuk.git_patch = wrapped
    try:
        yield seen
    finally:
        dwitbuk.git_patch = real


def clear_about_it(text):
    return "Submodule x" in text or "diff --unknown" in text or "section" in text.lower() or "attribut" in text.lower()


def test_Q_conflict_eyes_request_fails_clearly_and_writes_no_packet_when_a_section_cannot_be_attributed():
    for case in UNATTRIBUTABLE:
        with Project() as pj:
            conflict_project(pj)
            folder = os.path.join(pj.dir, ".dwitbuk", "packet")
            assert conflict_packet_diff(pj, folder), "control: the same tree gives a packet without the extra text"
            shutil.rmtree(folder)
            with unattributable_git(case) as seen:
                code, out = run_all("eyes", "request", "--out", folder, "--target", pj.dir)
            assert seen, "%s: a real diff call was made and carried the extra text" % case
            assert code != 0, "%s: a section no candidate owns is not dropped silently: exit %r\n%s" % (case, code, out)
            assert out.strip() and clear_about_it(out), "%s: a clear error that says what could not be attributed: %r" % (case, out)
            assert not os.path.exists(os.path.join(folder, "eyes-request.json")), "%s: no packet is written" % case


def test_Q_conflict_verify_packet_excluded_diff_fails_rather_than_returning_partial_text():
    for case in UNATTRIBUTABLE:
        with Project() as pj:
            write(os.path.join(pj.dir, "notes.json"), '"old notes"\n')
            git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "a record")
            since = git(pj.dir, "rev-parse", "HEAD")
            write(os.path.join(pj.dir, "notes.json"), '"new notes"\n')
            req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
                   "touched": [], "since": {".": since}, "excluded": {"record-paths": ["notes.json"]}}
            env = dwitbuk.verify_packet(req)
            assert env["excluded"] == ["notes.json"] and "excluded_diff" not in env and "new notes" not in json.dumps(env), json.dumps(env)   # 11-09, D2
            assert '+"new notes"' in dwitbuk.path_diff(pj.dir, ["notes.json"], ("HEAD",), cut=40000), "control: the record's own section"
            got, failure = None, None
            with unattributable_git(case) as seen:
                try:
                    got = dwitbuk.path_diff(pj.dir, ["notes.json"], ("HEAD",), cut=40000)
                except (Exception, SystemExit) as err:
                    failure = err
            assert seen, "%s: a real diff call was made and carried the extra text" % case
            assert failure is not None, "%s: path_diff fails, not partial text: %r" % (case, got)
            assert clear_about_it(str(failure)), "%s: a clear error that says what could not be attributed: %r" % (case, failure)


def modify_delete_project(pj, kind, other, lock=None):
    """c.py committed beside `other`; one branch deletes c.py, the other modifies it, and the merge leaves the conflict —
    `DU c.py` when main deleted it, `UD c.py` when the other branch did. `other` is then modified in the work tree.
    No review is taken. Returns git's porcelain status."""
    if lock is not None:
        write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
    write(os.path.join(pj.dir, "c.py"), "cmark = base\n")
    write(os.path.join(pj.dir, other), "omark = 1\n")
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "c and " + other)
    deleter, modifier = ("main", "other") if kind == "DU" else ("other", "main")
    git(pj.dir, "checkout", "-q", "-b", "other")
    git(pj.dir, "checkout", "-q", "main")
    for branch in (deleter, modifier):
        git(pj.dir, "checkout", "-q", branch)
        if branch == deleter:
            git(pj.dir, "rm", "-q", "c.py"); git(pj.dir, "commit", "-qm", "delete c")
        else:
            write(os.path.join(pj.dir, "c.py"), "cmark = changed\n"); git(pj.dir, "commit", "-qam", "modify c")
    git(pj.dir, "checkout", "-q", "main")
    git(pj.dir, "merge", "-q", "other")
    write(os.path.join(pj.dir, other), "omark = 2\n")
    status = [line.strip() for line in git(pj.dir, "status", "--porcelain").splitlines()]
    assert "%s c.py" % kind in status and "M %s" % other in status, "a modify/delete conflict and a modified file: %r" % status
    plain = subprocess.run(["git", "diff", *PLAIN_DIFF, "--no-renames"], cwd=pj.dir, capture_output=True).stdout.decode("utf-8")
    assert plain.count("* Unmerged path c.py\n") == 1 and "diff --cc" not in plain, "git prints the one line, no combined section: " + plain
    assert not dwitbuk.reviews(pj.dir), "no prior review"
    return status


MODIFY_DELETE = [(kind, other) for kind in ("DU", "UD") for other in ("d.py", "b.py")]   # c.py sorts before d.py, after b.py


def unmerged_lines(d):
    return re.findall(r"^\* Unmerged path .*$", d, re.M)


def test_Q_raw_text_a_modify_delete_conflict_is_its_own_unmerged_path_line_once_and_left_out_when_declared():
    for kind, other in MODIFY_DELETE:
        with Project() as pj:
            modify_delete_project(pj, kind, other)
            want = unbatched(pj.dir, [], ["c.py", other])
            assert want.count("* Unmerged path c.py\n") == 1 and "diff --git a/%s b/%s" % (other, other) in want, want
            folder = os.path.join(pj.dir, ".dwitbuk", "packet")
            for limit in (None, 1):
                with (batch_bytes(limit) if limit else contextlib.nullcontext()):
                    code, out = run_all("eyes", "request", "--out", folder, "--target", pj.dir)
                where = "%s c.py beside %s, limit %r" % (kind, other, limit)
                assert code == 0, "%s: a modify/delete conflict never fails the request: %s" % (where, out)
                d = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]
                assert unmerged_lines(d) == ["* Unmerged path c.py"], "%s: the line once, as its own line: %r\n%s" % (where, unmerged_lines(d), d)
                assert d.count("Unmerged path") == 1, "%s: %s" % (where, d)
                assert "+omark = 2" in d and d.count("diff --git a/%s b/%s" % (other, other)) == 1, "%s: %s's section stays: %s" % (where, other, d)
                assert d == want, "%s: the text one plain git diff gives over the kept paths:\n%r\n---\n%r" % (where, d, want)
    modify_delete_record_is_left_out()


def modify_delete_record_is_left_out():
    for kind, other in MODIFY_DELETE:
        with Project() as pj:
            modify_delete_project(pj, kind, other, {"record-paths": {"custom": ["c.py"]}})
            folder = os.path.join(pj.dir, ".dwitbuk", "packet")
            for limit in (None, 1):
                with (batch_bytes(limit) if limit else contextlib.nullcontext()):
                    code, out = run_all("eyes", "request", "--out", folder, "--target", pj.dir)
                where = "%s c.py declared, beside %s, limit %r" % (kind, other, limit)
                assert code == 0, "%s: a declared record's conflict never fails the request: %s" % (where, out)
                d = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]
                assert "Unmerged path" not in d and "c.py" not in d and "cmark" not in d, "%s: nothing of the record c.py: %r" % (where, d)
                assert "+omark = 2" in d and d == unbatched(pj.dir, [], [other]), "%s: %s's section only: %r" % (where, other, d)


def test_Q_raw_text_the_unmerged_path_line_is_not_attached_to_the_other_paths_section():
    for kind, other in MODIFY_DELETE:
        with Project() as pj:
            modify_delete_project(pj, kind, other, {"record-paths": {"custom": [other]}})
            folder = os.path.join(pj.dir, ".dwitbuk", "packet")
            for limit in (None, 1):
                with (batch_bytes(limit) if limit else contextlib.nullcontext()):
                    code, out = run_all("eyes", "request", "--out", folder, "--target", pj.dir)
                where = "%s c.py beside the declared record %s, limit %r" % (kind, other, limit)
                assert code == 0, "%s: %s" % (where, out)
                d = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]
                assert d == "* Unmerged path c.py\n", "%s: c.py's line stays when %s's section is left out: %r" % (where, other, d)
                assert d == unbatched(pj.dir, [], ["c.py"]), "%s: %r" % (where, d)


CR_OLD = b"one\rtwo\r"
CR_NEW = b"one\rdiff --git a/zz b/zz\rdiff these\rtwo\r"


def test_Q_raw_text_a_cr_only_file_holding_lines_beginning_diff_keeps_its_whole_section_at_both_batch_limits():
    with Project() as pj:
        with open(os.path.join(pj.dir, "cr.txt"), "wb") as fh:
            fh.write(CR_OLD)
        write(os.path.join(pj.dir, "d.py"), "dmark = 1\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "a CR-only file")
        run("review", "--target", pj.dir)
        with open(os.path.join(pj.dir, "cr.txt"), "wb") as fh:
            fh.write(CR_NEW)
        write(os.path.join(pj.dir, "d.py"), "dmark = 2\n")
        listed = git(pj.dir, "diff", "--no-renames", "--name-only", "HEAD").splitlines()
        assert listed == ["cr.txt", "d.py"], listed
        want = unbatched(pj.dir, ["HEAD"], listed)
        sections = dict(diff_sections(want))
        assert list(sections) == ["cr.txt", "d.py"], "the raw text splits into git's two sections: %r" % list(sections)
        section = sections["cr.txt"]
        assert "\n-" + CR_OLD.decode() + "\n" in section and "\n+" + CR_NEW.decode() + "\n" in section, repr(section)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        for limit in (None, 1):
            with (batch_bytes(limit) if limit else contextlib.nullcontext()):
                code, out = run_all("eyes", "request", "--out", folder, "--target", pj.dir)
            assert code == 0, "limit %r: a lone CR never fails the request: %s" % (limit, out)
            d = dwitbuk.load(os.path.join(folder, "eyes-request.json"))["diff"]
            raw = d.encode("utf-8")
            assert b"\n-" + CR_OLD + b"\n" in raw, "limit %r: the removed line, raw bytes: %r" % (limit, d)
            assert b"\n+" + CR_NEW + b"\n" in raw, "limit %r: the added line, CRs and all: %r" % (limit, d)
            assert section.encode("utf-8") in raw, "limit %r: cr.txt's whole section, byte for byte:\n%r\n---\n%r" % (limit, d, section)
            assert "+dmark = 2" in d, "limit %r: %r" % (limit, d)
            assert d == want, "limit %r: the text one plain git diff gives:\n%r\n---\n%r" % (limit, d, want)


def sections_of(d):
    """`d` split at each `diff --git`, `diff --cc` or `* Unmerged path` line: the sections git printed, in order."""
    return [part for part in re.split(r"(?m)^(?=diff --git |diff --cc |\* Unmerged path )", d) if part]


def test_Q_bounded_raw_text_a_conflict_sorting_after_a_modified_file_keeps_each_section_once_whole_at_every_limit():
    with Project() as pj:
        write(os.path.join(pj.dir, "e.py"), "head = 1\nside = base\ntail = 1\n")
        write(os.path.join(pj.dir, "d.py"), "dmark = 1\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "d and e")
        git(pj.dir, "checkout", "-q", "-b", "other")
        write(os.path.join(pj.dir, "e.py"), "head = 1\nside = other\ntail = 1\n")
        git(pj.dir, "commit", "-qam", "other side")
        git(pj.dir, "checkout", "-q", "main")
        write(os.path.join(pj.dir, "e.py"), "head = 1\nside = main\ntail = 1\n")
        git(pj.dir, "commit", "-qam", "main side")
        git(pj.dir, "merge", "-q", "other")
        write(os.path.join(pj.dir, "d.py"), "dmark = 2\n")
        status = [line.strip() for line in git(pj.dir, "status", "--porcelain").splitlines()]
        assert "UU e.py" in status and "M d.py" in status, status
        assert not dwitbuk.reviews(pj.dir), "no prior review"
        want = unbatched(pj.dir, [], ["d.py", "e.py"])
        assert cc_headers(want) == [("", "e.py"), ("d.py", "")], "one call gives diff --cc first: %r" % cc_headers(want)
        kept = sections_of(want)
        assert len(kept) == 2 and kept[0].startswith("diff --cc e.py") and kept[1].startswith("diff --git a/d.py "), kept
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        one = len(":(literal)d.py".encode())
        for limit in (None, 1, one - 1, one, one + 1, 2 * one, 2 * one + 1, 3 * one):
            with (batch_bytes(limit) if limit else contextlib.nullcontext()):
                d = conflict_packet_diff(pj, folder)
            where = "limit %r" % (limit,)
            got = sections_of(d)
            for section in kept:
                assert got.count(section) == 1, "%s: the section once, with all its source content:\n%r\n--- in ---\n%r" % (where, section, d)
            assert sorted(got) == sorted(kept), "%s: the kept sections and nothing else: %r" % (where, got)
            assert d.count("diff --cc e.py") == 1 and d.count("diff --git a/d.py b/d.py") == 1, "%s: %s" % (where, d)
            assert "side = main" in d and "side = other" in d and "+dmark = 2" in d, "%s: %s" % (where, d)
            if limit is None:
                assert d == want, "one batch keeps git's own order: one unbatched call's text:\n%s\n---\n%s" % (d, want)


@contextlib.contextmanager
def counted_subprocess_diffs():
    """subprocess.run wrapped: every `git diff` call that asks for content (no listing flag) recorded as (argv, the length
    of its decoded stdout); the real call made."""
    real = subprocess.run
    seen = []
    listing = {"--name-only", "--name-status", "--stat", "--numstat", "--raw", "--summary", "--shortstat"}
    def wrapped(argv, *a, **kw):
        done = real(argv, *a, **kw)
        args = list(argv) if isinstance(argv, (list, tuple)) else []
        if args and os.path.basename(str(args[0])) in ("git", "git.exe") and "diff" in args and not listing & set(args):
            if args.index("diff") < (args.index("--") if "--" in args else len(args)):
                out = done.stdout
                text = out.decode("utf-8", "replace") if isinstance(out, bytes) else (out or "")
                seen.append((args, len(text)))
        return done
    subprocess.run = wrapped
    try:
        yield seen
    finally:
        subprocess.run = real


def many_large_changes(pj, count, size, folder="src", ext=".py"):
    """`count` committed files, each then rewritten in the work tree with `size` characters of new lines. No review."""
    names = ["%s/f%03d%s" % (folder, i, ext) for i in range(count)]
    for n in names:
        write(os.path.join(pj.dir, n), "old = %r\n" % n)
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "many files")
    line = "y" * 59 + "\n"
    for n in names:
        write(os.path.join(pj.dir, n), "new = %r\n" % n + line * (size // len(line)))
    return names


def test_Q_bounded_eyes_request_invokes_no_git_diff_batch_after_the_one_whose_sections_pass_the_cut():
    with Project() as pj:
        names = many_large_changes(pj, 60, 6000)
        listed = git(pj.dir, "diff", "--no-renames", "--name-only").splitlines()
        assert listed == names, listed
        want = unbatched(pj.dir, [], listed)
        assert len(want) > 3 * 80000, "the change set's diff is far past the cut: %d" % len(want)
        limit = 2 * len((":(literal)" + names[0]).encode()) + 1   # two paths a batch: thirty batches
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        assert callable(getattr(dwitbuk, "git_patch", None)), "dwitbuk.git_patch(target, *args) is the patch seam"
        with batch_bytes(limit), counted_subprocess_diffs() as seen, recorded_git() as calls:
            code, out = run_all("eyes", "request", "--out", folder, "--target", pj.dir)
        assert code == 0, out
        assert seen, "git diff content calls were made through subprocess"
        sizes = [n for _, n in seen]
        assert len(seen) < len(names), "fewer git diff calls than changed paths: %d calls" % len(seen)
        assert sum(sizes[:-1]) < 80000 <= sum(sizes), \
            "the last git diff batch invoked is the one whose sections pass the 80000-character cut: %r" % sizes
        patched = [c for c in calls if c and c[0] == "diff" and "--name-only" not in c and "--name-status" not in c]
        assert len(patched) == len(seen), "the content calls go through git_patch: %d vs %d" % (len(patched), len(seen))
        packet = dwitbuk.load(os.path.join(folder, "eyes-request.json"))
        d = packet["diff"]
        assert packet.get("diff_truncated") is True, packet.get("diff_truncated")
        assert d.startswith("diff --git a/%s b/%s\n" % (listed[0], listed[0])), d[:200]
        assert 0 < len(d) <= 80000 and len(d) > 80000 - 2 * 6100, "cut at the limit: %d" % len(d)
        assert want.startswith(d), "the cut text is the start of git's text, nothing else in it"
        headers = re.findall(r"^diff --git a/(.*) b/", d, re.M)
        assert len(headers) == len(set(headers)), "no section repeats: %r" % headers
        assert headers == listed[:len(headers)], headers


def test_Q_bounded_excluded_diff_invokes_no_git_diff_batch_after_the_one_whose_sections_pass_the_cut():
    with Project() as pj:
        names = many_large_changes(pj, 40, 6000, "notes", ".json")
        since = git(pj.dir, "rev-parse", "HEAD")
        want = unbatched(pj.dir, [since], names)
        assert len(want) > 3 * 40000, len(want)
        limit = 2 * len((":(literal)" + names[0]).encode()) + 1
        req = {"artifact-type": "chongdae/request@1", "stage": "verify", "target": pj.dir, "task": "T", "brief": "b", "contract": {}, "checks": [], "tests": [],
               "touched": [], "since": {".": since}, "excluded": {"record-paths": list(names)}}
        with batch_bytes(limit), counted_subprocess_diffs() as seen:
            env = dwitbuk.verify_packet(req)
        assert env["excluded"] == list(names) and "excluded_diff" not in env, sorted(env)   # 11-09, D2
        assert not [a for a, n in seen if any("notes/" in x for x in a)], "verify_packet runs no git diff for the excluded paths: %r" % [a for a, n in seen]
        with batch_bytes(limit), counted_subprocess_diffs() as seen:
            ed = dwitbuk.path_diff(pj.dir, list(names), ("HEAD",), cut=40000)   # the late-eyes request's diff of them, bounded as before
        assert ed.startswith("diff --git a/%s b/%s\n" % (names[0], names[0])), ed[:200]
        assert 0 < len(ed) <= 40000 + 1, "cut at 40000 (path_diff keeps one character past it so a caller can say it was cut): %d" % len(ed)
        assert want.startswith(ed), "the cut text is the start of git's text"
        headers = re.findall(r"^diff --git a/(.*) b/", ed, re.M)
        assert len(headers) == len(set(headers)), headers
        seen = [(a, n) for a, n in seen if any("notes/" in x for x in a)]   # the record batches, not the touched diff
        sizes = [n for _, n in seen]
        assert seen and len(seen) < len(names), "fewer git diff calls than records: %d calls" % len(seen)
        assert sum(sizes[:-1]) < 40000 <= sum(sizes), "no batch after the one passing the 40000-character cut: %r" % sizes


CR_FILE = b"one\rtwo\r\nthree\n\xff four\r"


def test_Q_bounded_git_keeps_universal_newlines_and_git_patch_returns_gits_bytes_untranslated():
    assert callable(getattr(dwitbuk, "git_patch", None)), "dwitbuk.git_patch(target, *args) is the patch seam"
    with Project() as pj:
        with open(os.path.join(pj.dir, "cr.txt"), "wb") as fh:
            fh.write(CR_FILE)
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "a CR file")
        raw = subprocess.run(["git", "show", "HEAD:cr.txt"], cwd=pj.dir, capture_output=True).stdout
        assert raw == CR_FILE, raw
        decoded = raw.decode("utf-8", "replace")
        universal = decoded.replace("\r\n", "\n").replace("\r", "\n")
        assert dwitbuk.git(pj.dir, "show", "HEAD:cr.txt") == universal, "the generic helper: text, universal newlines"
        assert dwitbuk.git_patch(pj.dir, "show", "HEAD:cr.txt") == decoded, "the patch helper: git's bytes, no translation"
        assert dwitbuk.git_patch(pj.dir, "show", "HEAD:nothing-here") is None, "None on a non-zero exit"
        assert dwitbuk.git(pj.dir, "show", "HEAD:nothing-here") is None
        with open(os.path.join(pj.dir, "cr.txt"), "wb") as fh:
            fh.write(CR_FILE + b"five\r")
        patch = dwitbuk.git_patch(pj.dir, "diff", *PLAIN_DIFF, "--", "cr.txt")
        assert patch == subprocess.run(["git", "diff", *PLAIN_DIFF, "--", "cr.txt"], cwd=pj.dir, capture_output=True).stdout.decode("utf-8", "replace")
        assert "\rtwo\r\n" in patch and "five\r" in patch, repr(patch)
        assert "\r" not in dwitbuk.git(pj.dir, "diff", *PLAIN_DIFF, "--", "cr.txt"), "the generic helper still translates"


# ----------------------------------------------------------------------------------------------------------------------
# The installed payload is plugin/: what a host copies at install (the catalogs' `source`). These read it as a host does —
# that directory alone — and keep the source checkout (these tests, this project's hunsu environment, its run and review
# records) out of it.

PAYLOAD_REQUIRED = ("dwitbuk.py", "eyes_worker.py", "hostcall.py", "pluginroot.py", "plugin.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
                    "README.md", "LICENSE", "skills/review/SKILL.md", "commands/review.md", "commands/dispose.md", "commands/follow.md",
                    "commands/eyes.md", "hooks/hooks.json", "hooks/codex.json", "hooks/session_start.py", "hooks/stop_eyes.py")
PAYLOAD_SHAPE = re.compile(r"^(?:(?:dwitbuk|eyes_worker|hostcall|pluginroot)\.py|plugin\.json|README\.md|LICENSE|\.(?:claude|codex)-plugin/plugin\.json"
                           r"|skills/[\w.-]+/SKILL\.md|commands/[\w.-]+\.md|hooks/[\w.-]+\.(?:json|py))$")
PLUGIN_ROOT_VAR = re.compile(r"\$\{(?:CLAUDE_PLUGIN_ROOT|PLUGIN_ROOT)\}/([^\"'\s`\\]+)")   # up to a quote, space or JSON's escaping backslash


def in_git():
    return subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=HERE, capture_output=True).returncode == 0


def payload_files():
    """What the payload ships: the files under plugin/ git would commit (tracked, or new and not ignored) — a host installs
    the published tree, not this machine's bytecode; outside git, the directory minus bytecode."""
    done = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "plugin"], cwd=HERE, capture_output=True)
    if done.returncode == 0 and done.stdout:
        listed = {p[len("plugin/"):] for p in done.stdout.decode("utf-8").split("\0") if p.startswith("plugin/")}
        return sorted(p for p in listed if os.path.lexists(os.path.join(PLUGIN, *p.split("/"))))   # deleted in the tree: not shipped
    out = []
    for dirpath, dirs, files in os.walk(PLUGIN):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        out += [os.path.relpath(os.path.join(dirpath, f), PLUGIN).replace(os.sep, "/") for f in files if not f.endswith((".pyc", ".pyo"))]
    return sorted(out)


def copy_payload(dest):
    """The payload alone, as a host's cache holds it: plugin/'s shipped files, nothing above it."""
    for rel in payload_files():
        to = os.path.join(dest, *rel.split("/"))
        os.makedirs(os.path.dirname(to), exist_ok=True)
        shutil.copy2(os.path.join(PLUGIN, *rel.split("/")), to)
    return dest


def tree_state(root):
    state = {}
    for dirpath, _, files in os.walk(root):
        for f in files:
            with open(os.path.join(dirpath, f), "rb") as fh:
                state[os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/")] = fh.read()
    return state


def md_anchors(path):
    """The anchors a Markdown file's headings make (GitHub's rule: lower case, punctuation dropped, spaces to hyphens)."""
    out = set()
    for line in io.open(path, encoding="utf-8"):
        m = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
        if m:
            out.add(re.sub(r"[^\w\- ]", "", m.group(1).lower()).replace(" ", "-"))
    return out


def md_links(path, inside):
    """Every relative link in a Markdown file resolves to a file or directory under `inside`, and its anchor to a heading."""
    text = io.open(path, encoding="utf-8").read()
    for link in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", link):
            continue   # a URL
        page, _, anchor = link.partition("#")
        dest = os.path.normpath(os.path.join(os.path.dirname(path), page)) if page else path
        assert os.path.realpath(dest).startswith(os.path.realpath(inside) + os.sep) and os.path.exists(dest), \
            "%s links outside %s or to nothing: %s" % (path, inside, link)
        if anchor and dest.endswith(".md"):
            assert anchor in md_anchors(dest), "%s: no heading makes #%s in %s" % (path, anchor, dest)


def test_package_the_payload_is_the_runtime_alone_and_everything_it_names_is_inside_it():
    """Installation and development are separate: a host installs plugin/, so everything the plugin runs or names — engine,
    worker, hostcall, hooks, commands, the skill, its README and LICENSE — is in it, and nothing of the checkout is: no
    tests, no hunsu environment, no run, review or model records, no bytecode, no symlink."""
    files = payload_files()
    missing = [p for p in PAYLOAD_REQUIRED if p not in files]
    assert not missing, "the payload lacks %r" % missing
    stray = [p for p in files if not PAYLOAD_SHAPE.match(p)]
    assert not stray, "only the runtime ships; in the payload: %r" % stray
    for dirpath, dirs, names in os.walk(PLUGIN):
        for n in dirs + names:
            assert not os.path.islink(os.path.join(dirpath, n)), "no symlink in the payload: %s" % os.path.join(dirpath, n)
    if in_git():
        for rel in ("plugin/__pycache__/dwitbuk.cpython-312.pyc", "plugin/hooks/__pycache__/session_start.cpython-312.pyc"):
            assert subprocess.run(["git", "check-ignore", "-q", rel], cwd=HERE).returncode == 0, "bytecode is never shipped: %s" % rel
    with open(os.path.join(PLUGIN, "LICENSE"), "rb") as a, open(os.path.join(HERE, "LICENSE"), "rb") as b:
        assert a.read() == b.read(), "the payload's LICENSE is the repository's"
    manifests = {m: dwitbuk.load(os.path.join(PLUGIN, m)) for m in ("plugin.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json")}
    version = manifests["plugin.json"]["version"]
    for m, doc in manifests.items():
        assert doc["name"] == "dwitbuk" and doc["version"] == version and doc["engines"] == {"python": ">=3.11"}, (m, doc.get("version"), doc.get("engines"))
        for key in ("roles", "reads", "records"):
            assert doc[key] == manifests["plugin.json"][key], (m, key)
        for argv in list(doc["roles"].values()) + list(doc["reads"].values()):
            for a in argv:
                if a.startswith("{plugin:dwitbuk}/"):
                    assert os.path.isfile(os.path.join(PLUGIN, a[len("{plugin:dwitbuk}/"):])), (m, a)
    assert os.path.isfile(os.path.join(PLUGIN, manifests[".codex-plugin/plugin.json"]["skills"], "review", "SKILL.md"))
    assert os.path.isfile(os.path.join(PLUGIN, manifests["plugin.json"]["extensions"]["com.openai"]["hooks"]))
    named = []
    for rel in files:
        if rel.endswith((".json", ".md")):
            named += [(rel, p) for p in PLUGIN_ROOT_VAR.findall(io.open(os.path.join(PLUGIN, rel), encoding="utf-8").read())]
    assert {r for r, _ in named} >= {"hooks/hooks.json", "hooks/codex.json", "commands/review.md", "commands/dispose.md",
                                     "commands/follow.md", "commands/eyes.md"}, named
    for rel, p in named:
        assert os.path.isfile(os.path.join(PLUGIN, p)), "%s names %s, which is not in the payload" % (rel, p)
    for rel in (p for p in files if p.endswith(".md")):
        text = io.open(os.path.join(PLUGIN, rel), encoding="utf-8").read()
        assert not re.search(r"/(?:Users|home)/[^/\s]+/", text), "no local machine path in %s" % rel
        md_links(os.path.join(PLUGIN, rel), PLUGIN)   # an installed README links nowhere above the payload
    # the catalogs stay at the repository's root and name the payload
    claude = dwitbuk.load(os.path.join(HERE, ".claude-plugin", "marketplace.json"))
    entry = next(e for e in claude["plugins"] if e["name"] == "dwitbuk")
    assert entry["source"] == "./plugin" and entry["version"] == version == claude["metadata"]["version"], (entry, claude["metadata"])
    codex = dwitbuk.load(os.path.join(HERE, ".agents", "plugins", "marketplace.json"))
    entry = next(e for e in codex["plugins"] if e["name"] == "dwitbuk")
    assert entry["source"] == {"source": "local", "path": "./plugin"} and "version" not in entry, entry
    assert dwitbuk.catalog_source(HERE, "dwitbuk") == os.path.normpath(PLUGIN)
    # one source: nothing of the runtime is left beside the payload but the two entry points, and the developer docs link true
    for gone in ("hostcall.py", "plugin.json", "commands", "skills", "hooks", ".codex-plugin", os.path.join(".claude-plugin", "plugin.json")):
        assert not os.path.lexists(os.path.join(HERE, gone)), "%s lives in plugin/ only" % gone
    for doc in ("README.md", "AGENTS.md"):
        md_links(os.path.join(HERE, doc), HERE)


FAKE_CLAUDE = r'''import json, os, sys
argv = sys.argv[1:]
prompt = sys.stdin.read()
schema = json.loads(argv[argv.index("--json-schema") + 1])
with open(os.environ["FAKE_CLAUDE_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"argv": argv, "AGENT_WORKER": os.environ.get("AGENT_WORKER"), "AGENT_HOST": os.environ.get("AGENT_HOST"),
                         "packet": "dwitbuk/eyes-request@1" in prompt}) + "\n")
with open(os.environ["FAKE_CLAUDE_ANSWER"], encoding="utf-8") as fh:
    answer = json.load(fh)
answer["request"] = schema["properties"]["request"]["enum"][0]   # as a model gets it: the request's fingerprint, in the schema
print(json.dumps({"type": "system", "subtype": "init", "model": "fake-eyes-1", "session_id": "fake-1"}))
print(json.dumps({"type": "result", "num_turns": 1, "total_cost_usd": 0, "session_id": "fake-1", "structured_output": answer}))
'''


def test_package_a_copy_of_the_payload_alone_runs_review_dispose_eyes_and_hooks_outside_the_checkout():
    """A host installs plugin/ copied on its own. The copy, in a fresh directory outside this checkout, with no PYTHONPATH or
    user site and a project of its own as the working directory, runs the actual CLI on a small project: a review whose
    reporter typed one non-claim an observation (kept one through grouping), follow, a disposal with its quote and the
    finding's own text, the review lock refusing a competing mutation, late eyes through the manifest's own `eyes` argv and
    hostcall to a host (a fake `claude` answering as a model would, given the request's fingerprint in the schema), consume
    keeping only quoted findings, dispositions carried by the next review, the session-start line naming the copy's engine,
    and the stop hook placing the eyes from the copy. The payload itself is never written."""
    if os.name == "nt":
        raise Skip("the fake host is a POSIX shell script; the payload's shape is checked on every host")
    base = tempfile.mkdtemp(prefix="dwitbuk-payload-")
    try:
        assert not os.path.realpath(base).startswith(os.path.realpath(HERE) + os.sep)
        copy = copy_payload(os.path.join(base, "cache", "dwitbuk", "dwitbuk", "installed"))
        before = tree_state(copy)
        assert sorted(before) == payload_files() and not [p for p in before if "__pycache__" in p or p.endswith(".pyc")], sorted(before)
        home, proj, bindir = (os.path.join(base, d) for d in ("home", "project", "bin"))
        for d in (home, proj, bindir):
            os.makedirs(d)
        log, answer = os.path.join(base, "claude.log"), os.path.join(base, "answer.json")
        write(os.path.join(base, "fake_claude.py"), FAKE_CLAUDE)
        write(os.path.join(bindir, "claude"), '#!/bin/sh\nexec "%s" -B -s "%s" "$@"\n' % (sys.executable, os.path.join(base, "fake_claude.py")))
        os.chmod(os.path.join(bindir, "claude"), 0o755)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("PYTHON") and k not in ("AGENT_WORKER", "AGENT_HOST", "HUNSU_SURVEY", "CLAUDE_CONFIG_DIR")}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", HUNSU_CLAUDE_DIR=home, FAKE_CLAUDE_LOG=log, FAKE_CLAUDE_ANSWER=answer,
                   PATH=bindir + os.pathsep + os.environ.get("PATH", ""))

        def py(*argv, stdin=None, **more):
            done = subprocess.run([sys.executable, "-B", "-s", *argv], cwd=proj, input=stdin, capture_output=True, text=True,
                                  encoding="utf-8", env=dict(env, **more))
            return done.returncode, done.stdout, done.stderr
        engine = os.path.join(copy, "dwitbuk.py")
        cli = lambda *a: py(engine, *a, "--target", proj)
        calls = lambda: [json.loads(l) for l in open(log, encoding="utf-8")] if os.path.exists(log) else []
        latest = lambda: dwitbuk.load(os.path.join(proj, "reviews", sorted(os.listdir(os.path.join(proj, "reviews")))[-1]))

        # the copy's modules are the copy's, one engine instance, and nothing of the checkout is on the path it runs with
        probe = ("import json, sys; sys.path.insert(0, sys.argv[1]); import eyes_worker, dwitbuk, hostcall; "
                 "print(json.dumps({'files': [m.__file__ for m in (eyes_worker, dwitbuk, hostcall)], 'path': sys.path, "
                 "'one': eyes_worker.check_eyes.__globals__ is dwitbuk.__dict__}))")
        code, out, err = py("-c", probe, copy)
        seen = json.loads(out)
        assert all(os.path.realpath(f).startswith(os.path.realpath(copy) + os.sep) for f in seen["files"]), seen["files"]
        assert not [p for p in seen["path"] if p and os.path.realpath(p).startswith(os.path.realpath(HERE))], seen["path"]
        assert seen["one"], "one engine instance"

        git(proj, "init", "-q", "-b", "main")
        write(os.path.join(proj, "a.py"), "x = 1\n")
        git(proj, "add", "-A"); git(proj, "commit", "-q", "-m", "base")
        reporter = os.path.join(base, "reporter.py")
        doc = {"artifact-type": "dwitbuk/findings@1", "source": "chongdae", "findings": [
            {"kind": "non-claim", "where": "run-a", "text": "T1: (provider) a limit its role sets", "layer": "observation"},
            {"kind": "non-claim", "where": "run-a", "text": "T2: (provider) a limit its role sets", "layer": "observation"},
            {"kind": "non-claim", "where": "run-b", "text": "T3: (provider) the clause was left unread"},
            {"kind": "left-open", "where": "run-1/T", "text": "left open when its run closed"}]}
        write(reporter, "import sys\nprint(%r)\n" % json.dumps(doc))
        write(os.path.join(proj, "hunsu.lock.json"), {"reporters": {"chongdae": [sys.executable, reporter, "--since", "{since}"]}})

        code, out, err = cli("review")
        assert code == 0 and "2 objection(s) (left-open 1, non-claim 1), 1 observation(s)" in out, (code, out, err)
        r = latest()
        assert {f["where"]: dwitbuk.layer(f) for f in r["findings"]} == {"run-a": "observation", "run-b": "objection", "run-1/T": "objection"}, r["findings"]
        assert next(f for f in r["findings"] if f["where"] == "run-a").get("layer") == "observation", "the reporter's layer, written in the review"
        at = {f["where"]: i for i, f in enumerate(r["findings"])}
        code, out, err = cli("follow")
        assert code == 1 and "undisposed findings: 2" in out and "left unread" in out and "a limit its role sets" not in out, out
        code, out, err = cli("dispose", "%s/%d" % (r["id"], at["run-a"]), "--as", "dismissed", "--why", "x", "--by", "tester")
        assert code != 0 and "is an observation" in err, (code, out, err)
        code, out, err = cli("dispose", "%s/%d" % (r["id"], at["run-1/T"]), "--as", "accepted", "--why", "the task was dropped on purpose",
                             "--by", "tester", "--quote", "x = 1")
        assert code == 0, (out, err)
        held = latest()["findings"][at["run-1/T"]]["disposition"]
        assert held["by"] == "tester" and held["why"] == "the task was dropped on purpose" and held["quote"] == "x = 1" \
            and held["finding_text"] == r["findings"][at["run-1/T"]]["text"], held

        # serialized: while another process holds the review lock, a mutation from the copy is refused and writes nothing
        holder = subprocess.Popen([sys.executable, "-B", "-s", "-c", "import sys; sys.path.insert(0, sys.argv[1]); import dwitbuk\n"
                                   "with dwitbuk.ReviewLock(sys.argv[2]):\n    print('held', flush=True); sys.stdin.readline()", copy, proj],
                                  cwd=proj, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        try:
            assert holder.stdout.readline().strip() == "held"
            code, out, err = cli("dispose", "%s/%d" % (r["id"], at["run-b"]), "--as", "accepted", "--why", "y", "--by", "tester")
            assert code == 4 and "retry" in err, (code, out, err)
        finally:
            holder.communicate("\n", timeout=10)
        assert "disposition" not in latest()["findings"][at["run-b"]], "the refused mutation wrote nothing"

        # late eyes: request, the manifest's own `eyes` argv through hostcall to the (fake) host, consume
        write(os.path.join(proj, "a.py"), "x = 2\n")
        packets = os.path.join(proj, ".dwitbuk", "eyes")
        code, out, err = cli("eyes", "request", "--out", packets)
        assert code == 0 and os.path.isfile(os.path.join(packets, "eyes-request.json")), (out, err)
        write(answer, {"findings": [{"kind": "anomaly", "where": "a.py", "record_quote": "", "tree_quote": "x = 2", "why": "a constant changed outside a run"},
                                    {"kind": "contradiction", "where": "a.py", "record_quote": "", "tree_quote": "x = 2", "why": "quotes no record"}]})
        role = dwitbuk.load(os.path.join(copy, "plugin.json"))["roles"]["eyes"]
        fill = {"{plugin:dwitbuk}": copy, "{request}": os.path.join(packets, "eyes-request.json"),
                "{response}": os.path.join(packets, "eyes-response.json"), "{host}": "claude"}
        argv = list(role)
        for key, value in fill.items():
            argv = [a.replace(key, value) for a in argv]
        assert argv[0] == "python3" and argv[1] == os.path.join(copy, "eyes_worker.py"), argv
        code, out, err = py(*argv[1:])
        assert code == 0, (out, err)
        assert len(calls()) == 1, calls()
        call = calls()[0]
        assert call["AGENT_WORKER"] == "1" and call["AGENT_HOST"] == "claude-code" and call["packet"], call
        assert call["argv"][call["argv"].index("--tools") + 1] == "Read,Grep,Glob" and "--no-session-persistence" in call["argv"], call["argv"]
        resp = dwitbuk.load(os.path.join(packets, "eyes-response.json"))
        assert resp["worker"]["model"] == "fake-eyes-1" and os.path.isfile(os.path.join(packets, resp["worker"]["transcript"])), resp["worker"]
        code, out, err = py(argv[1], "--prompt-only", "--request", fill["{request}"], "--response", os.path.join(base, "unused.json"))
        assert code == 0 and resp["request"] in out and len(calls()) == 1, "prompt-only prints the bound schema and calls no host"
        code, out, err = cli("eyes", "consume", "--dir", packets)
        assert code == 0 and "1 finding(s) added" in out and "1 rejected" in out, (out, err)
        eyes = [f for f in latest()["findings"] if f["kind"] in ("anomaly", "contradiction")]
        assert len(eyes) == 1 and eyes[0]["kind"] == "anomaly" and "tree: “x = 2”" in eyes[0]["text"], eyes

        # the next review: the disposal answers its charge, the observation is on record once, the rest is still open
        import time; time.sleep(1.1)
        git(proj, "add", "a.py"); git(proj, "commit", "-q", "-m", "x = 2")
        code, out, err = cli("review")
        assert code == 0, (out, err)
        r2 = latest()
        assert r2["id"] != r["id"] and any(f["kind"] == "unchanged" and r["id"] in str(f.get("seen-in")) for f in r2["findings"]), r2["findings"]
        code, out, err = cli("follow")
        assert code == 1 and "undisposed findings: 2" in out and "left unread" in out and "a constant changed outside a run" in out \
            and "left open when its run closed" not in out, out

        # the session-start line names the copy's engine, and that command works as written
        hook = os.path.join(copy, "hooks", "session_start.py")
        code, out, err = py(hook, stdin=json.dumps({"cwd": proj}))
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert code == 0 and ctx.startswith("dwitbuk: 2 undisposed objection(s) in %s" % r2["id"]), ctx
        named = re.search(r'python3 "([^"]+)" follow', ctx).group(1)
        assert os.path.realpath(named) == os.path.realpath(engine), named
        code, out, err = py(named, "follow", "--target", proj)
        assert code == 1 and "undisposed findings: 2" in out, out
        code, out, err = py(hook, stdin=json.dumps({"cwd": home}), HUNSU_SURVEY="1")
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert ctx == session_start.STANDING and copy not in ctx, ctx

        # the stop hook: off without the switch; on, it places the eyes from the copy and refuses the stop with what they quote
        stop = os.path.join(copy, "hooks", "stop_eyes.py")
        write(os.path.join(proj, "a.py"), "x = 3\n")
        code, out, err = py(stop, stdin=json.dumps({"cwd": proj}))
        assert code == 0 and not os.path.exists(os.path.join(proj, ".dwitbuk", "stop.log")) and len(calls()) == 1, (code, err)
        write(os.path.join(proj, "hunsu.json"), {"settings": {"dwitbuk": {"stop-eyes": True}}})
        write(answer, {"findings": [{"kind": "anomaly", "where": "a.py", "record_quote": "", "tree_quote": "x = 3", "why": "changed again at the stop"}]})
        code, out, err = py(stop, stdin=json.dumps({"cwd": proj}))
        assert code == 2 and "changed again at the stop" in err and "x = 3" in err, (code, out, err)
        assert len(calls()) == 2 and calls()[-1]["AGENT_WORKER"] == "1", calls()
        assert any(f["kind"] == "anomaly" and "changed again at the stop" in f["text"] for f in latest()["findings"]), "added to the latest review"

        assert tree_state(copy) == before, "the payload is never written: no bytecode, scratch or record lands in it"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_package_the_checkouts_root_entry_points_run_the_payload_with_one_module_instance():
    """`python3 <checkout>/dwitbuk.py` and `<checkout>/eyes_worker.py` were the plugin's own paths before the payload moved to
    plugin/, and resolvers released before this layout (chongdae 2.0.0's `{plugin:NAME}`) take a `hunsu.local.json` link to
    a checkout as the plugin's root. They stay as entry points only: no engine code, the payload's file run as `__main__`,
    and when imported the payload's module in their place — never a second instance beside it."""
    import ast
    for name in ("dwitbuk.py", "eyes_worker.py"):
        tree = ast.parse(io.open(os.path.join(HERE, name), encoding="utf-8").read())
        assert not [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))], name
    assert os.path.realpath(dwitbuk.__file__) == os.path.realpath(os.path.join(PLUGIN, "dwitbuk.py")), dwitbuk.__file__
    assert w.check_eyes.__globals__ is dwitbuk.__dict__ and session_start.dwitbuk is dwitbuk, "this suite holds one engine instance"

    def py(*argv, cwd):
        return subprocess.run([sys.executable, "-B", *argv], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    with Project() as pj:
        pj.reporter([{"kind": "left-open", "where": "run-1/T", "text": "left open"}])
        assert run("review", "--target", pj.dir)[0] == 0
        for name, args in (("dwitbuk.py", ["follow", "--target", pj.dir]), ("dwitbuk.py", ["--help"]), ("eyes_worker.py", ["--help"])):
            via_root, direct = py(os.path.join(HERE, name), *args, cwd=pj.dir), py(os.path.join(PLUGIN, name), *args, cwd=pj.dir)
            assert (via_root.returncode, via_root.stdout, via_root.stderr) == (direct.returncode, direct.stdout, direct.stderr), (name, args, via_root, direct)
            if args[0] == "follow":
                assert via_root.returncode == 1 and "left open" in via_root.stdout, "the exit code and the output pass through"
    probe = ("import json, sys\n"
             "for n in sys.argv[1].split(','): __import__(n)\n"
             "import dwitbuk, eyes_worker\n"
             "engines = [m for m in list(sys.modules.values()) if (getattr(m, '__file__', None) or '').endswith(('dwitbuk.py', 'eyes_worker.py'))]\n"
             "print(json.dumps({'files': sorted(m.__file__ for m in engines), "
             "'one': eyes_worker.check_eyes.__globals__ is dwitbuk.__dict__ and sys.modules['dwitbuk'] is dwitbuk}))")
    want = sorted(os.path.realpath(os.path.join(PLUGIN, n)) for n in ("dwitbuk.py", "eyes_worker.py"))
    for order in ("dwitbuk,eyes_worker", "eyes_worker,dwitbuk"):
        done = py("-c", probe, order, cwd=HERE)   # the checkout's root first on sys.path: the entry points are what `import` finds
        seen = json.loads(done.stdout or "{}")
        assert seen.get("one") and sorted(os.path.realpath(f) for f in seen["files"]) == want, (order, seen, done.stderr)


def test_a_link_or_directory_marketplace_at_a_source_checkout_resolves_to_its_payload():
    """A `hunsu.local.json` link names a marketplace directory (hunsu's own reading of it). With the payload in plugin/, a link
    to a checkout's root would have run `<checkout>/<engine>.py`; the catalog's `source` says where the payload is — the
    Claude catalog's string, else the Codex catalog's local path — when a plugin manifest is there. Without one the earlier
    rule stands (`<link>/<name>`, else the link), so flat checkouts and folders of flat plugins resolve as before. A
    directory marketplace is read the same way, the checkout itself included (the host runs it in place from the catalog's
    source; its install record is a copy nothing runs); with no catalog or `<path>/<name>`, the install record, as before."""
    base = tempfile.mkdtemp(prefix="dwitbuk-links-")
    old = os.environ.get("HUNSU_CLAUDE_DIR")
    try:
        def manifest(d, kind=".claude-plugin"):
            write(os.path.join(d, kind, "plugin.json") if kind else os.path.join(d, "plugin.json"), {"name": "mangsang", "version": "9"})
        co = os.path.join(base, "co"); manifest(os.path.join(co, "plugin"))
        write(os.path.join(co, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "mangsang", "source": "./plugin"}]})
        cx = os.path.join(base, "cx"); manifest(os.path.join(cx, "plugin"), ".codex-plugin")
        write(os.path.join(cx, ".agents", "plugins", "marketplace.json"), {"plugins": [{"name": "mangsang", "source": {"source": "local", "path": "./plugin"}}]})
        folder = os.path.join(base, "folder"); manifest(os.path.join(folder, "mangsang", "plugin"))
        write(os.path.join(folder, "mangsang", ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "mangsang", "source": "./plugin"}]})
        flat = os.path.join(base, "flat"); manifest(flat, None)
        write(os.path.join(flat, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "mangsang", "source": "./"}]})
        old_folder = os.path.join(base, "old"); manifest(os.path.join(old_folder, "mangsang"), None)
        empty = os.path.join(base, "empty"); os.makedirs(os.path.join(empty, "plugin"))   # the catalog names a directory that holds no manifest
        write(os.path.join(empty, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "mangsang", "source": "./plugin"}]})
        broken = os.path.join(base, "broken"); write(os.path.join(broken, ".claude-plugin", "marketplace.json"), "{not json")
        want = {co: os.path.join(co, "plugin"), cx: os.path.join(cx, "plugin"), folder: os.path.join(folder, "mangsang", "plugin"),
                flat: flat, old_folder: os.path.join(old_folder, "mangsang"), empty: empty, broken: broken}
        with Project() as pj, environ(AGENT_HOST="claude-code", HUNSU_CODEX_DIR=os.path.join(base, "codex")):
            for link, root in want.items():
                write(os.path.join(pj.dir, "hunsu.local.json"), {"links": {"mangsang": link}})
                got = dwitbuk.plugin_root(pj.dir, "mangsang")
                assert os.path.normpath(got) == os.path.normpath(root), (link, got, root)
            write(os.path.join(pj.dir, "hunsu.local.json"), {"links": {"dwitbuk": HERE}})   # this checkout: the lock's argv reaches the payload
            argv = dwitbuk.resolve_argv(pj.dir, ["python3", "{plugin:dwitbuk}/dwitbuk.py", "follow"], None)
            assert os.path.normpath(argv[1]) == os.path.join(PLUGIN, "dwitbuk.py"), argv
            home = os.path.join(base, "home")
            os.environ["HUNSU_CLAUDE_DIR"] = home
            write(os.path.join(pj.dir, "hunsu.local.json"), {})
            write(os.path.join(pj.dir, "hunsu.json"), {"plugins": {"mangsang": {"marketplace": "dev"}}})
            # a directory marketplace is loaded in place by the host from the source its catalog names — also when the
            # marketplace is the checkout itself (`hunsu dev --market` on a checkout: no `<path>/<name>` beside its catalog)
            for market, root in ((co, os.path.join(co, "plugin")), (cx, os.path.join(cx, "plugin")), (flat, flat),
                                 (folder, os.path.join(folder, "mangsang", "plugin")), (old_folder, os.path.join(old_folder, "mangsang"))):
                write(os.path.join(home, "plugins", "known_marketplaces.json"), {"dev": {"source": {"source": "directory", "path": market}}})
                assert os.path.normpath(dwitbuk.plugin_root(pj.dir, "mangsang")) == root, market
            installed = made(os.path.join(home, "cache", "mangsang", "9"))   # an installPath that exists
            write(os.path.join(home, "plugins", "installed_plugins.json"), {"plugins": {"mangsang@dev": [
                {"scope": "project", "projectPath": pj.dir, "installPath": installed}]}})
            for market in (empty, broken, ""):   # no catalog names a manifest and no `<path>/<name>`: the install record, as before
                write(os.path.join(home, "plugins", "known_marketplaces.json"), {"dev": {"source": {"source": "directory", "path": market}}})
                assert same(dwitbuk.plugin_root(pj.dir, "mangsang"), installed), market
            write(os.path.join(home, "plugins", "known_marketplaces.json"), {"dev": {"source": {"source": "directory", "path": HERE}}})
            write(os.path.join(pj.dir, "hunsu.json"), {"plugins": {"dwitbuk": {"marketplace": "dev"}}})
            assert os.path.normpath(dwitbuk.plugin_root(pj.dir, "dwitbuk")) == PLUGIN, "this checkout as a directory marketplace: its payload"
    finally:
        if old is None:
            os.environ.pop("HUNSU_CLAUDE_DIR", None)
        else:
            os.environ["HUNSU_CLAUDE_DIR"] = old
        shutil.rmtree(base, ignore_errors=True)



def test_a_catalog_source_is_a_path_inside_the_catalog_and_its_manifest_names_the_plugin():
    """A fresh review (root, 2026-11-05, temp fixtures with a matching probe manifest): a catalog at /catalog whose source was
    `../outside` resolved to the sibling /outside, and `https://…` to a local /catalog/https:/… directory. A catalog's source
    is its own payload: a relative path that stays inside the catalog's directory by realpath (no URI, no absolute path, no
    `..` or symlink out), whose manifests name no other plugin. Anything else names nothing, and the earlier rules stand."""
    base = tempfile.mkdtemp(prefix="dwitbuk-contain-")
    old = os.environ.get("HUNSU_CLAUDE_DIR")
    try:
        cat = os.path.join(base, "catalog")
        def manifest(d, name="probe", kind=".claude-plugin"):
            write(os.path.join(d, kind, "plugin.json") if kind else os.path.join(d, "plugin.json"), {"name": name} if name else {"version": "1"})
        def claude(src):
            write(os.path.join(cat, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "probe", "source": src}]})
        def codex(path):
            shutil.rmtree(os.path.join(cat, ".claude-plugin"), ignore_errors=True)
            write(os.path.join(cat, ".agents", "plugins", "marketplace.json"), {"plugins": [{"name": "probe", "source": {"source": "local", "path": path}}]})
        outside = os.path.join(base, "outside")
        manifest(outside, kind=None)
        manifest(os.path.join(cat, "https:", "example.invalid", "probe"), kind=None)   # what `https://…` normalized to
        manifest(os.path.join(cat, "file:", "x"), kind=None)
        manifest(os.path.join(cat, "plugin"))
        manifest(os.path.join(cat, "plugins", "deep", "probe"))
        manifest(os.path.join(cat, "other"), name="someone-else")
        manifest(os.path.join(cat, "nameless"), name=None)
        write(os.path.join(cat, "broken", "plugin.json"), "{not json")
        for odd, value in (("listed", ["probe"]), ("mapped", {}), ("numbered", 5), ("bare", "probe")):   # a name that is not a name
            write(os.path.join(cat, odd, "plugin.json"), {"name": value} if odd != "bare" else ["probe"])
        write(os.path.join(cat, "nulled", "plugin.json"), {"name": None})   # an explicit null: no name, like none at all
        links = os.name != "nt"
        if links:
            os.symlink(outside, os.path.join(cat, "escape"))                    # a symlink out of the catalog
            os.symlink(os.path.join(cat, "plugin"), os.path.join(cat, "alias"))  # one that stays inside
        rejected = ["../outside", "./plugin/../../outside", "https://example.invalid/probe", "file://x", outside,
                    "./other", "./broken", "./missing", "./listed", "./mapped", "./numbered", "./bare"] + (["escape", "./escape"] if links else [])
        kept = {"./plugin": "plugin", "plugin": "plugin", "./plugins/deep/probe": os.path.join("plugins", "deep", "probe"),
                "./nameless": "nameless", "./nulled": "nulled", "./plugin/../plugin": "plugin", **({"./alias": "alias"} if links else {})}
        for src in rejected:
            claude(src)
            assert dwitbuk.catalog_source(cat, "probe") is None, src
        for src, rel in kept.items():
            claude(src)
            assert dwitbuk.catalog_source(cat, "probe") == os.path.normpath(os.path.join(cat, rel)), src
        manifest(cat, kind=None)   # a flat catalog: the payload is the directory itself
        claude("./")
        assert dwitbuk.catalog_source(cat, "probe") == os.path.normpath(cat)
        os.unlink(os.path.join(cat, "plugin.json"))
        for path in ("https://example.invalid/probe", "file://x", outside, "../outside"):   # the Codex catalog's local object
            codex(path)
            assert dwitbuk.catalog_source(cat, "probe") is None, path
        codex("./plugin")
        assert dwitbuk.catalog_source(cat, "probe") == os.path.join(cat, "plugin")
        # through plugin_root: a rejected source falls back to the earlier rule — the link itself here, the install record for
        # a directory marketplace — never to the escaped directory, and never a crash (a list for a name raised TypeError)
        codex("./listed")
        with Project() as pj, environ(AGENT_HOST="claude-code", HUNSU_CODEX_DIR=os.path.join(base, "codex-home")):
            write(os.path.join(pj.dir, "hunsu.local.json"), {"links": {"probe": cat}})
            assert dwitbuk.plugin_root(pj.dir, "probe") == cat
        codex("../outside")
        with Project() as pj, environ(AGENT_HOST="claude-code", HUNSU_CODEX_DIR=os.path.join(base, "codex-home")):
            write(os.path.join(pj.dir, "hunsu.local.json"), {"links": {"probe": cat}})
            assert dwitbuk.plugin_root(pj.dir, "probe") == cat
            home = os.path.join(base, "home")
            os.environ["HUNSU_CLAUDE_DIR"] = home
            write(os.path.join(home, "plugins", "known_marketplaces.json"), {"dev": {"source": {"source": "directory", "path": cat}}})
            installed = made(os.path.join(home, "cache", "probe", "1"))   # an installPath that exists
            write(os.path.join(home, "plugins", "installed_plugins.json"), {"plugins": {"probe@dev": [
                {"scope": "project", "projectPath": pj.dir, "installPath": installed}]}})
            write(os.path.join(pj.dir, "hunsu.local.json"), {})
            write(os.path.join(pj.dir, "hunsu.json"), {"plugins": {"probe": {"marketplace": "dev"}}})
            assert same(dwitbuk.plugin_root(pj.dir, "probe"), installed)
    finally:
        if old is None:
            os.environ.pop("HUNSU_CLAUDE_DIR", None)
        else:
            os.environ["HUNSU_CLAUDE_DIR"] = old
        shutil.rmtree(base, ignore_errors=True)



# --- 11-06 D1: verify_packet keeps every touched path but chongdae's runs and the host's settings, and says what its diff does not hold

def verify_req(pj, touched, since=None, **kw):
    return {"artifact-type": "chongdae/request@1", "stage": "verify", "run": "run-1", "task": "T", "target": pj.dir, "brief": "b",
            "contract": {}, "checks": [], "tests": [], "touched": list(touched), **({"since": {".": since}} if since else {}), **kw}


def test_D1_verify_packet_keeps_touched_record_paths_with_their_diff_and_drops_only_chongdae_and_claude():
    """11-06: today's model work (mangsang/relations/…) reached the verifier with no name and no diff."""
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"alpha": [".alpha/", "alpha.json"], "mangsang": ["mangsang/", ".mangsang/"]}})
        write(os.path.join(pj.dir, "mangsang", "relations", "R-1.json"), '{"id": "R-1", "v": "one"}\n')
        write(os.path.join(pj.dir, "hunsu.json"), '{"plugins": "before"}\n')
        write(os.path.join(pj.dir, ".alpha", "x.json"), '{"alpha": "before"}\n')
        write(os.path.join(pj.dir, "src", "a.py"), "src_a = 'before'\n")
        write(os.path.join(pj.dir, ".chongdae", "run-1", "tasks", "T.json"), '{"task": "chongdae-before"}\n')
        write(os.path.join(pj.dir, ".claude", "settings.json"), '{"claude": "settings-before"}\n')
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base with records")
        since = git(pj.dir, "rev-parse", "HEAD")
        write(os.path.join(pj.dir, "mangsang", "relations", "R-1.json"), '{"id": "R-1", "v": "two"}\n')
        write(os.path.join(pj.dir, "mangsang", "relations", "R-2.json"), '{"id": "R-2", "v": "brand new relation"}\n')
        write(os.path.join(pj.dir, "hunsu.json"), '{"plugins": "after"}\n')
        write(os.path.join(pj.dir, ".alpha", "x.json"), '{"alpha": "after"}\n')
        write(os.path.join(pj.dir, "src", "a.py"), "src_a = 'after'\n")
        write(os.path.join(pj.dir, ".chongdae", "run-1", "tasks", "T.json"), '{"task": "chongdae-after"}\n')
        write(os.path.join(pj.dir, ".claude", "settings.json"), '{"claude": "settings-after"}\n')
        kept = ["mangsang/relations/R-1.json", "mangsang/relations/R-2.json", "hunsu.json", ".alpha/x.json", "src/a.py"]
        p = dwitbuk.verify_packet(verify_req(pj, kept + [".chongdae/run-1/tasks/T.json", ".claude/settings.json"], since))
        assert p["touched"] == kept, p["touched"]
        d = p["diff"]
        assert '-{"id": "R-1", "v": "one"}' in d and '+{"id": "R-1", "v": "two"}' in d and "b/mangsang/relations/R-1.json" in d, d
        assert "mangsang/relations/R-2.json (new file)" in d and "brand new relation" in d, d
        assert '-{"plugins": "before"}' in d and '+{"plugins": "after"}' in d, d
        assert '-{"alpha": "before"}' in d and '+{"alpha": "after"}' in d, d
        assert "-src_a = 'before'" in d and "+src_a = 'after'" in d, d
        for gone in ("chongdae-before", "chongdae-after", "settings-before", "settings-after", ".chongdae/", ".claude/"):
            assert gone not in d, (gone, d)
        assert "not_in_diff" not in p, p.get("not_in_diff")   # every file whole: no key
        # documents_or_records still counts them records (unchanged)
        assert dwitbuk.documents_or_records(["mangsang/relations/R-1.json", "hunsu.json", ".alpha/x.json"], pj.dir)


def test_D1_verify_packet_names_in_not_in_diff_what_its_diff_does_not_hold_whole():
    with Project() as pj:
        write(os.path.join(pj.dir, "a_small.py"), "small = 'before'\n")
        write(os.path.join(pj.dir, "b_huge.py"), "huge = 0\n")
        write(os.path.join(pj.dir, "c_after.py"), "after = 'before'\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base")
        since = git(pj.dir, "rev-parse", "HEAD")
        write(os.path.join(pj.dir, "a_small.py"), "small = 'after'\n")
        write(os.path.join(pj.dir, "b_huge.py"), "".join("huge_%05d = %d  # a long line of the huge change\n" % (i, i) for i in range(2500)))
        write(os.path.join(pj.dir, "c_after.py"), "after = 'after'\n")
        write(os.path.join(pj.dir, "d_big_new.txt"), "big new file line\n" * 3000)   # 54000 bytes, untracked: git has no diff
        assert os.path.getsize(os.path.join(pj.dir, "b_huge.py")) > 80000 and os.path.getsize(os.path.join(pj.dir, "d_big_new.txt")) >= 40000
        p = dwitbuk.verify_packet(verify_req(pj, ["a_small.py", "b_huge.py", "c_after.py", "d_big_new.txt"], since))
        assert p["touched"] == ["a_small.py", "b_huge.py", "c_after.py", "d_big_new.txt"], p["touched"]
        assert "+small = 'after'" in p["diff"], p["diff"][:400]
        assert "not_in_diff" in p, sorted(p)
        nid = p["not_in_diff"]
        assert isinstance(nid, list) and set(nid) == {"b_huge.py", "c_after.py", "d_big_new.txt"}, nid
        assert "a_small.py" not in nid, nid
        # a 40000-byte new file exactly is not added whole either
        write(os.path.join(pj.dir, "e_exact.txt"), "x" * 39999 + "\n")
        assert os.path.getsize(os.path.join(pj.dir, "e_exact.txt")) == 40000
        q = dwitbuk.verify_packet(verify_req(pj, ["a_small.py", "e_exact.txt"], since))
        assert q.get("not_in_diff") == ["e_exact.txt"], q.get("not_in_diff")
        # and a packet whose diff holds every file whole has no key at all
        r = dwitbuk.verify_packet(verify_req(pj, ["a_small.py", "c_after.py"], since))
        assert "not_in_diff" not in r and "+after = 'after'" in r["diff"], sorted(r)


# --- 11-06 D2: an accept that left a touched file neither whole in the diff nor opened says so

def unread_project(pj):
    write(os.path.join(pj.dir, "small.py"), "small = 1\n")
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base small")
    since = git(pj.dir, "rev-parse", "HEAD")
    write(os.path.join(pj.dir, "small.py"), "small = 2\n")
    write(os.path.join(pj.dir, "big.py"), "".join("big_%05d = %d\n" % (i, i) for i in range(4000)))
    assert os.path.getsize(os.path.join(pj.dir, "big.py")) >= 40000
    return verify_req(pj, ["small.py", "big.py"], since, run="run-1", task="big-task", brief="add big",
                      contract={"Q-big": "big.py defines four thousand constants"}, checks=[["python3", "t.py"]], tests=["t.py"],
                      built={"summary": "built", "verified": [], "non-claims": []})


UNREAD_BIG = "accepted with 1 touched file(s) left unread — neither whole in the packet's diff nor opened by the eyes: `big.py`"



def test_D2_unread_touched_names_the_not_in_diff_files_the_eyes_did_not_open():
    """11-06 D2, amended 11-09 (D1-3): unread_touched works over `must_open`, in its order; with no session on record every
    must_open path is unread; a command opens a file by D1-3's rule (a whole token, a part that is not git's view, an echo
    or a listing, and that ran)."""
    assert callable(getattr(w, "unread_touched", None)), "eyes_worker.unread_touched is missing"
    with Project() as pj:
        packet = dict(dwitbuk.verify_packet(unread_project(pj)), must_open=["big.py"])   # the rule alone: must_open as D1-1 would give it for big.py
        big, small = pj.dir + "/big.py", pj.dir + "/small.py"
        def ut(files=(), commands=()):
            return w.unread_touched({"files": list(files), "commands": list(commands)}, packet)
        assert w.unread_touched(None, packet) == ["big.py"], "not on record: every must_open path is unread"
        assert ut() == ["big.py"]
        assert ut(["Read %s" % small]) == ["big.py"], "small.py read, big.py not"
        assert ut(["Read %s" % big]) == [], "absolute under the target"
        assert ut(["Read big.py"]) == [], "relative to the target"
        assert ut(["Read %s" % os.path.realpath(big)]) == [], "the real path"
        assert ut(["Grep %s" % big]) == [], "a Grep of the file opens it"
        assert ut(["Grep %s" % pj.dir]) == ["big.py"], "a Grep of the directory opens none under it"
        assert ut(["Glob %s" % pj.dir]) == ["big.py"], "a Glob of the directory opens none under it"
        assert ut(["Glob %s" % big]) == ["big.py"], "a Glob opens nothing"
        assert ut(["Read %s/big.py.bak" % pj.dir]) == ["big.py"], "another file's path is not this one"
        assert ut(commands=[{"command": "sed -n '1,80p' big.py", "exit": 0}]) == []
        assert ut(commands=[{"command": "sed -n '1,80p' big.py", "exit": None}]) == [], "exit None: it ran"
        assert ut(commands=[{"command": "sed -n '1,80p' big.py", "exit": 1}]) == ["big.py"], "a failed command read nothing"
        assert ut(commands=[{"command": "cat %s" % big, "exit": 0}]) == [], "absolute under the target"
        assert ut(commands=[{"command": "cat %s" % os.path.realpath(big), "exit": 0}]) == [], "the real path"
        assert ut(commands=[{"command": "cat old_big.py", "exit": 0}]) == ["big.py"], "not a whole token"
        assert ut(commands=[{"command": "cat big.py.orig", "exit": 0}]) == ["big.py"], "not a whole token"
        assert ut(commands=[{"command": "rg -n big_ .", "exit": 0}]) == ["big.py"], "a search of the directory opens none"
        for view in ("git diff -- big.py", "git diff --stat HEAD -- big.py", "git show HEAD:big.py", "git log -- big.py", "git status -- big.py"):
            assert ut(commands=[{"command": view, "exit": 0}]) == ["big.py"], "git's view of the change opens nothing: " + view
        for says in ("echo big.py", "printf '%s' big.py", "cd big.py", "true big.py", "pwd big.py"):
            assert ut(commands=[{"command": says, "exit": 0}]) == ["big.py"], "an echo opens nothing: " + says
        for lists in ("ls big.py", "ls -l big.py", "stat big.py", "wc -l big.py", "test -f big.py", "[ -f big.py ]", "file big.py", "du big.py", "find . -name big.py"):
            assert ut(commands=[{"command": lists, "exit": 0}]) == ["big.py"], "a listing opens nothing: " + lists
        assert ut(commands=[{"command": "git diff -- big.py && cat big.py", "exit": 0}]) == [], "a part after && counts on its own"
        assert ut(commands=[{"command": "ls big.py; sed -n 1,5p big.py", "exit": 0}]) == [], "a part after ; counts on its own"
        assert ut(commands=[{"command": "git show HEAD:big.py || head big.py", "exit": 0}]) == [], "a part after || counts on its own"
        assert ut(commands=[{"command": "echo big.py\ncat big.py", "exit": 0}]) == [], "a part on the next line counts on its own"
        assert ut(commands=[{"command": "cat big.py | head", "exit": 0}]) == [], "a part before | counts on its own"
        assert ut(commands=[{"command": "git diff -- big.py && cat big.py", "exit": 1}]) == ["big.py"], "a failed command opened nothing"
        # in must_open's order, and only what must_open names
        three = dict(packet, touched=["small.py", "big.py", "c.py"], must_open=["big.py", "c.py"])
        assert w.unread_touched({"files": [], "commands": []}, three) == ["big.py", "c.py"]
        assert w.unread_touched({"files": ["Read big.py"], "commands": []}, three) == ["c.py"]
        assert w.unread_touched(None, three) == ["big.py", "c.py"]
        whole = {k: v for k, v in packet.items() if k != "must_open"}
        assert w.unread_touched({"files": [], "commands": []}, whole) == [], "nothing to open: nothing unread"
        assert w.unread_touched(None, whole) == [], "nothing to open: nothing unread, even with no record"



def test_D2_an_accept_that_left_a_big_touched_file_unread_says_so_and_a_reject_is_untouched():
    """11-06 D2, amended 11-09 (D1-3): small.py (modified) and big.py (not in the diff) are both in must_open; an accept that
    left either unread is not an accept (verdict null, answered accept, the unread named); reading both is an accept with
    no non-claim; the 2.2.x "left unread" non-claim is never written; a reject is untouched."""
    assert callable(getattr(w, "unread_touched", None)), "eyes_worker.unread_touched is missing"
    with Project() as pj:
        req = unread_project(pj)
        assert dwitbuk.verify_packet(req).get("must_open") == ["small.py", "big.py"], dwitbuk.verify_packet(req).get("must_open")
        reqf, resp = os.path.join(pj.dir, "local", "req.json"), os.path.join(pj.dir, "local", "resp.json")
        write(reqf, req)
        verdict = '{"verdict":"accept","findings":[]}'
        def codex_item(n, kind, **kw):
            return json.dumps({"type": "item.completed", "item": dict(id="item_%d" % n, type=kind, **kw)})
        def shell(cmd):
            return "/bin/zsh -lc %s" % json.dumps(cmd).replace('"', "'")
        def claude_tool(name, **inp):
            return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t-" + name, "name": name, "input": inp}]}})
        said = json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": verdict}]}})
        streams = {
            "read-small": [claude_tool("Read", file_path=pj.dir + "/small.py"), said],
            "read-big": [claude_tool("Read", file_path=pj.dir + "/big.py"), said],
            "read-both": [claude_tool("Read", file_path=pj.dir + "/small.py"), claude_tool("Read", file_path=pj.dir + "/big.py"), said],
            "grep-dir": [claude_tool("Grep", pattern="big_", path=pj.dir), said],
            "sed-ok": [codex_item(0, "command_execution", command=shell("sed -n '1,80p' big.py"), aggregated_output="big_00000 = 0", exit_code=0),
                       codex_item(1, "command_execution", command=shell("cat small.py"), aggregated_output="small = 2", exit_code=0),
                       codex_item(2, "agent_message", text=verdict)],
            "sed-failed": [codex_item(0, "command_execution", command=shell("sed -n '1,80p' big.py"), aggregated_output="", exit_code=1),
                           codex_item(1, "agent_message", text=verdict)],
        }
        def answer(case, verdict_="accept", findings=()):
            def fake(packet, schema, args):
                write(os.path.join(os.path.dirname(args.response), "resp.transcript.jsonl"), "\n".join(streams[case]) + "\n")
                return {"verdict": verdict_, "findings": list(findings), "worker": {"host": "codex", "model": "m", "transcript": "resp.transcript.jsonl"}}
            old_codex, old_argv = w.codex, sys.argv
            w.codex, sys.argv = fake, ["eyes_worker.py", "--request", reqf, "--response", resp, "--host", "codex"]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    assert w.main() == 0
            finally:
                w.codex, sys.argv = old_codex, old_argv
            return json.load(io.open(resp, encoding="utf-8"))
        def not_an_accept(got, unread):
            assert "verdict" in got and got["verdict"] is None and got.get("answered") == "accept" and got.get("findings") == [], got
            assert got.get("unread") == unread and "read" in got, got
            assert got["summary"].startswith("not an accept:") and all("`%s`" % p in got["summary"] for p in unread), got["summary"]
            assert not [n for n in got.get("non-claims") or [] if n.startswith("accepted") or "left unread" in n], got.get("non-claims")
            assert UNREAD_BIG not in (got.get("non-claims") or []), "the 2.2.x non-claim is never written any more"
            return got
        got = not_an_accept(answer("read-small"), ["big.py"])
        assert got["read"]["files"] == ["Read %s/small.py" % pj.dir], got
        assert "`small.py`" not in got["summary"], got["summary"]
        got = not_an_accept(answer("read-big"), ["small.py"])
        assert got["read"]["files"] == ["Read %s/big.py" % pj.dir], got
        got = answer("read-both")
        assert got["verdict"] == "accept" and "non-claims" not in got and "unread" not in got and "answered" not in got, got
        assert got["read"]["files"] == ["Read %s/small.py" % pj.dir, "Read %s/big.py" % pj.dir], got["read"]
        not_an_accept(answer("grep-dir"), ["small.py", "big.py"])   # a Grep over the directory opens none of the files under it
        got = answer("sed-ok")
        assert got["verdict"] == "accept" and "non-claims" not in got and "unread" not in got, got
        assert got["read"]["commands"][0]["command"].startswith("sed -n") and got["read"]["commands"][0]["exit"] == 0, got
        got = not_an_accept(answer("sed-failed"), ["small.py", "big.py"])   # a failed command opened nothing — and no "accepted without reading the tree"
        assert "non-claims" not in got, got.get("non-claims")
        anomaly = {"kind": "anomaly", "where": "small.py", "record_quote": "", "tree_quote": "small = 2", "why": "odd"}
        got = answer("read-small", "reject", [anomaly])
        assert got["verdict"] == "reject" and "non-claims" not in got and "read" not in got, got
        assert "unread" not in got and "answered" not in got and got["findings"] == [anomaly], got


# --- 11-09 V1: an accept stands only when the eyes opened every changed file the packet did not show whole -----------------
# 11-09, dwitbuk 2.2.1: three files changed by small edits (every change in the diff as hunks); the verifier opened only
# mod_a.py and said accept; the record said `"verdict": "accept"` with no non-claim at all. The packet now names in
# `must_open` each touched file whose current text it does not hold whole, and an accept that left one unread is no accept.

def v1_project(pj, touched=None, **kw):
    """Three tracked files, each then changed by one small edit: every change is in the diff as hunks, no file whole."""
    for n in ("mod_a.py", "mod_b.py", "mod_c.py"):
        write(os.path.join(pj.dir, n), "%s = 1\nkeep = True\n" % n[:-3])
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "three files")
    since = git(pj.dir, "rev-parse", "HEAD")
    for n in ("mod_a.py", "mod_b.py", "mod_c.py"):
        write(os.path.join(pj.dir, n), "%s = 2\nkeep = True\n" % n[:-3])
    return verify_req(pj, touched or ["mod_a.py", "mod_b.py", "mod_c.py"], since, brief="three small edits",
                      contract={"Q-three": "## Q-three\n\neach constant is two"}, checks=[["python3", "t.py"]], tests=["t.py"],
                      built={"summary": "built", "verified": [], "non-claims": []}, **kw)


V1_VERDICT = '{"verdict":"accept","findings":[]}'


def v1_read(path):
    """A Claude session's Read of `path` (absolute or relative to the target), as the host streams it."""
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t-read", "name": "Read", "input": {"file_path": path}}]}})


def v1_tool(name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t-" + name, "name": name, "input": inp}]}})


def v1_said(text=V1_VERDICT):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})


def v1_ran(command, exit_code=0, n=0):
    """A Codex session's command, as the host streams it: the argument of a login shell, with its exit code."""
    return json.dumps({"type": "item.completed", "item": {"id": "item_%d" % n, "type": "command_execution", "command": "/bin/zsh -lc " + shlex.quote(command),
                                                           "aggregated_output": "", "exit_code": exit_code}})


def v1_answer(pj, req, events, verdict="accept", findings=(), transcript="resp.transcript.jsonl", summary=None, fail=None):
    """eyes_worker.main on `req` through a fake host that writes `events` (None: no transcript at all) beside the response and
    answers `verdict`/`findings` with a worker record naming `transcript` (None: no transcript key); the saved response."""
    reqf, resp = os.path.join(pj.dir, "local", "req.json"), os.path.join(pj.dir, "local", "resp.json")
    write(reqf, req)
    for stale in (resp, os.path.join(pj.dir, "local", "resp.transcript.jsonl")):
        if os.path.exists(stale):
            os.unlink(stale)
    def fake(packet, schema, args):
        if fail:
            raise SystemExit(fail)
        if events is not None:
            write(os.path.join(os.path.dirname(args.response), "resp.transcript.jsonl"), "\n".join(events) + "\n")
        worker = {"host": "codex", "model": "m", **({"transcript": transcript} if transcript else {})}
        return {"verdict": verdict, "findings": list(findings), **({"summary": summary} if summary else {}), "worker": worker}
    old_codex, old_argv = w.codex, sys.argv
    w.codex, sys.argv = fake, ["eyes_worker.py", "--request", reqf, "--response", resp, "--host", "codex"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            assert w.main() == 0
    finally:
        w.codex, sys.argv = old_codex, old_argv
    return json.load(io.open(resp, encoding="utf-8"))


def v1_not_an_accept(got, unread, on_record=True):
    """D1-3: the shape of an answer the eyes called accept while a `must_open` file went unread."""
    assert "verdict" in got and got["verdict"] is None, got
    assert got.get("answered") == "accept", got
    assert got.get("unread") == list(unread), got
    assert got.get("findings") == [], got
    assert ("read" in got) == on_record, got
    summary = got.get("summary") or ""
    assert summary.startswith("not an accept:"), summary
    for path in unread:
        assert "`%s`" % path in summary, (path, summary)
    if not on_record:
        assert "not on record" in summary, summary
    assert not [n for n in got.get("non-claims") or [] if n.startswith("accepted")], got.get("non-claims")
    assert not [n for n in got.get("non-claims") or [] if "left unread" in n], got.get("non-claims")
    return got


def v1_accept(got):
    """D1-3: an accept that stands — exactly as today, nothing of the not-an-accept shape on it."""
    assert got.get("verdict") == "accept" and got.get("findings") == [], got
    assert "unread" not in got and "answered" not in got, got
    assert not [n for n in got.get("non-claims") or [] if "left unread" in n], got.get("non-claims")
    return got


def test_V1_must_open_names_each_modified_file_and_not_a_file_the_diff_shows_whole():
    """D1-1: a modified tracked file is in must_open; an untracked small new file (shown as `(new file)`), a file added and
    committed since `since` (a new-file text diff) and a deleted file are not; when nothing qualifies the key is absent."""
    with Project() as pj:
        write(os.path.join(pj.dir, "m.py"), "m = 1\n")
        write(os.path.join(pj.dir, "d.py"), "d = 1\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base")
        since = git(pj.dir, "rev-parse", "HEAD")
        write(os.path.join(pj.dir, "c.py"), "c = 'committed since'\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "the task committed a new file")
        write(os.path.join(pj.dir, "m.py"), "m = 2\n")
        write(os.path.join(pj.dir, "n.py"), "n = 'untracked, small'\n")
        os.unlink(os.path.join(pj.dir, "d.py"))
        p = dwitbuk.verify_packet(verify_req(pj, ["n.py", "m.py", "c.py", "d.py"], since))
        d = p["diff"]
        assert "+++ n.py (new file)" in d and "new file mode" in d and "+c = 'committed since'" in d and "deleted file mode" in d and "+m = 2" in d, d
        assert "not_in_diff" not in p, p.get("not_in_diff")
        assert p.get("must_open") == ["m.py"], p.get("must_open")
        assert isinstance(p["must_open"], list)
        q = dwitbuk.verify_packet(verify_req(pj, ["n.py", "c.py", "d.py"], since))
        assert "must_open" not in q, q.get("must_open")   # every file whole or gone: no key, as not_in_diff has none
        assert "not_in_diff" not in q


def test_V1_must_open_holds_the_files_not_in_diff_and_binary_changes_in_touched_order():
    """D1-1: a big untracked new file (in not_in_diff), a file whose diff is cut by the 80000 limit, a binary change (modified,
    or new in a new-file binary diff) and every modified file are in must_open, in touched order, each once; not_in_diff keeps
    its meaning and its key beside it."""
    with Project() as pj:
        write(os.path.join(pj.dir, "a_small.py"), "small = 'before'\n")
        write(os.path.join(pj.dir, "b_huge.py"), "huge = 0\n")
        write(os.path.join(pj.dir, "c_after.py"), "after = 'before'\n")
        with open(os.path.join(pj.dir, "bin_mod.dat"), "wb") as fh:
            fh.write(b"\x00\x01binary-before\x00\n" * 50)
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base")
        since = git(pj.dir, "rev-parse", "HEAD")
        with open(os.path.join(pj.dir, "bin_new.dat"), "wb") as fh:
            fh.write(b"\x00\x02binary-new\x00\n" * 50)
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "a binary file added since")
        write(os.path.join(pj.dir, "a_small.py"), "small = 'after'\n")
        write(os.path.join(pj.dir, "b_huge.py"), "".join("huge_%05d = %d  # a long line of the huge change\n" % (i, i) for i in range(2500)))
        write(os.path.join(pj.dir, "c_after.py"), "after = 'after'\n")
        write(os.path.join(pj.dir, "d_big_new.txt"), "big new file line\n" * 3000)   # 54000 bytes, untracked: git has no diff
        write(os.path.join(pj.dir, "n.py"), "n = 'small and new'\n")
        with open(os.path.join(pj.dir, "bin_mod.dat"), "wb") as fh:
            fh.write(b"\x00\x03binary-after\x00\n" * 50)
        assert os.path.getsize(os.path.join(pj.dir, "b_huge.py")) > 80000 and os.path.getsize(os.path.join(pj.dir, "d_big_new.txt")) >= 40000
        touched = ["d_big_new.txt", "n.py", "bin_new.dat", "a_small.py", "bin_mod.dat", "b_huge.py", "c_after.py"]
        p = dwitbuk.verify_packet(verify_req(pj, touched, since))
        assert p["touched"] == touched
        assert "Binary files" in p["diff"] and "+++ n.py (new file)" in p["diff"], p["diff"][:600]
        nid = p.get("not_in_diff")
        assert isinstance(nid, list) and set(nid) == {"d_big_new.txt", "b_huge.py", "c_after.py"}, nid   # unchanged beside must_open
        assert p.get("must_open") == ["d_big_new.txt", "bin_new.dat", "a_small.py", "bin_mod.dat", "b_huge.py", "c_after.py"], p.get("must_open")
        # the same files touched in another order: must_open follows touched, and names each path once
        shuffled = ["c_after.py", "a_small.py", "a_small.py", "bin_mod.dat", "n.py", "d_big_new.txt"]
        q = dwitbuk.verify_packet(verify_req(pj, shuffled, since))
        assert q.get("must_open") == ["c_after.py", "a_small.py", "bin_mod.dat", "d_big_new.txt"], q.get("must_open")


def test_V1_must_open_follows_a_nested_repository_and_skips_what_is_not_a_regular_file():
    """D1-1: a modified file inside a nested repository with its own `since` is in must_open (its diff taken there); a file
    added and committed there since is not; a touched directory and a gitlink are not regular files and are not in it."""
    with Project() as pj:
        write(os.path.join(pj.dir, ".gitignore"), "/engine/\n")
        write(os.path.join(pj.dir, "pkg", "x.py"), "x = 1\n")
        lib = os.path.join(pj.dir, "lib")
        write(os.path.join(lib, "child.py"), "child = 1\n")
        git(lib, "init", "-q"); git(lib, "add", "-A"); git(lib, "commit", "-qm", "lib")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-q", "-m", "base with pkg and a gitlink")
        base = git(pj.dir, "rev-parse", "HEAD")
        eng = os.path.join(pj.dir, "engine")
        os.makedirs(eng)
        git(eng, "init", "-q")
        write(os.path.join(eng, "gate.py"), "limit = 1\n")
        git(eng, "add", "-A"); git(eng, "commit", "-q", "-m", "base")
        start = git(eng, "rev-parse", "HEAD")
        write(os.path.join(eng, "gate.py"), "limit = 2\n")
        write(os.path.join(eng, "new.py"), "fresh = 1\n")
        git(eng, "add", "-A"); git(eng, "commit", "-q", "-m", "the task's work, committed in the nested repository")
        write(os.path.join(pj.dir, "a.py"), "x = 2\n")
        write(os.path.join(pj.dir, "pkg", "x.py"), "x = 2\n")
        changed_gitlink(lib)
        req = verify_req(pj, ["a.py", "engine/new.py", "engine/gate.py", "pkg", "pkg/x.py", "lib"], base)
        req["since"] = {".": base, "engine": start}
        p = dwitbuk.verify_packet(req)
        assert "-limit = 1" in p["diff"] and "+limit = 2" in p["diff"] and "+fresh = 1" in p["diff"] and "+x = 2" in p["diff"], p["diff"]
        assert not os.path.isfile(os.path.join(pj.dir, "pkg")) and not os.path.isfile(os.path.join(pj.dir, "lib"))
        assert p.get("must_open") == ["a.py", "engine/gate.py", "pkg/x.py"], p.get("must_open")


def test_V1_must_open_never_holds_a_path_only_in_excluded_and_is_absent_when_nothing_qualifies():
    """D1-1: a record path in the request's `excluded` (not in `touched`) is never in must_open, however it changed; the same
    path in `touched` is the task's and follows the rule like any file."""
    with Project() as pj:
        write(os.path.join(pj.dir, "hunsu.json"), '{"plugins": "before"}\n')
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base")
        since = git(pj.dir, "rev-parse", "HEAD")
        write(os.path.join(pj.dir, "hunsu.json"), '{"plugins": "after"}\n')
        write(os.path.join(pj.dir, "n.py"), "n = 'small and new'\n")
        excluded = {"record-paths": ["hunsu.json", ".chongdae/run-1/state.json"]}
        p = dwitbuk.verify_packet(verify_req(pj, ["n.py"], since, excluded=excluded))
        assert p["excluded"] == ["hunsu.json"] and "+++ n.py (new file)" in p["diff"], p
        assert "must_open" not in p, p.get("must_open")
        q = dwitbuk.verify_packet(verify_req(pj, [], since, excluded=excluded))
        assert q["touched"] == [] and q["excluded"] == ["hunsu.json"] and "must_open" not in q, q.get("must_open")
        r = dwitbuk.verify_packet(verify_req(pj, ["hunsu.json", "n.py"], since, excluded=excluded))
        assert r.get("must_open") == ["hunsu.json"] and '+{"plugins": "after"}' in r["diff"], r.get("must_open")


def test_V1_instructions_name_must_open_only_when_it_is_present():
    """D1-2: with must_open the instructions tell the eyes to open (Read) each of its files under target before they accept and
    that an accept counts only when their session opened each; without it they do not mention must_open."""
    with Project() as pj:
        req = v1_project(pj)
        p = dwitbuk.verify_packet(req)
        assert p.get("must_open") == ["mod_a.py", "mod_b.py", "mod_c.py"], p.get("must_open")
        instr = p["instructions"]
        assert "`must_open`" in instr, instr
        assert "Read" in instr and "accept" in instr and "reject" in instr, instr
        write(os.path.join(pj.dir, "n.py"), "n = 'small and new'\n")
        q = dwitbuk.verify_packet(dict(req, touched=["n.py"]))
        assert "must_open" not in q and "must_open" not in q["instructions"], q["instructions"]


def test_V1_an_accept_that_left_a_must_open_file_unread_is_not_an_accept():
    """D1-3, the 11-09 reproduction: three modified files, the eyes opened only mod_a.py and said accept — verdict null,
    answered accept, unread the other two in must_open order, a summary that starts `not an accept:` and names them in
    backticks, no non-claim starting "accepted". A session that opened nothing on that diff is not an accept either."""
    with Project() as pj:
        req = v1_project(pj)
        got = v1_not_an_accept(v1_answer(pj, req, [v1_read(pj.dir + "/mod_a.py"), v1_said()]), ["mod_b.py", "mod_c.py"])
        assert got["read"]["files"] == ["Read %s/mod_a.py" % pj.dir], got["read"]
        assert "`mod_a.py`" not in got["summary"], got["summary"]
        assert "non-claims" not in got, got.get("non-claims")
        got = v1_not_an_accept(v1_answer(pj, req, [v1_said()]), ["mod_a.py", "mod_b.py", "mod_c.py"])
        assert got["read"] == {"files": [], "commands": [], "answered-before-reading": True}, got["read"]
        # a Grep of the directory, a Glob, a search of the directory: none opens a file under it
        got = v1_not_an_accept(v1_answer(pj, req, [v1_tool("Grep", pattern="keep", path=pj.dir), v1_tool("Glob", pattern="*.py", path=pj.dir),
                                                   v1_ran("rg -n keep .", 0), v1_said()]), ["mod_a.py", "mod_b.py", "mod_c.py"])
        assert len(got["read"]["files"]) == 2 and len(got["read"]["commands"]) == 1, got["read"]


def test_V1_an_accept_whose_session_opened_every_must_open_file_stands():
    """D1-3: opening all three — a Claude Read by absolute path, a Read by target-relative path, a Grep of the file; or Codex's
    `sed -n` and `cat` — is an accept exactly as today: `read` kept, no `unread`, no `answered`, no non-claim."""
    with Project() as pj:
        req = v1_project(pj)
        assert dwitbuk.verify_packet(req).get("must_open") == ["mod_a.py", "mod_b.py", "mod_c.py"], "the accept stands against a must_open that names all three"
        got = v1_accept(v1_answer(pj, req, [v1_read(pj.dir + "/mod_a.py"), v1_read("mod_b.py"), v1_tool("Grep", pattern="keep", path=pj.dir + "/mod_c.py"), v1_said()]))
        assert got["read"]["files"] == ["Read %s/mod_a.py" % pj.dir, "Read mod_b.py", "Grep %s/mod_c.py" % pj.dir] and "non-claims" not in got, got
        got = v1_accept(v1_answer(pj, req, [v1_ran("sed -n 1,9p mod_a.py", 0, 0), v1_ran("cat %s/mod_b.py" % pj.dir, 0, 1),
                                            v1_ran("sed -n '1,80p' mod_c.py | head -3", 0, 2), v1_said()]))
        assert [c["exit"] for c in got["read"]["commands"]] == [0, 0, 0] and "non-claims" not in got, got
        # the real path of the target, when the eyes resolved a symlinked temporary directory
        real = os.path.realpath(pj.dir)
        got = v1_accept(v1_answer(pj, req, [v1_read(real + "/mod_a.py"), v1_read(real + "/mod_b.py"), v1_read(real + "/mod_c.py"), v1_said()]))
        assert "non-claims" not in got, got


def test_V1_an_accept_with_no_recorded_session_is_not_an_accept():
    """D1-3: with no transcript (the worker record names none, or names a file that is missing) nothing is on record as
    opened: every must_open file is unread, there is no `read`, and the summary says what the eyes opened is not on record."""
    with Project() as pj:
        req = v1_project(pj)
        got = v1_not_an_accept(v1_answer(pj, req, None, transcript=None), ["mod_a.py", "mod_b.py", "mod_c.py"], on_record=False)
        assert got.get("worker", {}).get("host") == "codex", got.get("worker")
        got = v1_not_an_accept(v1_answer(pj, req, None, transcript="gone.transcript.jsonl"), ["mod_a.py", "mod_b.py", "mod_c.py"], on_record=False)
        assert not os.path.exists(os.path.join(pj.dir, "local", "gone.transcript.jsonl"))
        # an answer with no worker record at all (a host that gave none): the same
        reqf, resp = os.path.join(pj.dir, "local", "req.json"), os.path.join(pj.dir, "local", "resp.json")
        write(reqf, req)
        old_claude, old_argv = w.claude, sys.argv
        w.claude, sys.argv = (lambda packet, schema, args: {"verdict": "accept", "findings": []}), ["eyes_worker.py", "--request", reqf, "--response", resp]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                assert w.main() == 0
        finally:
            w.claude, sys.argv = old_claude, old_argv
        v1_not_an_accept(json.load(io.open(resp, encoding="utf-8")), ["mod_a.py", "mod_b.py", "mod_c.py"], on_record=False)


def test_V1_a_command_opens_a_file_only_when_it_reads_it_as_a_whole_token_and_ran():
    """D1-3, the command rule: git's view of the change, an echo and a listing open nothing, nor does a command that failed or
    one naming another file; `cat`, `sed -n`, `head` do, by the target-relative, absolute or real path, and a part after `&&`
    counts on its own. mod_b.py and mod_c.py are Read in every case; the command under test is mod_a.py's only opening."""
    with Project() as pj:
        req = v1_project(pj)
        real = os.path.realpath(pj.dir)
        def outcome(command, exit_code=0):
            return v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_ran(command, exit_code), v1_said()])
        for command in ("git diff -- mod_a.py", "git diff --stat HEAD -- mod_a.py", "git show HEAD:mod_a.py", "git log --oneline -- mod_a.py", "git status --short mod_a.py",
                        "ls -l mod_a.py", "wc -l mod_a.py", "stat mod_a.py", "file mod_a.py", "du -h mod_a.py", "test -f mod_a.py", "[ -f mod_a.py ]", "find . -name mod_a.py",
                        "echo mod_a.py", "printf '%s\\n' mod_a.py", "cat mod_a.py.orig", "cat old_mod_a.py", "cat mod_a.pyc", "git diff -- mod_a.py; echo mod_a.py",
                        "cat %s/mod_a.py.bak" % pj.dir):
            got = outcome(command)
            v1_not_an_accept(got, ["mod_a.py"])
            assert got["read"]["commands"] == [{"command": command, "exit": 0}], (command, got["read"])
        for command in ("cat mod_a.py", "sed -n 1,9p mod_a.py", "head -5 mod_a.py", "cat %s/mod_a.py" % pj.dir, "cat %s/mod_a.py" % real,
                        "git diff -- mod_a.py && cat mod_a.py", "git log -- mod_a.py || sed -n '1,80p' mod_a.py", "ls\ncat mod_a.py", "cat mod_a.py | head -3"):
            v1_accept(outcome(command))
        v1_not_an_accept(outcome("cat mod_a.py", 1), ["mod_a.py"])   # a command that failed opened nothing
        v1_not_an_accept(outcome("git diff -- mod_a.py && cat mod_a.py", 1), ["mod_a.py"])
        v1_accept(outcome("cat mod_a.py", None))   # no exit recorded: it ran


def test_V1_an_empty_must_open_keeps_todays_accept_and_its_non_claim():
    """D1-3: with no must_open (only a small new file and a deleted file touched) an accept that read nothing stands as today,
    with today's "accepted without reading the tree" non-claim; with no transcript, today's "not on record" non-claim."""
    with Project() as pj:
        write(os.path.join(pj.dir, "d.py"), "d = 1\n")
        git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base")
        since = git(pj.dir, "rev-parse", "HEAD")
        os.unlink(os.path.join(pj.dir, "d.py"))
        write(os.path.join(pj.dir, "n.py"), "n = 'small and new'\n")
        req = verify_req(pj, ["n.py", "d.py"], since, contract={"Q-n": "## Q-n\n\nn is new"}, tests=["t.py"], built={"summary": "built", "verified": [], "non-claims": []})
        assert "must_open" not in dwitbuk.verify_packet(req)
        got = v1_accept(v1_answer(pj, req, [v1_said()]))
        assert got["read"] == {"files": [], "commands": [], "answered-before-reading": True}, got["read"]
        assert len(got["non-claims"]) == 1 and got["non-claims"][0].startswith("accepted without reading the tree: the eyes opened no file and ran no command"), got["non-claims"]
        got = v1_accept(v1_answer(pj, req, None, transcript=None))
        assert "read" not in got and got["non-claims"] == ["accepted, and what the eyes read is not on record (no transcript of their session)"], got
        # and the 2.2.x "left unread" non-claim is never written: a must_open file unread is not an accept, never a note
        three = v1_project(pj)
        got = v1_not_an_accept(v1_answer(pj, three, [v1_said()]), ["mod_a.py", "mod_b.py", "mod_c.py"])
        assert "non-claims" not in got, got.get("non-claims")


def test_V1_a_reject_weigh_counts_as_accept_with_an_unread_must_open_file_is_not_an_accept():
    """D1-3: a reject on unfounded findings only, which weigh counts as accept, is not an accept while a must_open file is
    unread: `unfounded` stays and the summary keeps weigh's "counted as accept" after `not an accept:`; with every file
    opened it is the accept weigh made of it."""
    with Project() as pj:
        req = v1_project(pj)
        nowhere = {"kind": "claim-unverified", "where": "built.verified[0]", "record_quote": "`I ran nothing at all`", "tree_quote": "keep = True", "why": "says so"}
        got = v1_not_an_accept(v1_answer(pj, req, [v1_said()], "reject", [nowhere], summary="s"), ["mod_a.py", "mod_b.py", "mod_c.py"])
        assert len(got.get("unfounded") or []) == 1 and got["unfounded"][0]["where"] == "built.verified[0]", got.get("unfounded")
        assert "counted as accept" in got["summary"] and "the eyes said: s" in got["summary"], got["summary"]
        opened = [v1_read("mod_a.py"), v1_read("mod_b.py"), v1_read("mod_c.py"), v1_said()]
        got = v1_accept(v1_answer(pj, req, opened, "reject", [nowhere], summary="s"))
        assert len(got["unfounded"]) == 1 and got["summary"].startswith("rejected only on unfounded finding(s)") and "counted as accept" in got["summary"], got
        # a reject with no finding at all, counted as accept, follows the same rule
        got = v1_not_an_accept(v1_answer(pj, req, [v1_read("mod_a.py"), v1_said()], "reject", []), ["mod_b.py", "mod_c.py"])
        assert "counted as accept" in got["summary"] and "unfounded" not in got, got["summary"]


def test_V1_a_reject_with_a_grounded_finding_stays_a_reject_while_the_same_unread_session_cannot_accept():
    """D1-4: a reject whose grounded, founded finding stands is not changed — no `unread`, no `read`, no `answered`, its verdict,
    findings and summary as today — although the eyes opened nothing; the same session saying accept is not an accept. A
    null verdict from a host that failed stays as today."""
    with Project() as pj:
        req = v1_project(pj)
        anomaly = {"kind": "anomaly", "where": "mod_a.py", "record_quote": "", "tree_quote": "mod_a = 2", "why": "odd"}
        got = v1_answer(pj, req, [v1_said('{"verdict":"reject","findings":[]}')], "reject", [anomaly], summary="the eyes' own words")
        assert got["verdict"] == "reject" and got["findings"] == [anomaly] and got["summary"] == "the eyes' own words", got
        assert "unread" not in got and "read" not in got and "answered" not in got and "non-claims" not in got and "unfounded" not in got, got
        founded = {"kind": "plan-vs-code", "where": "contract.Q-three; mod_a.py", "record_quote": "`each constant is two`", "tree_quote": "mod_a = 2", "why": "three"}
        got = v1_answer(pj, req, None, "reject", [founded], transcript=None)
        assert got["verdict"] == "reject" and got["findings"] == [founded] and "unread" not in got and "answered" not in got, got
        v1_not_an_accept(v1_answer(pj, req, [v1_said()]), ["mod_a.py", "mod_b.py", "mod_c.py"])
        got = v1_answer(pj, req, None, fail="codex exited 1: boom")
        assert got["verdict"] is None and got["findings"] == [] and got["summary"] == "codex exited 1: boom", got
        assert "answered" not in got and "unread" not in got and "read" not in got, got


# --- 11-09 V2: a verify packet holds only its own task's changes --------------------------------------------------------------
# 11-09, dwitbuk 2.2.1: a record another open task wrote and did not commit, listed in the request's excluded record paths and
# not in this task's touched, reached the packet with its diff in excluded_diff — another task's work handed to this verifier.

def v2_project(pj):
    """Two relation records and a source file committed; then another task changes R-other (uncommitted), this task changes
    R-mine and the source file. Returns the request: R-mine and src/a.py touched, both records in `excluded.record-paths`."""
    write(os.path.join(pj.dir, "hunsu.lock.json"), {"record-paths": {"mangsang": ["mangsang/"]}})
    write(os.path.join(pj.dir, "mangsang", "relations", "R-other.json"), '{"id": "R-other", "v": "other-task-old-relation"}\n')
    write(os.path.join(pj.dir, "mangsang", "relations", "R-mine.json"), '{"id": "R-mine", "v": "my-old-relation"}\n')
    write(os.path.join(pj.dir, "src", "a.py"), "src_a = 'before'\n")
    git(pj.dir, "add", "-A"); git(pj.dir, "commit", "-qm", "base with records")
    since = git(pj.dir, "rev-parse", "HEAD")
    write(os.path.join(pj.dir, "mangsang", "relations", "R-other.json"), '{"id": "R-other", "v": "other-task-new-relation"}\n')
    write(os.path.join(pj.dir, "mangsang", "relations", "R-mine.json"), '{"id": "R-mine", "v": "my-new-relation"}\n')
    write(os.path.join(pj.dir, "src", "a.py"), "src_a = 'after'\n")
    return verify_req(pj, ["src/a.py", "mangsang/relations/R-mine.json"], since,
                      excluded={"record-paths": ["mangsang/relations/R-other.json", "mangsang/relations/R-mine.json", ".chongdae/run-1/state.json"]})


# --- 11-09 V1 fix: the command rule resolves each shell word as a path, not as one of three spellings -------------------------
# Late eyes on the 2.2.1 build: `cat ./mod_a.py`, `sed -n 1,9p ./mod_a.py` and `head -3 pkg/../mod_a.py`, run in the target,
# did not count as opening mod_a.py — the command rule compared each word with exactly three spellings of the file, unnormalized,
# while the Read/Grep branch beside it normalized a relative path. The amended rule: a word, taken as a path relative to the
# target (an absolute word stays absolute), opens the file when it resolves by real path to the file's real path under the target.

def v1_fix_outcome(pj, req, command, exit_code=0):
    """mod_b.py and mod_c.py Read; `command` is mod_a.py's only chance of being opened."""
    return v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_ran(command, exit_code), v1_said()])


def v1_fix_nested(pj):
    """The target as `proj` under the temporary area, whose parent really holds a mod_a.py of its own (so `../mod_a.py` names
    a real, different file); the project handle for the helpers, and the parent's file."""
    parent_file = os.path.join(pj.dir, "mod_a.py")
    write(parent_file, "mod_a = 'the parent directory has one too'\n")
    sub = made(os.path.join(pj.dir, "proj"))
    git(sub, "init", "-q", "-b", "main")
    inner = argparse.Namespace(dir=sub)
    return inner, parent_file


def v1_fix_link(pj, target):
    """A symlink in the temporary area to the target directory; Skip where the host will not let a test make one."""
    link = os.path.join(pj.dir, "link")
    try:
        os.symlink(target, link, target_is_directory=True)
    except (OSError, NotImplementedError, AttributeError) as err:
        raise Skip("os.symlink is not available to this test on this host: %s" % err)
    assert os.path.isfile(os.path.join(link, "mod_a.py")), "the link reaches the target's files"
    return link


def test_V1_fix_a_command_opens_a_file_by_every_spelling_that_resolves_to_it():
    """The amended command rule: `./mod_a.py`, `pkg/../mod_a.py` (pkg a real directory) and `<target>/./mod_a.py` each open
    mod_a.py, as the target-relative, absolute and real paths already do — with cat, sed -n and head alike, and in a part after
    `&&` or before `|`. The real path of the temporary directory is a symlinked spelling of the target on macOS."""
    with Project() as pj:
        req = v1_project(pj)
        made(os.path.join(pj.dir, "pkg"))
        real = os.path.realpath(pj.dir)
        assert dwitbuk.verify_packet(req).get("must_open") == ["mod_a.py", "mod_b.py", "mod_c.py"]
        for command in ("cat ./mod_a.py", "sed -n 1,9p ./mod_a.py", "head -3 pkg/../mod_a.py", "cat %s/./mod_a.py" % pj.dir, "sed -n '1,80p' ./pkg/../mod_a.py",
                        "cat %s/pkg/../mod_a.py" % real, "git diff -- ./mod_a.py && cat ./mod_a.py", "cat ./mod_a.py | head -3", "ls ./mod_a.py; sed -n 1,9p ./mod_a.py",
                        "cat mod_a.py", "cat %s/mod_a.py" % pj.dir, "cat %s/mod_a.py" % real):
            got = v1_fix_outcome(pj, req, command)
            assert got.get("verdict") == "accept", "%r opens mod_a.py: %s" % (command, {k: got.get(k) for k in ("verdict", "answered", "unread", "summary")})
            v1_accept(got)
            assert got["read"]["commands"] == [{"command": command, "exit": 0}], (command, got["read"])
            assert got["read"]["files"] == ["Read mod_b.py", "Read mod_c.py"], got["read"]
        v1_accept(v1_fix_outcome(pj, req, "cat ./mod_a.py", None))   # no exit recorded: it ran


def test_V1_fix_a_command_naming_another_path_opens_nothing_whatever_the_spelling():
    """The rule resolves a word, it does not search for the name: `mod_a.py.orig`, `old_mod_a.py`, `./mod_a.pyc`, `./pkg/mod_a.py`
    (a real file of another directory) and `<target>/./mod_a.py.bak` leave mod_a.py unread; and the exclusions keep their reach
    under the new spellings — git's view, a listing, an echo of `./mod_a.py` open nothing, nor does a `cat ./mod_a.py` that failed."""
    with Project() as pj:
        req = v1_project(pj)
        write(os.path.join(pj.dir, "pkg", "mod_a.py"), "other = 'another file'\n")
        assert dwitbuk.verify_packet(req).get("must_open") == ["mod_a.py", "mod_b.py", "mod_c.py"], "an untracked pkg/mod_a.py is not the task's change"
        for command in ("cat mod_a.py.orig", "cat old_mod_a.py", "cat ./mod_a.pyc", "cat ./pkg/mod_a.py", "sed -n 1,9p pkg/mod_a.py", "cat %s/./mod_a.py.bak" % pj.dir,
                        "cat %s/pkg/mod_a.py" % pj.dir, "cat ./mod_a.py.", "cat ./",
                        "git diff -- ./mod_a.py", "git show HEAD:./mod_a.py", "git log --oneline -- ./mod_a.py", "ls ./mod_a.py", "ls -l ./mod_a.py", "wc -l ./mod_a.py",
                        "stat ./mod_a.py", "echo ./mod_a.py", "printf '%s\\n' ./mod_a.py", "echo pkg/../mod_a.py", "ls %s/./mod_a.py" % pj.dir):
            got = v1_fix_outcome(pj, req, command)
            assert got.get("verdict") is None, "%r does not open mod_a.py: %s" % (command, {k: got.get(k) for k in ("verdict", "answered", "unread")})
            v1_not_an_accept(got, ["mod_a.py"])
            assert got["read"]["commands"] == [{"command": command, "exit": 0}], (command, got["read"])
        v1_not_an_accept(v1_fix_outcome(pj, req, "cat ./mod_a.py", 1), ["mod_a.py"])   # a failed command opened nothing
        v1_not_an_accept(v1_fix_outcome(pj, req, "head -3 pkg/../mod_a.py", 2), ["mod_a.py"])
        v1_not_an_accept(v1_fix_outcome(pj, req, "git diff -- ./mod_a.py && cat ./mod_a.py", 1), ["mod_a.py"])


def test_V1_fix_the_parent_directorys_mod_a_is_not_this_one():
    """`../mod_a.py`, relative to the target, resolves to the parent directory's own mod_a.py — a real file that is not the
    task's — so a session that read only that one left mod_a.py unread; `../proj/mod_a.py` comes back to this one and opens it."""
    with Project() as pj:
        inner, parent_file = v1_fix_nested(pj)
        req = v1_project(inner)
        assert req["target"] == inner.dir and os.path.isfile(parent_file) and os.path.isfile(os.path.join(inner.dir, "..", "mod_a.py"))
        assert dwitbuk.verify_packet(req).get("must_open") == ["mod_a.py", "mod_b.py", "mod_c.py"]
        for command in ("cat ../mod_a.py", "sed -n 1,9p ../mod_a.py", "head -3 ./../mod_a.py", "cat %s/../mod_a.py" % inner.dir, "cat %s" % parent_file):
            got = v1_fix_outcome(inner, req, command)
            assert got.get("verdict") is None, "%r is the parent's file, not this one: %s" % (command, {k: got.get(k) for k in ("verdict", "answered", "unread")})
            v1_not_an_accept(got, ["mod_a.py"])
        # the Read branch agrees: a Read of the parent's file is not a Read of this one
        v1_not_an_accept(v1_answer(inner, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read("../mod_a.py"), v1_said()]), ["mod_a.py"])
        v1_not_an_accept(v1_answer(inner, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read(parent_file), v1_said()]), ["mod_a.py"])
        # and a relative word that leaves the target and comes back names this one (red until the rule resolves the word)
        got = v1_fix_outcome(inner, req, "cat ../proj/mod_a.py")
        assert got.get("verdict") == "accept", "../proj/mod_a.py resolves to the target's own mod_a.py: %s" % {k: got.get(k) for k in ("verdict", "answered", "unread")}
        v1_accept(got)


def test_V1_fix_a_symlinked_spelling_of_the_target_opens_the_file():
    """A symlink to the target directory made in the temporary area: `<link>/mod_a.py` (absolute) and `../link/mod_a.py`
    (relative, out through the parent and back through the link) each resolve by real path to the target's mod_a.py and open
    it — by command and by Read alike. Skipped only where the host will not let a test make a symlink."""
    with Project() as pj:
        inner, _ = v1_fix_nested(pj)
        req = v1_project(inner)
        link = v1_fix_link(pj, inner.dir)
        assert os.path.realpath(os.path.join(link, "mod_a.py")) == os.path.realpath(os.path.join(inner.dir, "mod_a.py"))
        for command in ("cat %s/mod_a.py" % link, "sed -n 1,9p %s/mod_a.py" % link, "cat ../link/mod_a.py", "head -3 %s/./mod_a.py" % link):
            got = v1_fix_outcome(inner, req, command)
            assert got.get("verdict") == "accept", "%r resolves to the target's mod_a.py: %s" % (command, {k: got.get(k) for k in ("verdict", "answered", "unread")})
            v1_accept(got)
        for command in ("ls %s/mod_a.py" % link, "echo ../link/mod_a.py", "git diff -- %s/mod_a.py" % link, "cat %s/mod_a.py.orig" % link, "cat %s/pkg/mod_a.py" % link):
            v1_not_an_accept(v1_fix_outcome(inner, req, command), ["mod_a.py"])
        v1_not_an_accept(v1_fix_outcome(inner, req, "cat %s/mod_a.py" % link, 1), ["mod_a.py"])
        got = v1_answer(inner, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read(link + "/mod_a.py"), v1_said()])
        assert got.get("verdict") == "accept", "a Read by the symlinked absolute path opens the file: %s" % {k: got.get(k) for k in ("verdict", "answered", "unread")}
        v1_accept(got)


def test_V1_fix_a_read_of_a_dot_slash_path_still_opens_it_and_agrees_with_the_command_rule():
    """The Read/Grep branch keeps its behaviour — a relative path normalized, an absolute one by real path — and the two branches
    now say the same of the same spelling: `./mod_a.py` opens mod_a.py whether Read or cat'd; `./pkg/mod_a.py` does not, either way."""
    with Project() as pj:
        req = v1_project(pj)
        write(os.path.join(pj.dir, "pkg", "mod_a.py"), "other = 'another file'\n")
        v1_accept(v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read("./mod_a.py"), v1_said()]))
        v1_accept(v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read("pkg/../mod_a.py"), v1_said()]))
        v1_accept(v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read(pj.dir + "/./mod_a.py"), v1_said()]))
        v1_accept(v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_tool("Grep", pattern="keep", path="./mod_a.py"), v1_said()]))
        v1_not_an_accept(v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read("./pkg/mod_a.py"), v1_said()]), ["mod_a.py"])
        v1_not_an_accept(v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read("./mod_a.pyc"), v1_said()]), ["mod_a.py"])
        for spelling in ("./mod_a.py", "pkg/../mod_a.py", pj.dir + "/./mod_a.py"):
            by_read = v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read(spelling), v1_said()])
            by_command = v1_fix_outcome(pj, req, "cat " + spelling)
            assert by_read.get("verdict") == by_command.get("verdict") == "accept", (spelling, by_read.get("verdict"), by_command.get("verdict"))
        for spelling in ("./pkg/mod_a.py", "./mod_a.pyc"):
            by_read = v1_answer(pj, req, [v1_read("mod_b.py"), v1_read("mod_c.py"), v1_read(spelling), v1_said()])
            by_command = v1_fix_outcome(pj, req, "cat " + spelling)
            assert by_read.get("verdict") is None and by_command.get("verdict") is None, (spelling, by_read.get("verdict"), by_command.get("verdict"))


def test_V1_fix_unread_touched_resolves_a_command_word_as_a_path_relative_to_the_target():
    """unread_touched on the packet itself, with a hand-built read of commands only: `cat ./mod_a.py`, `head -3 pkg/../mod_a.py`
    and `cat <target>/./mod_a.py` leave mod_b.py and mod_c.py unread and nothing else; `cat ../mod_a.py` (the parent's real file),
    `cat ./pkg/mod_a.py`, `cat ./mod_a.pyc` and `git diff -- ./mod_a.py` leave all three."""
    assert callable(getattr(w, "unread_touched", None)), "eyes_worker.unread_touched is missing"
    with Project() as pj:
        inner, parent_file = v1_fix_nested(pj)
        req = v1_project(inner)
        made(os.path.join(inner.dir, "pkg"))
        packet = dwitbuk.verify_packet(req)
        assert packet.get("must_open") == ["mod_a.py", "mod_b.py", "mod_c.py"]
        def ut(*commands, exit_code=0):
            return w.unread_touched({"files": [], "commands": [{"command": c, "exit": exit_code} for c in commands]}, packet)
        assert ut() == ["mod_a.py", "mod_b.py", "mod_c.py"]
        for command in ("cat ./mod_a.py", "sed -n 1,9p ./mod_a.py", "head -3 pkg/../mod_a.py", "cat %s/./mod_a.py" % inner.dir, "cat %s/pkg/../mod_a.py" % os.path.realpath(inner.dir),
                        "cat ../proj/mod_a.py", "git diff -- ./mod_a.py && cat ./mod_a.py"):
            assert ut(command) == ["mod_b.py", "mod_c.py"], "%r opens mod_a.py: unread %r" % (command, ut(command))
        assert ut("cat ./mod_a.py", "cat ./mod_b.py", "head -3 ./pkg/../mod_c.py") == []
        for command in ("cat ../mod_a.py", "cat %s" % parent_file, "cat ./pkg/mod_a.py", "cat ./mod_a.pyc", "cat old_mod_a.py", "cat mod_a.py.orig",
                        "git diff -- ./mod_a.py", "ls ./mod_a.py", "echo ./mod_a.py", "echo pkg/../mod_a.py"):
            assert ut(command) == ["mod_a.py", "mod_b.py", "mod_c.py"], "%r does not open mod_a.py: unread %r" % (command, ut(command))
        assert ut("cat ./mod_a.py", exit_code=1) == ["mod_a.py", "mod_b.py", "mod_c.py"], "a failed command opened nothing"
        assert ut("cat ./mod_a.py", exit_code=None) == ["mod_b.py", "mod_c.py"], "exit None: it ran"


def test_V2_verify_packet_holds_no_diff_of_another_tasks_excluded_record():
    """D2-1: the 11-09 reproduction — `excluded` names the other task's record (today's list, without .chongdae/), there is no
    `excluded_diff`, and none of that record's changed text is anywhere in the packet; a record path also in `touched` keeps
    its diff in `diff`. D2-3: path_diff stays, for the late-eyes request."""
    with Project() as pj:
        req = v2_project(pj)
        p = dwitbuk.verify_packet(req)
        assert p["excluded"] == ["mangsang/relations/R-other.json", "mangsang/relations/R-mine.json"], p["excluded"]
        assert "excluded_diff" not in p, sorted(p)
        text = json.dumps(p, ensure_ascii=False)
        assert "other-task-new-relation" not in text and "other-task-old-relation" not in text, text
        assert "R-other" in text, "the name stays: the eyes know the file differs from HEAD and was left out by rule"
        assert '-{"id": "R-mine", "v": "my-old-relation"}' in p["diff"] and '+{"id": "R-mine", "v": "my-new-relation"}' in p["diff"], p["diff"]
        assert "-src_a = 'before'" in p["diff"] and "+src_a = 'after'" in p["diff"], p["diff"]
        assert p["touched"] == ["src/a.py", "mangsang/relations/R-mine.json"]
        # the other task's record alone in excluded, nothing touched: the name, no text
        q = dwitbuk.verify_packet(dict(req, touched=[], excluded={"record-paths": ["mangsang/relations/R-other.json"]}))
        assert q["excluded"] == ["mangsang/relations/R-other.json"] and "excluded_diff" not in q and q["diff"] == "", q
        assert "other-task-new-relation" not in json.dumps(q, ensure_ascii=False)
        # path_diff is unchanged: the late-eyes request still reads a record's diff through it
        pd = dwitbuk.path_diff(pj.dir, ["mangsang/relations/R-other.json"], ("HEAD",), cut=40000)
        assert '+{"id": "R-other", "v": "other-task-new-relation"}' in pd and "R-mine" not in pd, pd


def test_V2_instructions_say_excluded_files_are_not_this_tasks_changes_and_name_no_excluded_diff():
    """D2-2: with `excluded` the instructions say those files are not this task's changes and may be another open task's,
    that the packet holds none of their changes, not an undeclared edit, no record-vs-tree finding, not verified here; the
    2.2.x sentence reading `excluded_diff` as the slice's work is gone. Without `excluded`, nothing of it."""
    with Project() as pj:
        req = v2_project(pj)
        instr = dwitbuk.verify_packet(req)["instructions"]
        assert "`excluded`" in instr, instr
        assert "not this task's changes" in instr, instr
        assert "another open task" in instr, instr
        assert "none of their changes" in instr, instr
        assert "undeclared edit" in instr and "no record-vs-tree finding" in instr, instr
        assert "excluded_diff" not in instr, instr
        assert "as the slice's work" not in instr, instr
        bare = dwitbuk.verify_packet(dict(req, excluded={"record-paths": [".chongdae/run-1/state.json"]}))
        assert "excluded" not in bare and "`excluded`" not in bare["instructions"] and "excluded_diff" not in bare["instructions"], bare["instructions"]


# --- D3: a live-tree eyes packet is bound to what it quoted, not to every record ---------------------------------------------

D3_RUN = "run-20261106-000001-d3d3"


def session_run(pj, rid, tasks, status="running", goal=None):
    """A chongdae 2.1.0 session run: plan.json with no tasks, state.json, and one file per task under tasks/."""
    root = os.path.join(pj.dir, ".chongdae", rid)
    write(os.path.join(root, "plan.json"), {"artifact-type": "chongdae/plan@1", "kind": "session", "goal": goal or "goal of " + rid, "tasks": []})
    write(os.path.join(root, "state.json"), {"status": status, "tasks": {}, "non-claims": []})
    for tid, st in tasks.items():
        write(os.path.join(root, "tasks", tid + ".json"),
              {"def": {"id": tid, "role": "implementer", "brief": "brief of " + tid, "checks": [["python3", "t.py"]]}, **st})


def d3_project(pj):
    """An open session run: task `eyes` (todo, the one running the eyes) and a done task with a non-claim; a review to add to."""
    run("review", "--target", pj.dir)
    session_run(pj, D3_RUN, {"eyes": {"status": "todo"},
                             "built": {"status": "done", "touched": ["a.py"], "confirmed": {"by": "verifier"}, "attempts": 1,
                                       "non-claims": ["no check decides the wording"]}})


def d3_task_path(pj, tid, rid=D3_RUN):
    return os.path.join(pj.dir, ".chongdae", rid, "tasks", tid + ".json")


def d3_edit(path, change):
    doc = dwitbuk.load(path)
    change(doc)
    write(path, doc)


def append_did(pj, tid="eyes", rid=D3_RUN):
    """What chongdae records of the eyes call itself, appended to the task's file (the same second)."""
    d3_edit(d3_task_path(pj, tid, rid), lambda t: t.setdefault("did", []).append(
        {"command": "python3 eyes_worker.py --request .dwitbuk/packet/eyes-request.json --response .dwitbuk/packet/eyes-response.json", "exit": 0}))


def d3_taken(pj, folder, name):
    code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
    assert code == 0 and "source changed" not in out, out
    assert any(f["kind"] == "anomaly" and name in f["text"] for f in pj.latest()["findings"]), (out, pj.latest()["findings"])


def test_D3_a_did_chongdae_appends_to_the_eyes_task_during_the_call_does_not_stale_the_packet():
    with Project() as pj:
        d3_project(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder, "d3-did")
        assert any(r["run"] == D3_RUN for r in packet["runs"]), "the open run is packed"
        append_did(pj)
        d3_taken(pj, folder, "d3-did")


def test_D3_a_new_task_with_its_own_non_claims_and_a_new_run_during_the_call_do_not_stale_the_packet():
    with Project() as pj:
        d3_project(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder, "d3-new")
        write(d3_task_path(pj, "later"), {"def": {"id": "later", "role": "implementer", "brief": "added after", "checks": []},
                                          "status": "todo", "non-claims": ["no check decides this task; done means the agent said so"]})
        session_run(pj, "run-20261106-000002-eeee", {"other": {"status": "todo"}})
        append_did(pj)
        d3_taken(pj, folder, "d3-new")


def d3_refusals():
    """(what changed, the change) — each a change to something the packet carries, or to the source."""
    def task(tid, change):
        return lambda pj: d3_edit(d3_task_path(pj, tid), change)
    def state(change):
        return lambda pj: d3_edit(os.path.join(pj.dir, ".chongdae", D3_RUN, "state.json"), change)
    def plan(change):
        return lambda pj: d3_edit(os.path.join(pj.dir, ".chongdae", D3_RUN, "plan.json"), change)
    return [
        ("the done task's status", task("built", lambda t: t.update(status="failed"))),
        ("a packed task's brief", task("built", lambda t: t["def"].update(brief="another brief"))),
        ("a packed task's checks", task("eyes", lambda t: t["def"].update(checks=[]))),
        ("a packed task's touched", task("built", lambda t: t.update(touched=["a.py", "b.py"]))),
        ("a packed task's confirmed", task("built", lambda t: t.update(confirmed={"by": "someone else"}))),
        ("a packed task-state field added", task("eyes", lambda t: t.update(accepted={"by": "kim"}))),
        ("the run's status", state(lambda s: s.update(status="complete"))),
        ("the run's goal", plan(lambda p: p.update(goal="another goal"))),
        ("a packed non-claim removed", task("built", lambda t: t.update({"non-claims": []}))),
        ("a packed task gone", lambda pj: os.unlink(d3_task_path(pj, "built"))),
        ("a packed run gone", lambda pj: shutil.rmtree(os.path.join(pj.dir, ".chongdae", D3_RUN))),
        ("a source file", lambda pj: write(os.path.join(pj.dir, "a.py"), "x = 7\n")),
    ]


def test_D3_a_change_to_what_the_packet_carries_or_to_the_source_is_still_refused_beside_a_did():
    # the rule tells the two apart: a `did` alone is taken ...
    with Project() as pj:
        d3_project(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder, "d3-control")
        append_did(pj)
        d3_taken(pj, folder, "d3-control")
    # ... and a `did` beside a change to anything packed is refused, the review untouched
    for what, change in d3_refusals():
        with Project() as pj:
            d3_project(pj)
            folder = os.path.join(pj.dir, ".dwitbuk", "packet")
            eyes_answer(pj, folder, "d3-refused")
            before = pj.latest()
            append_did(pj)
            change(pj)
            code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
            assert code != 0 and "source changed" in out, (what, out)
            assert pj.latest() == before, what


def d3_worker(pj, folder, during=None):
    """eyes_worker.main on the packet in folder with a patched host; `during` runs inside the host call. Returns (host called, error)."""
    from unittest.mock import patch
    response = os.path.join(folder, "eyes-response.json")
    if os.path.exists(response):
        os.unlink(response)
    called = []
    def host(packet, schema, args):
        called.append(True)
        if during:
            during(pj)
        return {"findings": [{"kind": "anomaly", "where": "a.py", "tree_quote": "x = 1", "record_quote": "", "why": "d3-worker"}]}
    with patch.object(w, "claude", host), patch.object(sys, "argv", ["eyes_worker.py", "--request", os.path.join(folder, "eyes-request.json"), "--response", response]), \
            contextlib.redirect_stdout(io.StringIO()):
        try:
            w.main()
            return bool(called), None
        except SystemExit as err:
            return bool(called), str(err)


def test_D3_the_worker_saves_its_answer_when_chongdae_writes_a_did_during_the_host_call():
    with Project() as pj:
        d3_project(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder, "unused")
        called, err = d3_worker(pj, folder, during=append_did)
        response = os.path.join(folder, "eyes-response.json")
        assert called and err is None and os.path.exists(response), err
        assert dwitbuk.load(response).get("request") == dwitbuk.fingerprint(packet)
        d3_taken(pj, folder, "d3-worker")


def test_D3_the_worker_refuses_a_packed_change_before_and_after_its_host_call_by_the_same_rule():
    response_of = lambda folder: os.path.join(folder, "eyes-response.json")
    with Project() as pj:
        d3_project(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder, "unused")
        append_did(pj)   # before the call: taken
        called, err = d3_worker(pj, folder, during=lambda p: append_did(p))
        assert called and err is None and os.path.exists(response_of(folder)), err
    with Project() as pj:
        d3_project(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder, "unused")
        append_did(pj)
        d3_edit(d3_task_path(pj, "built"), lambda t: t.update(status="failed"))   # before the call: refused, the host never asked
        called, err = d3_worker(pj, folder)
        assert not called and err and "source changed" in err and not os.path.exists(response_of(folder)), (called, err)
    with Project() as pj:
        d3_project(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder, "unused")
        def during(p):
            append_did(p)
            d3_edit(d3_task_path(p, "built"), lambda t: t["def"].update(brief="rewritten during the call"))
        called, err = d3_worker(pj, folder, during=during)
        assert called and err and "source changed" in err and not os.path.exists(response_of(folder)), (called, err)


def test_D3_a_packet_bound_the_2_1_0_way_keeps_the_whole_records_rule():
    with Project() as pj:
        d3_project(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder, "d3-new-style")
        append_did(pj)
        d3_taken(pj, folder, "d3-new-style")   # bound the new way, a `did` is taken
    with Project() as pj:
        d3_project(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder, "d3-old-style")
        src = packet["source"]
        # what dwitbuk 2.1.0 wrote: no `review`, `records: true`, the digest over the tree and every run's whole record
        packet["source"] = {"output": src["output"], "extra": src.get("extra", []), "records": True,
                            "digest": dwitbuk.source_state(pj.dir, src["output"], src.get("extra", []), True)}
        write(os.path.join(folder, "eyes-request.json"), packet)
        write(os.path.join(folder, "eyes-response.json"), {"request": dwitbuk.fingerprint(packet), "findings": [
            {"kind": "anomaly", "where": "a.py", "tree_quote": "d3-old-style", "record_quote": "", "why": "d3-old-style"}]})
        d3_taken(pj, folder, "d3-old-style")   # the hand-bound packet is a valid binding ...
        append_did(pj)
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code != 0 and "source changed" in out, out   # ... and a `did` stales it, as in 2.1.0


# --- D4: consume never rewrites a closed run's close review ------------------------------------------------------------------

D4_CHARGES = [{"kind": "contradiction", "where": "run-1/T: a.py", "text": "d4 charge one"},
              {"kind": "stale", "where": "rel-7", "text": "d4 charge two"}]
D4_OBSERVATION = {"kind": "delegated", "where": "R-1 a.py realizes concept:x", "text": "d4 observation"}


def d4_reporter(pj, fixed):
    """A reporter that says the given findings and, for each file committed since --since, an outside-run."""
    script = os.path.join(pj.dir, ".dwitbuk", "d4rep.py")   # under a record directory: rewriting the reporter is no source change
    write(script, "import json, os, subprocess, sys\n"
                  "since = sys.argv[sys.argv.index('--since') + 1]\n"
                  "here = os.path.dirname(os.path.abspath(__file__))\n"
                  "names = subprocess.run(['git', 'diff', '--name-only', since, 'HEAD'], cwd=here, capture_output=True, text=True).stdout.split()\n"
                  "fixed = json.loads(%r)\n"
                  "print(json.dumps({'artifact-type': 'dwitbuk/findings@1', 'source': 'd4rep', 'findings': fixed + "
                  "[{'kind': 'outside-run', 'where': n, 'files': [n], 'text': 'changed; no run'} for n in names]}))\n" % json.dumps(fixed))
    lock = dwitbuk.load(os.path.join(pj.dir, "hunsu.lock.json"))
    lock["reporters"] = {"d4rep": [sys.executable, script, "--since", "{since}"]}
    write(os.path.join(pj.dir, "hunsu.lock.json"), lock)


def d4_close(pj, rid, review_id, status="complete"):
    """A run whose reviewer wrote review_id at its close, as chongdae 2.1.0 records it."""
    root = os.path.join(pj.dir, ".chongdae", rid)
    write(os.path.join(root, "plan.json"), {"artifact-type": "chongdae/plan@1", "kind": "session", "goal": "closed " + rid, "tasks": []})
    write(os.path.join(root, "state.json"), {"status": status, "tasks": {}, "non-claims": [],
                                            "reviewed": {"by": "reviewer", "said": "closed", "wrote": ["reviews/%s.json" % review_id], "at": "2026-11-06T04:00:00Z"}})


def review_bytes(pj, rid):
    with open(os.path.join(pj.dir, "reviews", rid + ".json"), "rb") as fh:
        return fh.read()


def d4_first_review(pj):
    d4_reporter(pj, D4_CHARGES + [D4_OBSERVATION])
    assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
    return pj.latest()


def assert_eyes_review(pj, new, of, latest, eyes_names):
    """new is the eyes review written for a packet bound to `of`, answering `latest`."""
    assert new["artifact-type"] == "dwitbuk/review@1" and new["id"] > latest["id"] and new["eyes-of"] == of, new
    assert new["since"] == latest["since"] and new["head"] == latest["head"], new
    fs = new["findings"]
    n = len(eyes_names)
    assert [f["kind"] for f in fs[:n]] == ["anomaly"] * n and all(any(name in f["text"] for f in fs[:n]) for name in eyes_names), fs
    open_ = [(i, f) for i, f in enumerate(latest["findings"]) if dwitbuk.layer(f) == "objection" and not f.get("disposition")]
    carried = fs[n:n + len(open_)]
    assert [f["kind"] for f in carried] == ["undisposed"] * len(open_), fs
    for c, (i, old) in zip(carried, open_):
        # raised in the latest review at its index; a charge the latest itself carried may keep where it was first raised
        allowed = {"%s/%d" % (latest["id"], i)} | ({old.get("raised-in")} if old.get("kind") == "undisposed" and old.get("raised-in") else set())
        assert c["raised-in"] in allowed and tuple(c["carries"]) == dwitbuk.charge(old), (c, old)
    rest = fs[n + len(open_):]
    # one `unchanged` line only when the latest review stands on observations (its own, or ones its `unchanged` lines count);
    # a latest review that stands on none gets none (the newer review of the bound-to-A case reports no observation)
    held = dwitbuk.carried_observations([r for r in dwitbuk.reviews(pj.dir) if r["id"] <= latest["id"]])
    if not held:
        assert rest == [], rest
        return
    assert len(rest) == 1 and rest[0]["kind"] == "unchanged" and rest[0]["seen-in"], rest
    assert {rid for _, rid in held.values()} <= set(rest[0]["seen-in"]), (rest[0]["seen-in"], held)
    assert re.match(r"%d observation" % len(held), rest[0]["text"]), rest[0]


def test_D4_consume_on_a_packet_bound_to_a_closed_review_writes_a_new_eyes_review_and_leaves_the_closed_one_as_it_was():
    import time
    with Project() as pj:
        closed = d4_first_review(pj)
        d4_close(pj, "run-20261106-000001-c105", closed["id"])
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder, "d4-eyes")
        assert packet["source"].get("review") == closed["id"], packet["source"]   # the binding names the latest review
        before = review_bytes(pj, closed["id"])
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code == 0, out
        assert review_bytes(pj, closed["id"]) == before, "a closed review's file is byte-for-byte as it was"
        new = pj.latest()
        assert new["id"] != closed["id"] and len(dwitbuk.reviews(pj.dir)) == 2, [r["id"] for r in dwitbuk.reviews(pj.dir)]
        assert_eyes_review(pj, new, closed["id"], closed, ["d4-eyes"])
        assert "added to %s" % new["id"] in out and closed["id"] in out.replace("added to %s" % new["id"], ""), out
        # follow: the old open charges once each, and the eyes finding
        code, out = run("follow", "--target", pj.dir)
        assert code == 1 and out.splitlines()[-1] == "undisposed findings: 3", out
        assert out.count("d4 charge one") == 1 and out.count("d4 charge two") == 1 and "d4-eyes" in out and "d4 observation" not in out, out
        # a disposal of a carried charge answers it, where it stands now
        i = next(i for i, f in enumerate(new["findings"]) if f["kind"] == "undisposed" and f["text"] == "d4 charge one")
        code, out = run("dispose", "%s/%d" % (new["id"], i), "--as", "dismissed", "--why", "fixed", "--by", "kim", "--target", pj.dir)
        assert code == 0, out
        assert run("follow", "--target", pj.dir)[1].splitlines()[-1] == "undisposed findings: 2"
        assert review_bytes(pj, closed["id"]) == before
        # a later review starts at the eyes review's head: a commit made after it shows, nothing lost
        write(os.path.join(pj.dir, "b.py"), "y = 1\n")
        git(pj.dir, "add", "b.py"); git(pj.dir, "commit", "-qm", "after the close")
        d4_reporter(pj, [])
        time.sleep(1.1)
        assert run("review", "--target", pj.dir)[0] == 0
        later = pj.latest()
        assert later["since"] == closed["head"], (later["since"], closed["head"])
        assert any(f["kind"] == "outside-run" and "b.py" in f["where"] for f in later["findings"]), later["findings"]
        texts = [f["text"] for f in later["findings"] if dwitbuk.layer(f) == "objection" and not f.get("disposition")]
        assert any("d4 charge two" in t for t in texts) and any("d4-eyes" in t for t in texts) and not any("d4 charge one" in t for t in texts), texts


def test_D4_consume_on_a_packet_bound_to_an_open_latest_review_appends_to_it_as_now():
    with Project() as pj:
        older = d4_first_review(pj)
        import time; time.sleep(1.1)
        assert run("review", "--target", pj.dir)[0] == 0
        latest = pj.latest()
        d4_close(pj, "run-20261106-000001-c105", older["id"])   # a completed run closed an older review, not this one
        d4_close(pj, "run-20261106-000002-0be7", latest["id"], status="running")   # not a completed run: does not close it
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder, "d4-open")
        assert packet["source"].get("review") == latest["id"], packet["source"]
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code == 0 and "added to %s" % latest["id"] in out, out
        assert len(dwitbuk.reviews(pj.dir)) == 2 and pj.latest()["id"] == latest["id"]
        assert any(f["kind"] == "anomaly" and "d4-open" in f["text"] for f in pj.latest()["findings"])


def test_D4_a_newer_review_written_before_consume_gets_a_new_eyes_review_naming_the_bound_one():
    import time
    with Project() as pj:
        a = d4_first_review(pj)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder, "d4-late")
        assert packet["source"].get("review") == a["id"], packet["source"]
        d4_reporter(pj, D4_CHARGES[1:])   # charge one stops recurring: B carries it; charge two is the reporter's again
        time.sleep(1.1)
        assert run("review", "--target", pj.dir)[0] == 0
        b = pj.latest()
        before = {r: review_bytes(pj, r) for r in (a["id"], b["id"])}
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code == 0, out
        assert {r: review_bytes(pj, r) for r in before} == before, "neither the bound review nor the newer one is rewritten"
        new = pj.latest()
        assert len(dwitbuk.reviews(pj.dir)) == 3 and new["id"] not in before, [r["id"] for r in dwitbuk.reviews(pj.dir)]
        assert_eyes_review(pj, new, a["id"], b, ["d4-late"])
        assert "added to %s" % new["id"] in out and a["id"] in out.replace("added to %s" % new["id"], ""), out


def test_D4_a_second_packet_bound_to_the_same_closed_review_appends_to_the_eyes_review_already_made():
    with Project() as pj:
        closed = d4_first_review(pj)
        d4_close(pj, "run-20261106-000001-c105", closed["id"])
        first, second, third = [os.path.join(pj.dir, ".dwitbuk", n) for n in ("first", "second", "third")]
        eyes_answer(pj, first, "d4-first")
        eyes_answer(pj, second, "d4-second")
        eyes_answer(pj, third, "d4-third")
        before = review_bytes(pj, closed["id"])
        assert run("eyes", "consume", "--dir", first, "--target", pj.dir)[0] == 0
        made = pj.latest()
        assert made["id"] != closed["id"] and made.get("eyes-of") == closed["id"], made.get("id")
        code, out = run("eyes", "consume", "--dir", second, "--target", pj.dir)
        assert code == 0 and "added to %s" % made["id"] in out, out
        ids = [r["id"] for r in dwitbuk.reviews(pj.dir)]
        assert ids == [closed["id"], made["id"]], ids   # no third review
        grown = pj.latest()
        assert grown["findings"][:len(made["findings"])] == made["findings"], "appended, as consume appends"
        added = grown["findings"][len(made["findings"]):]
        assert [f["kind"] for f in added] == ["anomaly"] and "d4-second" in added[0]["text"], added
        assert grown.get("eyes-of") == closed["id"] and grown["since"] == closed["since"] and grown["head"] == closed["head"], grown
        assert review_bytes(pj, closed["id"]) == before
        # nothing new kept (every finding rejected) writes no review
        write(os.path.join(third, "eyes-response.json"), {"request": dwitbuk.fingerprint(dwitbuk.load(os.path.join(third, "eyes-request.json"))),
                                                          "findings": [{"kind": "style", "where": "a.py", "tree_quote": "x", "record_quote": "y", "why": "no kind"}]})
        code, out = run("eyes", "consume", "--dir", third, "--target", pj.dir)
        assert [r["id"] for r in dwitbuk.reviews(pj.dir)] == ids and review_bytes(pj, closed["id"]) == before, out


def test_D4_nothing_new_kept_against_a_closed_review_writes_no_review():
    with Project() as pj:
        closed = d4_first_review(pj)
        d4_close(pj, "run-20261106-000001-c105", closed["id"])
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder, "unused")
        assert packet["source"].get("review") == closed["id"], packet["source"]
        write(os.path.join(folder, "eyes-response.json"), {"request": dwitbuk.fingerprint(packet), "findings": [
            {"kind": "style", "where": "a.py", "tree_quote": "x", "record_quote": "y", "why": "not a kind"}]})
        before = review_bytes(pj, closed["id"])
        run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert [r["id"] for r in dwitbuk.reviews(pj.dir)] == [closed["id"]] and review_bytes(pj, closed["id"]) == before


def test_D4_the_new_eyes_review_sorts_after_the_latest_within_the_same_second():
    import time
    with Project() as pj:
        first = d4_first_review(pj)
        # the latest review, renamed to this very second with the highest suffix there is
        late_id = "review-%s-ffff" % time.strftime("%Y%m%d-%H%M%S")
        os.rename(os.path.join(pj.dir, "reviews", first["id"] + ".json"), os.path.join(pj.dir, "reviews", late_id + ".json"))
        save_review(pj, dict(first, id=late_id))
        d4_close(pj, "run-20261106-000001-c105", late_id)
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        eyes_answer(pj, folder, "d4-same-second")
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code == 0, out
        ids = [r["id"] for r in dwitbuk.reviews(pj.dir)]
        assert len(ids) == 2 and ids[0] == late_id and ids[1] > late_id and pj.latest().get("eyes-of") == late_id, ids


# --- 11-06 D5: one host-aware resolver of `{plugin:NAME}` (plugin/pluginroot.py, vendored byte-identical by chongdae and jokbo).
# Every fixture is a temporary project and temporary host homes; `environ` is passed, so this machine's ~/.claude and ~/.codex
# are never read.

D5_KEYS = ("name", "root", "host", "via", "marketplace", "declared", "version", "note", "reason")


def pluginroot():
    """plugin/pluginroot.py, imported from the payload; its absence is a failed assertion, not an import error."""
    assert os.path.isfile(os.path.join(PLUGIN, "pluginroot.py")), "plugin/pluginroot.py does not exist"
    import importlib
    mod = importlib.import_module("pluginroot")
    assert callable(getattr(mod, "resolve", None)), "pluginroot.resolve is missing"
    return mod


class Hosts:
    """A temporary project (`target`) and temporary host homes: Claude Code's and Codex's, written as each host writes them."""

    def __init__(self):
        self.base = tempfile.mkdtemp(prefix="dwitbuk-d5-")
        self.target = made(os.path.join(self.base, "project"))   # under /var on macOS: its real path is /private/var/…
        self.claude = made(os.path.join(self.base, "claude-home"))
        self.codex = made(os.path.join(self.base, "codex-home"))
        self.installed = {}
        self.known = {}
        self.config = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        shutil.rmtree(self.base, ignore_errors=True)

    def env(self, host="claude-code", **extra):
        e = {"AGENT_HOST": host, "HUNSU_CLAUDE_DIR": self.claude, "HUNSU_CODEX_DIR": self.codex, "HOME": made(os.path.join(self.base, "home"))}
        e.update(extra)
        return {k: v for k, v in e.items() if v is not None}

    def resolve(self, name, host="claude-code", target=None, **extra):
        got = pluginroot().resolve(target or self.target, name, environ=self.env(host, **extra))
        assert isinstance(got, dict), got
        missing = [k for k in D5_KEYS if k not in got]
        assert not missing, ("resolve() result lacks keys", missing, got)
        return got

    def os_environ(self, host):
        """For what reads os.environ (dwitbuk.plugin_root, a review): this host and these homes, the fallbacks unset."""
        return environ(AGENT_HOST=host, HUNSU_CLAUDE_DIR=self.claude, HUNSU_CODEX_DIR=self.codex,
                       CLAUDE_CONFIG_DIR=None, AGENT_CODEX_HOME=None, CODEX_HOME=None)

    def declare(self, name, marketplace=None, version=None):
        doc = dwitbuk.load(os.path.join(self.target, "hunsu.json")) if os.path.isfile(os.path.join(self.target, "hunsu.json")) else {}
        entry = {k: v for k, v in (("marketplace", marketplace), ("version", version)) if v is not None}
        doc.setdefault("plugins", {})[name] = entry
        write(os.path.join(self.target, "hunsu.json"), doc)

    def local(self, doc):
        write(os.path.join(self.target, "hunsu.local.json"), doc)

    def claude_install(self, name, market, version, scope="user", project=None, exists=True, manifest=True):
        path = os.path.join(self.claude, "plugins", "cache", market, name, version)
        if exists:
            made(path)
            if manifest:
                write(os.path.join(path, ".claude-plugin", "plugin.json"), {"name": name, "version": version})
        entry = {"scope": scope, "installPath": path, "version": version}
        if project is not None:
            entry["projectPath"] = project
        self.installed.setdefault("%s@%s" % (name, market), []).append(entry)
        write(os.path.join(self.claude, "plugins", "installed_plugins.json"), {"version": 2, "plugins": self.installed})
        return path

    def claude_directory_market(self, market, path):
        self.known[market] = {"source": {"source": "directory", "path": path}, "installLocation": path}
        write(os.path.join(self.claude, "plugins", "known_marketplaces.json"), self.known)

    def codex_install(self, name, market, version, enabled=True, manifest=".codex-plugin", configured=True):
        path = made(os.path.join(self.codex, "plugins", "cache", market, name, version))
        if manifest:
            write(os.path.join(path, manifest, "plugin.json") if manifest != "flat" else os.path.join(path, "plugin.json"),
                  {"name": name, "version": version})
        if configured:
            self.config["%s@%s" % (name, market)] = enabled
        self.write_config()
        return path

    def write_config(self):
        text = 'model = "x"\n\n' + "".join('[plugins."%s"]\nenabled = %s\n\n' % (k, "true" if v else "false") for k, v in self.config.items())
        write(os.path.join(self.codex, "config.toml"), text)


def plugin_dir(path, name, version="1.0.0", kind=".claude-plugin"):
    """A plugin payload at `path`: its manifest names it."""
    write(os.path.join(path, kind, "plugin.json") if kind else os.path.join(path, "plugin.json"), {"name": name, "version": version})
    return path


def test_D5_pluginroot_is_a_stdlib_only_module_in_the_payload_with_resolve():
    import ast, inspect
    mod = pluginroot()
    src = open(os.path.join(PLUGIN, "pluginroot.py"), encoding="utf-8").read()
    names = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "a relative import: pluginroot is vendored alone"
            names.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) in ("__import__", "import_module"):
            raise AssertionError("pluginroot imports by name at run time; it must import only the standard library")
    foreign = sorted(n for n in names if n not in sys.stdlib_module_names)
    assert not foreign, ("pluginroot imports outside the standard library", foreign)
    params = list(inspect.signature(mod.resolve).parameters.values())
    assert [p.name for p in params[:3]] == ["target", "name", "environ"] and params[2].default is None, params


def test_D5_the_host_is_codex_only_for_AGENT_HOST_codex():
    with Hosts() as h:
        h.declare("probe", "m")
        for host, want in (("codex", "codex"), ("claude-code", "claude-code"), ("claude", "claude-code"), ("", "claude-code"),
                           ("CODEX", "claude-code"), (None, "claude-code")):
            got = h.resolve("probe", host=host)
            assert got["host"] == want and got["name"] == "probe", (host, got)


def test_D5_environ_defaults_to_os_environ():
    with Hosts() as h:
        h.declare("probe", "m")
        path = h.codex_install("probe", "m", "1.0.0")
        mod = pluginroot()
        with environ(AGENT_HOST="codex", HUNSU_CLAUDE_DIR=h.claude, HUNSU_CODEX_DIR=h.codex):
            got = mod.resolve(h.target, "probe")
        assert got["host"] == "codex" and same(got["root"], path), got
        with environ(AGENT_HOST="claude-code", HUNSU_CLAUDE_DIR=h.claude, HUNSU_CODEX_DIR=h.codex):
            got = mod.resolve(h.target, "probe")
        assert got["host"] == "claude-code" and got["root"] is None, got


def test_D5_host_homes_follow_their_variables_in_order():
    with Hosts() as h:
        h.declare("probe", "m")
        # Claude Code: HUNSU_CLAUDE_DIR, else CLAUDE_CONFIG_DIR
        other = made(os.path.join(h.base, "claude-config"))
        path = h.claude_install("probe", "m", "1.0.0")
        got = h.resolve("probe", HUNSU_CLAUDE_DIR=None, CLAUDE_CONFIG_DIR=h.claude)
        assert same(got["root"], path), ("CLAUDE_CONFIG_DIR is the Claude home without HUNSU_CLAUDE_DIR", got)
        got = h.resolve("probe", CLAUDE_CONFIG_DIR=other)
        assert same(got["root"], path), ("HUNSU_CLAUDE_DIR wins over CLAUDE_CONFIG_DIR", got)
        got = h.resolve("probe", HUNSU_CLAUDE_DIR=other, CLAUDE_CONFIG_DIR=h.claude)
        assert got["root"] is None, ("HUNSU_CLAUDE_DIR wins over CLAUDE_CONFIG_DIR", got)
        # Codex: HUNSU_CODEX_DIR, else AGENT_CODEX_HOME, else CODEX_HOME
        empty = made(os.path.join(h.base, "codex-empty"))
        cpath = h.codex_install("probe", "m", "1.0.0")
        assert same(h.resolve("probe", "codex", HUNSU_CODEX_DIR=None, AGENT_CODEX_HOME=h.codex, CODEX_HOME=empty)["root"], cpath), \
            "AGENT_CODEX_HOME before CODEX_HOME"
        assert same(h.resolve("probe", "codex", HUNSU_CODEX_DIR=None, CODEX_HOME=h.codex)["root"], cpath), "CODEX_HOME last"
        assert h.resolve("probe", "codex", HUNSU_CODEX_DIR=None, AGENT_CODEX_HOME=empty, CODEX_HOME=h.codex)["root"] is None, \
            "AGENT_CODEX_HOME before CODEX_HOME"
        assert h.resolve("probe", "codex", HUNSU_CODEX_DIR=empty, AGENT_CODEX_HOME=h.codex)["root"] is None, "HUNSU_CODEX_DIR first"


def test_D5_codex_only_install_resolves_on_codex_and_not_on_claude_code():
    with Hosts() as h:
        h.declare("probe", "m", "1.0.0")
        path = h.codex_install("probe", "m", "1.0.0")
        got = h.resolve("probe", "codex")
        assert same(got["root"], path) and got["host"] == "codex" and got["via"] == "install", got
        assert got["marketplace"] == "m" and got["declared"] == "1.0.0" and got["version"] == "1.0.0" and got["note"] is None, got
        got = h.resolve("probe", "claude-code")
        assert got["root"] is None and got["host"] == "claude-code", ("never the other host's copy", got)
        assert "not installed for it here" in (got["reason"] or ""), got


def test_D5_claude_only_install_resolves_on_claude_code_and_not_on_codex():
    with Hosts() as h:
        h.declare("probe", "m", "1.0.0")
        path = h.claude_install("probe", "m", "1.0.0")
        got = h.resolve("probe", "claude-code")
        assert same(got["root"], path) and got["via"] == "install" and got["marketplace"] == "m" and got["version"] == "1.0.0", got
        got = h.resolve("probe", "codex")
        assert got["root"] is None and got["host"] == "codex" and "not installed for it here" in (got["reason"] or ""), got


def test_D5_both_hosts_installed_each_gets_its_own_copy():
    with Hosts() as h:
        h.declare("probe", "m")
        cl = h.claude_install("probe", "m", "1.0.0")
        cx = h.codex_install("probe", "m", "1.0.0")
        assert same(h.resolve("probe", "claude-code")["root"], cl)
        assert same(h.resolve("probe", "codex")["root"], cx)
        h.declare("probe", None)   # undeclared too: each host's own installs only
        assert same(h.resolve("probe", "claude-code")["root"], cl)
        assert same(h.resolve("probe", "codex")["root"], cx)


def test_D5_the_same_name_in_two_marketplaces():
    with Hosts() as h:
        for host, install in (("claude-code", h.claude_install), ("codex", h.codex_install)):
            h.config.clear(); h.installed.clear()
            a = install("probe", "alpha", "1.0.0")
            b = install("probe", "beta", "1.0.0")
            h.declare("probe", "alpha")
            got = h.resolve("probe", host)
            assert same(got["root"], a) and got["marketplace"] == "alpha", (host, got)
            h.declare("probe", "beta")
            assert same(h.resolve("probe", host)["root"], b), host
            h.declare("probe", "gamma")   # declared, absent; the others present: no root, never another marketplace's
            got = h.resolve("probe", host)
            assert got["root"] is None and "not installed for it here" in (got["reason"] or ""), (host, got)
            h.declare("probe", None)   # undeclared, two marketplaces: ambiguous, the reason names them
            got = h.resolve("probe", host)
            assert got["root"] is None and "alpha" in (got["reason"] or "") and "beta" in got["reason"], (host, got)


def test_D5_declared_marketplace_absent_but_another_present_gives_no_root():
    with Hosts() as h:
        h.declare("probe", "mine")
        h.claude_install("probe", "theirs", "1.0.0")
        h.codex_install("probe", "theirs", "1.0.0")
        for host in ("claude-code", "codex"):
            got = h.resolve("probe", host)
            assert got["root"] is None and "not installed for it here" in (got["reason"] or ""), (host, got)


def test_D5_an_undeclared_plugin_from_one_marketplace_is_that_copy():
    with Hosts() as h:
        cl = h.claude_install("probe", "solo", "1.2.0")
        cx = h.codex_install("probe", "solo", "1.2.0")
        for host, path in (("claude-code", cl), ("codex", cx)):
            got = h.resolve("probe", host)
            assert same(got["root"], path) and got["marketplace"] == "solo" and got["declared"] is None, (host, got)
            assert got["version"] == "1.2.0" and got["note"] is None, (host, got)
        got = h.resolve("nothing", "claude-code")   # undeclared and not installed: no root, a reason
        assert got["root"] is None and got["reason"], got
        got = h.resolve("nothing", "codex")
        assert got["root"] is None and got["reason"], got


def test_D5_an_undeclared_plugin_skips_installs_of_other_projects():
    with Hosts() as h:
        h.claude_install("probe", "elsewhere", "1.0.0", scope="project", project="/some/other/project")
        mine = h.claude_install("probe", "here", "1.0.0", scope="project", project=os.path.realpath(h.target))
        got = h.resolve("probe")
        assert same(got["root"], mine) and got["marketplace"] == "here", ("only installs that apply to this target count", got)


def test_D5_a_version_differing_from_the_pin_returns_root_and_a_note_with_both():
    with Hosts() as h:
        h.declare("probe", "m", "1.0.0")
        cl = h.claude_install("probe", "m", "1.3.0")
        cx = h.codex_install("probe", "m", "1.4.0")
        for host, path, found in (("claude-code", cl, "1.3.0"), ("codex", cx, "1.4.0")):
            got = h.resolve("probe", host)
            assert same(got["root"], path) and got["declared"] == "1.0.0" and got["version"] == found, (host, got)
            assert got["note"] and "1.0.0" in got["note"] and found in got["note"], ("the note names both versions", host, got)


def test_D5_the_version_is_read_from_any_plugin_manifest():
    with Hosts() as h:
        h.declare("probe", "m")
        for kind in ("flat", ".claude-plugin", ".codex-plugin"):
            shutil.rmtree(os.path.join(h.codex, "plugins"), ignore_errors=True)
            path = h.codex_install("probe", "m", "3.%d.0" % len(kind), manifest=kind)
            got = h.resolve("probe", "codex")
            assert same(got["root"], path) and got["version"] == "3.%d.0" % len(kind), (kind, got)


def test_D5_several_codex_versions_take_the_declared_one_else_none():
    with Hosts() as h:
        h.codex_install("probe", "m", "1.0.0")
        two = h.codex_install("probe", "m", "1.1.0")
        h.declare("probe", "m", "1.1.0")
        got = h.resolve("probe", "codex")
        assert same(got["root"], two) and got["version"] == "1.1.0" and got["note"] is None, got
        for version in (None, "2.0.0"):   # none declared, or none matching: ambiguous, the reason lists the versions
            h.declare("probe", "m", version)
            got = h.resolve("probe", "codex")
            assert got["root"] is None and "1.0.0" in (got["reason"] or "") and "1.1.0" in got["reason"], (version, got)


def test_D5_a_codex_version_directory_without_a_manifest_is_not_a_version():
    with Hosts() as h:
        h.declare("probe", "m")
        one = h.codex_install("probe", "m", "1.0.0")
        h.codex_install("probe", "m", "0.9.0", manifest=None)   # a leftover directory: no plugin manifest
        got = h.resolve("probe", "codex")
        assert same(got["root"], one) and got["version"] == "1.0.0", got


def test_D5_a_codex_plugin_not_enabled_is_not_installed():
    with Hosts() as h:
        h.declare("probe", "m")
        h.codex_install("probe", "m", "1.0.0", enabled=False)
        got = h.resolve("probe", "codex")
        assert got["root"] is None and "not installed for it here" in (got["reason"] or ""), got
        h.declare("probe", None)
        assert h.resolve("probe", "codex")["root"] is None
        h.config.clear(); h.write_config()   # in the cache but not in config.toml at all
        h.declare("probe", "m")
        assert h.resolve("probe", "codex")["root"] is None


def test_D5_a_claude_install_path_that_no_longer_exists_is_no_install():
    with Hosts() as h:
        h.declare("probe", "m")
        h.claude_install("probe", "m", "1.0.0", exists=False)
        got = h.resolve("probe")
        assert got["root"] is None and "not installed for it here" in (got["reason"] or ""), got
        h.declare("probe", None)
        assert h.resolve("probe")["root"] is None


def test_D5_claude_scope_order_local_then_project_for_this_target_then_user():
    with Hosts() as h:
        h.declare("probe", "m")
        real = os.path.realpath(h.target)
        user = h.claude_install("probe", "m", "1.0.0", scope="user")
        h.claude_install("probe", "m", "1.1.0", scope="project", project="/another/project")
        assert same(h.resolve("probe")["root"], user), "another project's entry does not apply here"
        proj = h.claude_install("probe", "m", "1.2.0", scope="project", project=real)   # by real path
        assert same(h.resolve("probe")["root"], proj)
        h.claude_install("probe", "m", "1.3.0", scope="local", project="/another/project")
        assert same(h.resolve("probe")["root"], proj), "another project's local entry does not apply here"
        loc = h.claude_install("probe", "m", "1.4.0", scope="local", project=real)
        assert same(h.resolve("probe")["root"], loc)


def test_D5_a_claude_directory_marketplace_is_used_in_place():
    with Hosts() as h:
        market = os.path.join(h.base, "dir-market")
        payload = plugin_dir(os.path.join(market, "plugin"), "probe")
        write(os.path.join(market, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "probe", "source": "./plugin"}]})
        h.claude_directory_market("dev", market)
        h.claude_install("probe", "dev", "1.0.0")   # the copy the host made: nothing runs it
        h.declare("probe", "dev")
        got = h.resolve("probe")
        assert same(got["root"], payload) and got["via"] == "directory-marketplace", got
        nested = os.path.join(h.base, "folder-market")
        inner = plugin_dir(os.path.join(nested, "probe"), "probe", kind=None)
        h.claude_directory_market("dev", nested)
        got = h.resolve("probe")
        assert same(got["root"], inner) and got["via"] == "directory-marketplace", got
        got = h.resolve("probe", "codex")   # Claude Code's directory marketplace is not Codex's install
        assert got["root"] is None, got


def test_D5_a_stale_link_gives_no_root_and_its_reason_even_with_an_install():
    with Hosts() as h:
        h.declare("probe", "m")
        h.claude_install("probe", "m", "1.0.0")
        h.codex_install("probe", "m", "1.0.0")
        gone = os.path.join(h.base, "gone-checkout")
        h.local({"links": {"probe": gone}})
        for host in ("claude-code", "codex"):
            got = h.resolve("probe", host)
            assert got["root"] is None, ("a stale link never falls through to an install", host, got)
            assert got["reason"] and ("gone-checkout" in got["reason"]), ("the reason names the link", host, got)
        h.local({"links": {"probe": "../gone-relative"}})
        got = h.resolve("probe")
        assert got["root"] is None and "gone-relative" in (got["reason"] or ""), got


def test_D5_a_link_resolves_relative_to_the_target_through_its_catalog():
    with Hosts() as h:
        h.declare("probe", "m")
        h.claude_install("probe", "m", "1.0.0")   # a link wins over an install
        co = os.path.join(h.base, "checkout")
        payload = plugin_dir(os.path.join(co, "plugin"), "probe")
        write(os.path.join(co, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "probe", "source": "./plugin"}]})
        h.local({"links": {"probe": "../checkout"}})
        for host in ("claude-code", "codex"):
            got = h.resolve("probe", host)
            assert same(got["root"], payload) and got["via"] == "link" and got["host"] == host, (host, got)
        cx = os.path.join(h.base, "codex-checkout")
        cpayload = plugin_dir(os.path.join(cx, "plugin"), "probe", kind=".codex-plugin")
        write(os.path.join(cx, ".agents", "plugins", "marketplace.json"), {"plugins": [{"name": "probe", "source": {"source": "local", "path": "./plugin"}}]})
        h.local({"links": {"probe": "../codex-checkout"}})
        assert same(h.resolve("probe")["root"], cpayload)
        folder = os.path.join(h.base, "folder")
        inner = plugin_dir(os.path.join(folder, "probe"), "probe", kind=None)
        h.local({"links": {"probe": "../folder"}})
        assert same(h.resolve("probe")["root"], inner), "<link>/<NAME>"
        flat = made(os.path.join(h.base, "flat"))
        h.local({"links": {"probe": "../flat"}})
        got = h.resolve("probe")
        assert same(got["root"], flat) and got["via"] == "link", "the link itself"


def test_D5_dev_overrides_the_declared_marketplace():
    with Hosts() as h:
        h.declare("probe", "m")
        h.claude_install("probe", "m", "1.0.0")
        dev = h.claude_install("probe", "devmarket", "1.0.0")
        h.local({"dev": {"probe": "devmarket"}})
        got = h.resolve("probe")
        assert same(got["root"], dev) and got["marketplace"] == "devmarket", got


def test_D5_dwitbuk_plugin_root_is_resolves_root_and_stops_with_its_reason():
    with Project() as pj, Hosts() as h:
        h.target = pj.dir
        h.declare("probe", "m", "1.0.0")
        cx = h.codex_install("probe", "m", "1.0.0")
        with h.os_environ("codex"):
            want = pluginroot().resolve(pj.dir, "probe")
            assert same(want["root"], cx), want
            assert same(dwitbuk.plugin_root(pj.dir, "probe"), want["root"]), "dwitbuk resolves a Codex-only install on codex"
        with h.os_environ("claude-code"):
            want = pluginroot().resolve(pj.dir, "probe")
            assert want["root"] is None and want["reason"], want
            try:
                got = dwitbuk.plugin_root(pj.dir, "probe")
                raise AssertionError("no root: plugin_root must stop, got %r" % (got,))
            except SystemExit as err:
                assert str(err) == want["reason"] or want["reason"] in str(err), (str(err), want["reason"])


def test_D5_a_reporter_resolved_with_a_version_note_carries_a_plugin_version_objection():
    with Project() as pj, Hosts() as h:
        h.target = pj.dir
        h.declare("probe", "m", "1.0.0")
        path = h.claude_install("probe", "m", "1.5.0")
        doc = {"artifact-type": "dwitbuk/findings@1", "source": "probe", "findings": []}
        write(os.path.join(path, "report.py"), "print(%r)\n" % json.dumps(doc))
        lock = dwitbuk.load(os.path.join(pj.dir, "hunsu.lock.json"))
        lock.setdefault("reporters", {})["probe-report"] = [sys.executable, "{plugin:probe}/report.py"]
        lock["reporters"]["missing-report"] = [sys.executable, "{plugin:absent}/report.py"]
        write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
        with h.os_environ("claude-code"):
            note = pluginroot().resolve(pj.dir, "probe")["note"]
            assert note and "1.0.0" in note and "1.5.0" in note, note
            code, out = run("review", "--since", pj.base, "--target", pj.dir)
        assert code == 0, out
        r = pj.latest()
        pv = [f for f in r["findings"] if f["kind"] == "plugin-version"]
        assert len(pv) == 1, r["findings"]
        assert pv[0]["where"] == "probe-report" and pv[0]["text"] == note and dwitbuk.layer(pv[0]) == "objection", pv
        failed = [f for f in r["findings"] if f["kind"] == "reporter-failed"]
        assert len(failed) == 1 and "missing-report" in failed[0]["where"], failed
        assert not [f for f in r["findings"] if f["kind"] == "plugin-version" and f["where"] == "missing-report"], r["findings"]


def test_D5_a_reporter_resolved_without_a_note_carries_no_plugin_version_finding():
    with Project() as pj, Hosts() as h:
        h.target = pj.dir
        h.declare("probe", "m", "1.5.0")
        path = h.claude_install("probe", "m", "1.5.0")
        doc = {"artifact-type": "dwitbuk/findings@1", "source": "probe", "findings": []}
        write(os.path.join(path, "report.py"), "print(%r)\n" % json.dumps(doc))
        lock = dwitbuk.load(os.path.join(pj.dir, "hunsu.lock.json"))
        lock.setdefault("reporters", {})["probe-report"] = [sys.executable, "{plugin:probe}/report.py"]
        write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
        with h.os_environ("claude-code"):
            assert pluginroot().resolve(pj.dir, "probe")["note"] is None
            code, out = run("review", "--since", pj.base, "--target", pj.dir)
        assert code == 0, out
        k = kinds(pj.latest())
        assert "plugin-version" not in k and "reporter-failed" not in k, k


# --- 11-06 E1: a packet bound to no review never appends to an ordinary review written after it.

def test_E1_a_packet_bound_to_no_review_gets_a_new_eyes_review_and_leaves_the_ordinary_review_as_it_was():
    import time
    with Project() as pj:
        d4_reporter(pj, D4_CHARGES + [D4_OBSERVATION])
        assert dwitbuk.reviews(pj.dir) == [], "no review yet"
        folder = os.path.join(pj.dir, ".dwitbuk", "packet")
        packet, _ = eyes_answer(pj, folder, "e1-unbound")
        assert packet["source"].get("review") is None, packet["source"]   # packed when no review existed
        time.sleep(1.1)
        assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
        ordinary = pj.latest()
        assert "eyes-of" not in ordinary, ordinary
        before = review_bytes(pj, ordinary["id"])
        code, out = run("eyes", "consume", "--dir", folder, "--target", pj.dir)
        assert code == 0, out
        assert review_bytes(pj, ordinary["id"]) == before, "the ordinary review written after the packet is byte-for-byte as it was"
        new = pj.latest()
        assert new["id"] != ordinary["id"] and len(dwitbuk.reviews(pj.dir)) == 2, [r["id"] for r in dwitbuk.reviews(pj.dir)]
        assert "eyes-of" in new and new["eyes-of"] is None, new
        assert_eyes_review(pj, new, None, ordinary, ["e1-unbound"])
        assert "added to %s" % new["id"] in out, out
        assert "no review" in out.replace("added to %s" % new["id"], ""), ("the printed line says the packet was bound to no review", out)


def test_E1_a_second_packet_bound_to_no_review_appends_to_the_eyes_review_with_eyes_of_null():
    import time
    with Project() as pj:
        d4_reporter(pj, D4_CHARGES + [D4_OBSERVATION])
        first, second = [os.path.join(pj.dir, ".dwitbuk", n) for n in ("first", "second")]
        p1, _ = eyes_answer(pj, first, "e1-first")
        p2, _ = eyes_answer(pj, second, "e1-second")
        assert p1["source"].get("review") is None and p2["source"].get("review") is None, (p1["source"], p2["source"])
        time.sleep(1.1)
        assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
        ordinary = pj.latest()
        before = review_bytes(pj, ordinary["id"])
        assert run("eyes", "consume", "--dir", first, "--target", pj.dir)[0] == 0
        made = pj.latest()
        assert made["id"] != ordinary["id"] and "eyes-of" in made and made["eyes-of"] is None, made
        code, out = run("eyes", "consume", "--dir", second, "--target", pj.dir)
        assert code == 0 and "added to %s" % made["id"] in out, out
        ids = [r["id"] for r in dwitbuk.reviews(pj.dir)]
        assert ids == [ordinary["id"], made["id"]], ids   # no third review
        grown = pj.latest()
        assert grown["findings"][:len(made["findings"])] == made["findings"], "appended, as consume appends"
        added = grown["findings"][len(made["findings"]):]
        assert [f["kind"] for f in added] == ["anomaly"] and "e1-second" in added[0]["text"], added
        assert grown["eyes-of"] is None and review_bytes(pj, ordinary["id"]) == before


def test_E1_a_packet_bound_to_a_review_never_appends_to_an_eyes_review_bound_to_no_review():
    import time
    with Project() as pj:
        d4_reporter(pj, D4_CHARGES + [D4_OBSERVATION])
        unbound = os.path.join(pj.dir, ".dwitbuk", "unbound")
        eyes_answer(pj, unbound, "e1-unbound")
        time.sleep(1.1)
        assert run("review", "--since", pj.base, "--target", pj.dir)[0] == 0
        ordinary = pj.latest()
        bound = os.path.join(pj.dir, ".dwitbuk", "bound")
        packet, _ = eyes_answer(pj, bound, "e1-bound")
        assert packet["source"].get("review") == ordinary["id"], packet["source"]
        assert run("eyes", "consume", "--dir", unbound, "--target", pj.dir)[0] == 0
        eyes_null = pj.latest()
        assert eyes_null["id"] != ordinary["id"] and eyes_null.get("eyes-of", "absent") is None, eyes_null
        null_bytes = review_bytes(pj, eyes_null["id"])
        code, out = run("eyes", "consume", "--dir", bound, "--target", pj.dir)
        assert code == 0, out
        assert review_bytes(pj, eyes_null["id"]) == null_bytes, "an eyes review of no review is not the bound review's eyes review"
        new = pj.latest()
        assert new["id"] not in (ordinary["id"], eyes_null["id"]) and new.get("eyes-of") == ordinary["id"], new


# --- 11-06 E2: pluginroot.resolve never raises on what it reads; collect never dies on a reporter it cannot resolve.

def e2_resolve(h, name, host="claude-code", **extra):
    """h.resolve, with any exception turned into a failed assertion: resolve must never raise on what it reads."""
    try:
        return h.resolve(name, host, **extra)
    except AssertionError:
        raise
    except Exception as err:
        raise AssertionError("pluginroot.resolve raised %s: %s" % (type(err).__name__, err))


def e2_review(pj):
    try:
        return run("review", "--since", pj.base, "--target", pj.dir)
    except Exception as err:
        raise AssertionError("dwitbuk review stopped with %s: %s" % (type(err).__name__, err))


def test_E2_a_linked_root_whose_manifest_is_not_an_object_is_a_root_with_no_version():
    with Hosts() as h:
        h.declare("probe", "m", "1.0.0")
        for i, bad in enumerate(("[]", '"x"', "3", "null", "{not json")):
            co = made(os.path.join(h.base, "linked-%d" % i))
            write(os.path.join(co, ".claude-plugin", "plugin.json"), bad)
            h.local({"links": {"probe": co}})
            for host in ("claude-code", "codex"):
                got = e2_resolve(h, "probe", host)
                assert got["root"] is not None and same(got["root"], co), (bad, host, got)
                assert got["version"] is None, ("a manifest that is not an object gives no version", bad, host, got)


def test_E2_an_installed_copy_whose_manifest_is_not_an_object_does_not_raise():
    with Hosts() as h:
        h.declare("probe", "m", "1.0.0")
        cl = h.claude_install("probe", "m", "1.0.0")
        cx = h.codex_install("probe", "m", "1.0.0")
        write(os.path.join(cl, ".claude-plugin", "plugin.json"), "[]")
        write(os.path.join(cx, ".codex-plugin", "plugin.json"), '"x"')
        got = e2_resolve(h, "probe", "claude-code")
        assert got["version"] is None and (got["root"] is not None or "plugin.json" in (got["reason"] or "")), got
        got = e2_resolve(h, "probe", "codex")
        assert got["version"] is None and (got["root"] is not None or "plugin.json" in (got["reason"] or "")), got


def test_E2_a_malformed_or_non_object_installed_plugins_json_gives_no_root_and_the_reason_names_it():
    with Hosts() as h:
        h.declare("probe", "m")
        h.claude_install("probe", "m", "1.0.0")
        reg = os.path.join(h.claude, "plugins", "installed_plugins.json")
        for bad in ("{not json", "[]", '[{"probe@m": []}]', '"x"', ""):
            write(reg, bad)
            got = e2_resolve(h, "probe")
            assert got["root"] is None and "installed_plugins.json" in (got["reason"] or ""), (bad, got)
        os.unlink(reg)
        made(reg)   # unreadable: a directory where the file should be
        got = e2_resolve(h, "probe")
        assert got["root"] is None and "installed_plugins.json" in (got["reason"] or ""), got
        h.declare("probe", None)   # undeclared: the same
        got = e2_resolve(h, "probe")
        assert got["root"] is None and "installed_plugins.json" in (got["reason"] or ""), got


def test_E2_a_malformed_config_toml_on_codex_gives_no_root_and_the_reason_names_it():
    with Hosts() as h:
        h.declare("probe", "m")
        h.codex_install("probe", "m", "1.0.0")
        cfg = os.path.join(h.codex, "config.toml")
        for bad in ('[plugins."probe@m"\nenabled = \n', "model = \n", "= = =\n"):
            write(cfg, bad)
            got = e2_resolve(h, "probe", "codex")
            assert got["root"] is None and "config.toml" in (got["reason"] or ""), (bad, got)
        os.unlink(cfg)
        made(cfg)   # unreadable
        got = e2_resolve(h, "probe", "codex")
        assert got["root"] is None and "config.toml" in (got["reason"] or ""), got


def test_E2_a_hunsu_json_or_hunsu_local_json_that_is_not_an_object_does_not_raise():
    with Hosts() as h:
        cl = h.claude_install("probe", "solo", "1.0.0")
        for fname in ("hunsu.json", "hunsu.local.json"):
            for bad in ("[]", '["probe"]', '"x"', "{not json"):
                for other in ("hunsu.json", "hunsu.local.json"):
                    p = os.path.join(h.target, other)
                    if os.path.lexists(p):
                        os.unlink(p)
                write(os.path.join(h.target, fname), bad)
                for host in ("claude-code", "codex"):
                    got = e2_resolve(h, "probe", host)
                    if got["root"] is None:
                        assert fname in (got["reason"] or "") or host == "codex", (fname, bad, host, got)
                assert same(e2_resolve(h, "probe")["root"], cl) or fname in (e2_resolve(h, "probe")["reason"] or ""), (fname, bad)
        # a hunsu.json whose plugins or entry are not objects
        for doc in ({"plugins": []}, {"plugins": "x"}, {"plugins": {"probe": []}}, {"plugins": {"probe": "m"}}):
            os.unlink(os.path.join(h.target, "hunsu.local.json")) if os.path.exists(os.path.join(h.target, "hunsu.local.json")) else None
            write(os.path.join(h.target, "hunsu.json"), doc)
            e2_resolve(h, "probe")
            e2_resolve(h, "probe", "codex")
        write(os.path.join(h.target, "hunsu.json"), {"plugins": {"probe": {"marketplace": "solo"}}})
        for doc in ({"links": []}, {"links": "x"}, {"links": {"probe": 3}}, {"dev": []}, {"dev": {"probe": 3}}):
            h.local(doc)
            e2_resolve(h, "probe")
            e2_resolve(h, "probe", "codex")


def test_E2_a_malformed_known_marketplaces_json_or_catalog_does_not_raise():
    with Hosts() as h:
        h.declare("probe", "dev")
        h.claude_install("probe", "dev", "1.0.0")
        known = os.path.join(h.claude, "plugins", "known_marketplaces.json")
        for bad in ("{not json", "[]", '{"dev": []}', '{"dev": {"source": "x"}}'):
            write(known, bad)
            got = e2_resolve(h, "probe")
            assert got["root"] is not None or "known_marketplaces.json" in (got["reason"] or ""), (bad, got)
        market = os.path.join(h.base, "dir-market")
        made(market)
        h.claude_directory_market("dev", market)
        catalog = os.path.join(market, ".claude-plugin", "marketplace.json")
        for bad in ("{not json", "[]", '{"plugins": {}}', '{"plugins": ["probe"]}', '{"plugins": [{"name": "probe", "source": 3}]}'):
            write(catalog, bad)
            got = e2_resolve(h, "probe")
            assert got["root"] is not None or "marketplace.json" in (got["reason"] or ""), (bad, got)
        co = made(os.path.join(h.base, "checkout"))
        h.local({"links": {"probe": co}})
        for bad in ("{not json", "[]", '{"plugins": [{"name": "probe", "source": []}]}'):
            write(os.path.join(co, ".claude-plugin", "marketplace.json"), bad)
            write(os.path.join(co, ".agents", "plugins", "marketplace.json"), bad)
            for host in ("claude-code", "codex"):
                got = e2_resolve(h, "probe", host)
                assert got["root"] is not None or "marketplace.json" in (got["reason"] or ""), (bad, host, got)


def test_E2_a_review_whose_reporter_hits_a_non_object_manifest_finishes():
    with Project() as pj, Hosts() as h:
        h.target = pj.dir
        h.declare("probe", "m", "1.0.0")
        path = h.claude_install("probe", "m", "1.0.0")
        write(os.path.join(path, ".claude-plugin", "plugin.json"), "[]")
        doc = {"artifact-type": "dwitbuk/findings@1", "source": "probe", "findings": []}
        write(os.path.join(path, "report.py"), "print(%r)\n" % json.dumps(doc))
        lock = dwitbuk.load(os.path.join(pj.dir, "hunsu.lock.json"))
        lock.setdefault("reporters", {})["probe-report"] = [sys.executable, "{plugin:probe}/report.py"]
        write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
        with h.os_environ("claude-code"):
            code, out = e2_review(pj)
        assert code == 0 and "Traceback" not in out, out
        r = pj.latest()
        assert r["head"], r
        failed = [f for f in r["findings"] if f["kind"] == "reporter-failed" and "probe-report" in f["where"]]
        assert "reporter-failed" not in kinds(r) or failed, r["findings"]


def test_E2_a_review_whose_registry_is_malformed_records_reporter_failed_for_its_reporter():
    with Project() as pj, Hosts() as h:
        h.target = pj.dir
        h.declare("probe", "m", "1.0.0")
        path = h.claude_install("probe", "m", "1.0.0")
        doc = {"artifact-type": "dwitbuk/findings@1", "source": "probe", "findings": []}
        write(os.path.join(path, "report.py"), "print(%r)\n" % json.dumps(doc))
        lock = dwitbuk.load(os.path.join(pj.dir, "hunsu.lock.json"))
        lock.setdefault("reporters", {})["probe-report"] = [sys.executable, "{plugin:probe}/report.py"]
        write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
        for bad in ("{not json", "[]"):
            write(os.path.join(h.claude, "plugins", "installed_plugins.json"), bad)
            with h.os_environ("claude-code"):
                code, out = e2_review(pj)
            assert code == 0 and "Traceback" not in out, (bad, out)
            failed = [f for f in pj.latest()["findings"] if f["kind"] == "reporter-failed" and "probe-report" in f["where"]]
            assert len(failed) == 1, (bad, pj.latest()["findings"])
            import time; time.sleep(1.1)


def test_E2_a_review_whose_codex_config_is_malformed_records_reporter_failed_for_its_reporter():
    with Project() as pj, Hosts() as h:
        h.target = pj.dir
        h.declare("probe", "m", "1.0.0")
        path = h.codex_install("probe", "m", "1.0.0")
        doc = {"artifact-type": "dwitbuk/findings@1", "source": "probe", "findings": []}
        write(os.path.join(path, "report.py"), "print(%r)\n" % json.dumps(doc))
        lock = dwitbuk.load(os.path.join(pj.dir, "hunsu.lock.json"))
        lock.setdefault("reporters", {})["probe-report"] = [sys.executable, "{plugin:probe}/report.py"]
        write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
        write(os.path.join(h.codex, "config.toml"), '[plugins."probe@m"\nenabled = \n')
        with h.os_environ("codex"):
            code, out = e2_review(pj)
        assert code == 0 and "Traceback" not in out, out
        failed = [f for f in pj.latest()["findings"] if f["kind"] == "reporter-failed" and "probe-report" in f["where"]]
        assert len(failed) == 1, pj.latest()["findings"]


# --- 11-06 E3: the version note says what hunsu.json declares and what the copy found is.

def e3_assert_note(got, name, declared, found, who):
    note = got["note"]
    assert note, got
    assert "hunsu.json declares" in note, ("the declaration is hunsu.json's, not the plugin's", note)
    assert name in note and declared in note and found in note, note
    root = got["root"]
    assert root and (root in note or os.path.realpath(root) in note), ("the note names the root", root, note)
    rest = note.replace(os.path.realpath(root), "").replace(root, "")
    assert who in rest, ("the note names the host or the link, beside the root", who, note)
    assert "declares version" not in note, ("the plugin declares nothing", note)


def test_E3_the_version_note_on_claude_code_says_hunsu_json_declares_and_the_claude_code_copy_is():
    with Hosts() as h:
        h.declare("probe", "m", "1.0.0")
        h.claude_install("probe", "m", "1.3.0")
        got = h.resolve("probe", "claude-code")
        e3_assert_note(got, "probe", "1.0.0", "1.3.0", "claude-code")


def test_E3_the_version_note_on_codex_says_hunsu_json_declares_and_the_codex_copy_is():
    with Hosts() as h:
        h.declare("probe", "m", "1.0.0")
        h.codex_install("probe", "m", "1.4.0")
        got = h.resolve("probe", "codex")
        e3_assert_note(got, "probe", "1.0.0", "1.4.0", "codex")


def test_E3_the_version_note_for_a_link_says_hunsu_json_declares_and_the_linked_copy_is():
    with Hosts() as h:
        h.declare("probe", "m", "1.0.0")
        co = os.path.join(h.base, "checkout")
        plugin_dir(os.path.join(co, "plugin"), "probe", version="1.7.0")
        write(os.path.join(co, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "probe", "source": "./plugin"}]})
        h.local({"links": {"probe": "../checkout"}})
        for host in ("claude-code", "codex"):
            got = h.resolve("probe", host)
            assert got["via"] == "link" and got["version"] == "1.7.0", (host, got)
            e3_assert_note(got, "probe", "1.0.0", "1.7.0", "linked")


def test_E3_the_review_finding_carries_the_new_note():
    with Project() as pj, Hosts() as h:
        h.target = pj.dir
        h.declare("probe", "m", "1.0.0")
        path = h.claude_install("probe", "m", "1.5.0")
        doc = {"artifact-type": "dwitbuk/findings@1", "source": "probe", "findings": []}
        write(os.path.join(path, "report.py"), "print(%r)\n" % json.dumps(doc))
        lock = dwitbuk.load(os.path.join(pj.dir, "hunsu.lock.json"))
        lock.setdefault("reporters", {})["probe-report"] = [sys.executable, "{plugin:probe}/report.py"]
        write(os.path.join(pj.dir, "hunsu.lock.json"), lock)
        with h.os_environ("claude-code"):
            code, out = run("review", "--since", pj.base, "--target", pj.dir)
        assert code == 0, out
        pv = [f for f in pj.latest()["findings"] if f["kind"] == "plugin-version"]
        assert len(pv) == 1 and "hunsu.json declares" in pv[0]["text"] and "claude-code" in pv[0]["text"], pv


# --- D6: a catalog is read only inside the folder it was found in (chongdae 2.1.0's rule M1) ---------------------------

D6_CATALOGS = (("claude",), ("codex",), ("claude", "codex"))
D6_HOSTS = ("claude-code", "codex")


def d6_symlink(src, dst):
    """os.symlink(src, dst); a Skip only where symlinks need a privilege this host lacks (Windows), never on macOS/Linux."""
    try:
        os.symlink(src, dst)
    except (OSError, NotImplementedError) as err:
        if os.name == "nt":
            raise Skip("os.symlink is unavailable here: %s" % err)
        raise


def d6_inside(path, folder):
    """realpath(path) is realpath(folder) or under it."""
    p, f = os.path.realpath(path), os.path.realpath(folder)
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def d6_market(folder, catalogs=("claude",), name="probe"):
    """`folder` holds the given catalogs, each selecting ./plugin, and folder/plugin a manifest naming `name` for each; the payload."""
    payload = os.path.join(folder, "plugin")
    for c in catalogs:
        if c == "claude":
            write(os.path.join(folder, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": name, "source": "./plugin"}]})
            plugin_dir(payload, name)
        else:
            write(os.path.join(folder, ".agents", "plugins", "marketplace.json"),
                  {"plugins": [{"name": name, "source": {"source": "local", "path": "./plugin"}}]})
            plugin_dir(payload, name, kind=".codex-plugin")
    return payload


def d6_escape(h, style, catalogs):
    """M, with M/probe a directory whose realpath leaves M, and the outside folder holding the catalogs and a real payload
    naming probe (so a catalog read would succeed). Returns (M, outside, payload)."""
    if style == "parent":
        outside = made(os.path.join(h.base, "par"))
        M = made(os.path.join(outside, "M"))
        payload = d6_market(outside, catalogs)
        d6_symlink("..", os.path.join(M, "probe"))
    else:
        M = made(os.path.join(h.base, "M"))
        outside = made(os.path.join(h.base, "outside"))
        payload = d6_market(outside, catalogs)
        if style == "relative":
            d6_symlink(os.path.join("..", "outside"), os.path.join(M, "probe"))
        elif style == "absolute":
            d6_symlink(os.path.abspath(outside), os.path.join(M, "probe"))
        elif style == "chain":
            d6_symlink(os.path.join("..", "outside"), os.path.join(M, "hop"))
            d6_symlink("hop", os.path.join(M, "probe"))
        else:
            raise AssertionError("fixture: unknown escape style %r" % style)
    probe = os.path.join(M, "probe")
    assert os.path.isdir(probe), ("fixture: M/probe is a directory", style)
    assert not d6_inside(probe, M), ("fixture: realpath(M/probe) is not inside realpath(M)", style, os.path.realpath(probe))
    assert os.path.isfile(os.path.join(payload, ".claude-plugin" if "claude" in catalogs else ".codex-plugin", "plugin.json")), "fixture"
    return M, outside, payload


def d6_as_named(got, M, payload, via, ctx):
    """root is the child as named — os.path.join(M, "probe") exactly — and not the outside payload nor anything under it."""
    want = os.path.join(M, "probe")
    assert got["root"] == want and got["via"] == via, ("the escaping child, as named", ctx, want, got)
    assert not same(got["root"], payload) and not d6_inside(got["root"], payload), ("never the outside catalog's choice", ctx, got)


def d6_link_escape(style):
    for catalogs in D6_CATALOGS:
        with Hosts() as h:
            M, outside, payload = d6_escape(h, style, catalogs)
            h.local({"links": {"probe": M}})
            for host in D6_HOSTS:
                d6_as_named(h.resolve("probe", host), M, payload, "link", (style, catalogs, host))


def d6_market_escape(style):
    for catalogs in D6_CATALOGS:
        with Hosts() as h:
            M, outside, payload = d6_escape(h, style, catalogs)
            h.claude_directory_market("dev", M)
            h.declare("probe", "dev")
            h.claude_install("probe", "dev", "1.0.0")
            d6_as_named(h.resolve("probe"), M, payload, "directory-marketplace", (style, catalogs))


def test_D6_C1_in_place_reads_no_catalog_of_a_child_that_escapes_the_folder():
    """C1: in_place(M, "probe") is None when M/probe's realpath leaves M — relative (Claude catalog) first, then every escape
    style and catalog kind; the outside folder's catalog would have chosen a real payload naming probe."""
    with Hosts() as h:
        M, outside, payload = d6_escape(h, "relative", ("claude",))
        got = pluginroot().in_place(M, "probe")
        assert got is None, ("in_place read the catalog of a child outside M", got)
    for style in ("relative", "absolute", "parent", "chain"):
        for catalogs in D6_CATALOGS:
            with Hosts() as h:
                M, outside, payload = d6_escape(h, style, catalogs)
                got = pluginroot().in_place(M, "probe")
                assert got is None, ("in_place read the catalog of a child outside M", style, catalogs, got)


def test_D6_C1_a_link_whose_child_escapes_by_a_relative_symlink_is_the_child_as_named():
    """C1, relative (M/probe -> ../outside): a link to M resolves to M/probe as named, via link, on both hosts — Claude
    catalog, Codex-only catalog, and both — never to outside/plugin."""
    d6_link_escape("relative")


def test_D6_C1_a_link_whose_child_escapes_by_an_absolute_symlink_is_the_child_as_named():
    """C1, absolute (M/probe -> <abs>/outside): the link resolves to M/probe as named, never outside/plugin."""
    d6_link_escape("absolute")


def test_D6_C1_a_link_whose_child_is_the_folders_parent_is_the_child_as_named():
    """C1, the folder's parent (M/probe -> ..; the parent holds the catalogs and plugin/): the link resolves to M/probe as named."""
    d6_link_escape("parent")


def test_D6_C1_a_link_whose_child_escapes_through_a_chain_is_the_child_as_named():
    """C1, a chain (M/hop -> ../outside, M/probe -> hop): the link resolves to M/probe as named."""
    d6_link_escape("chain")


def test_D6_C1_a_directory_marketplace_whose_child_escapes_by_a_relative_symlink_is_the_child_as_named():
    """C1, relative, Claude directory marketplace at M: M/probe as named via directory-marketplace, never outside/plugin."""
    d6_market_escape("relative")


def test_D6_C1_a_directory_marketplace_whose_child_escapes_by_an_absolute_symlink_is_the_child_as_named():
    """C1, absolute, directory marketplace: M/probe as named via directory-marketplace."""
    d6_market_escape("absolute")


def test_D6_C1_a_directory_marketplace_whose_child_is_the_folders_parent_is_the_child_as_named():
    """C1, the folder's parent, directory marketplace: M/probe as named via directory-marketplace."""
    d6_market_escape("parent")


def test_D6_C1_a_directory_marketplace_whose_child_escapes_through_a_chain_is_the_child_as_named():
    """C1, a chain, directory marketplace: M/probe as named via directory-marketplace."""
    d6_market_escape("chain")


def d6_own_catalog_out(h, how):
    """M (no M/probe) whose own catalog is reached through a symlink out of M; the outside catalog selects ./plugin and both
    M/plugin and outside/plugin hold a manifest naming probe, so only the catalog's location decides."""
    M = made(os.path.join(h.base, "M"))
    outside = made(os.path.join(h.base, "outside"))
    if how == "codex-dir":
        d6_market(outside, ("codex",))
        plugin_dir(os.path.join(M, "plugin"), "probe", kind=".codex-plugin")
        d6_symlink(os.path.join("..", "outside", ".agents"), os.path.join(M, ".agents"))
        catalog = os.path.join(M, ".agents", "plugins", "marketplace.json")
    else:
        d6_market(outside, ("claude",))
        plugin_dir(os.path.join(M, "plugin"), "probe")
        if how == "claude-dir":
            d6_symlink(os.path.join("..", "outside", ".claude-plugin"), os.path.join(M, ".claude-plugin"))
        else:
            made(os.path.join(M, ".claude-plugin"))
            d6_symlink(os.path.join("..", "..", "outside", ".claude-plugin", "marketplace.json"),
                       os.path.join(M, ".claude-plugin", "marketplace.json"))
        catalog = os.path.join(M, ".claude-plugin", "marketplace.json")
    assert os.path.isfile(catalog) and not d6_inside(catalog, M), ("fixture: the catalog is reached and lies outside M", how)
    return M


def d6_C2_own(how):
    with Hosts() as h:
        M = d6_own_catalog_out(h, how)
        got = pluginroot().catalog_source(M, "probe")
        assert got is None, ("a catalog whose realpath leaves the folder named a source", how, got)
        h.local({"links": {"probe": M}})
        for host in D6_HOSTS:
            got = h.resolve("probe", host)
            assert got["root"] == M and got["via"] == "link", ("the link itself", how, host, got)


def test_D6_C2_a_catalog_directory_symlinked_out_of_the_folder_names_nothing():
    """C2 (a): M/.claude-plugin -> ../outside/.claude-plugin: catalog_source(M, "probe") is None; a link to M is M itself."""
    d6_C2_own("claude-dir")


def test_D6_C2_a_catalog_file_symlinked_out_of_the_folder_names_nothing():
    """C2 (b): M/.claude-plugin/marketplace.json -> a file in outside: catalog_source(M, "probe") is None; the link is M."""
    d6_C2_own("claude-file")


def test_D6_C2_a_codex_catalog_directory_symlinked_out_of_the_folder_names_nothing():
    """C2 (c): M/.agents -> ../outside/.agents (Codex-only): catalog_source(M, "probe") is None; the link is M."""
    d6_C2_own("codex-dir")


def test_D6_C2_a_childs_catalog_symlinked_out_of_the_folder_names_nothing():
    """C2, a child: M/probe a real directory inside M whose .claude-plugin -> ../../outside/.claude-plugin: in_place(M,
    "probe") is None and the link resolves to M/probe as named."""
    with Hosts() as h:
        M = made(os.path.join(h.base, "M"))
        outside = made(os.path.join(h.base, "outside"))
        d6_market(outside, ("claude",))
        child = made(os.path.join(M, "probe"))
        plugin_dir(os.path.join(child, "plugin"), "probe")
        d6_symlink(os.path.join("..", "..", "outside", ".claude-plugin"), os.path.join(child, ".claude-plugin"))
        assert d6_inside(child, M) and not d6_inside(os.path.join(child, ".claude-plugin", "marketplace.json"), M), "fixture"
        got = pluginroot().in_place(M, "probe")
        assert got is None, ("the child's catalog lies outside M and was read", got)
        h.local({"links": {"probe": M}})
        for host in D6_HOSTS:
            got = h.resolve("probe", host)
            assert got["root"] == child and got["via"] == "link", ("the child as named", host, got)


def test_D6_C3_a_catalog_source_that_leaves_the_catalogs_folder_names_nothing():
    """C3, a guard shown, not red (catalog_local already holds it): a link to M whose own catalog selects ./plugin, with
    M/plugin -> ../outside/plugin, M/plugin -> M/hop -> ../outside/plugin, source "../outside/plugin", and an absolute
    source — each names nothing and the link resolves to M."""
    for case in ("symlink", "chain", "dotdot", "absolute"):
        with Hosts() as h:
            M = made(os.path.join(h.base, "M"))
            outside = made(os.path.join(h.base, "outside"))
            out_payload = plugin_dir(os.path.join(outside, "plugin"), "probe")
            source = "./plugin"
            if case == "symlink":
                d6_symlink(os.path.join("..", "outside", "plugin"), os.path.join(M, "plugin"))
            elif case == "chain":
                d6_symlink(os.path.join("..", "outside", "plugin"), os.path.join(M, "hop"))
                d6_symlink("hop", os.path.join(M, "plugin"))
            elif case == "dotdot":
                source = "../outside/plugin"
            else:
                source = os.path.abspath(out_payload)
            write(os.path.join(M, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "probe", "source": source}]})
            assert pluginroot().catalog_source(M, "probe") is None, case
            h.local({"links": {"probe": M}})
            for host in D6_HOSTS:
                got = h.resolve("probe", host)
                assert got["root"] == M and got["via"] == "link", ("the link itself", case, host, got)


def test_D6_C3_an_inside_childs_catalog_source_that_leaves_it_names_nothing():
    """C3, a guard shown, not red: M/probe a real directory whose catalog selects ./plugin with M/probe/plugin ->
    ../../outside/plugin: the child's catalog names nothing and the link resolves to M/probe as named."""
    with Hosts() as h:
        M = made(os.path.join(h.base, "M"))
        outside = made(os.path.join(h.base, "outside"))
        plugin_dir(os.path.join(outside, "plugin"), "probe")
        child = made(os.path.join(M, "probe"))
        write(os.path.join(child, ".claude-plugin", "marketplace.json"), {"plugins": [{"name": "probe", "source": "./plugin"}]})
        d6_symlink(os.path.join("..", "..", "outside", "plugin"), os.path.join(child, "plugin"))
        assert pluginroot().catalog_source(child, "probe") is None
        h.local({"links": {"probe": M}})
        for host in D6_HOSTS:
            got = h.resolve("probe", host)
            assert got["root"] == child and got["via"] == "link", (host, got)


D6_BAD_NAMES = ("..", ".", "", "a/b", "../outside", "a\\b")


def d6_bad_name_folder(h, name):
    """M inside a dedicated parent; os.path.join(M, name) exists as a directory and, where it is not M itself, holds a
    catalog selecting ./plugin with a manifest naming `name`."""
    par = made(os.path.join(h.base, "par"))
    M = made(os.path.join(par, "M"))
    d = made(os.path.join(M, name))
    assert os.path.isdir(os.path.join(M, name)), ("fixture", name)
    if os.path.normpath(d) != os.path.normpath(M):
        d6_market(d, ("claude",), name=name)
    return M


def test_D6_C4_in_place_takes_no_child_for_a_name_that_is_not_one_component():
    """C4: for "..", ".", "", "a/b", "../outside" and a name with a backslash, in_place(M, NAME) reads only M's own catalog
    (none here: None), though os.path.join(M, NAME) is a directory whose catalog would choose a payload naming NAME."""
    for name in D6_BAD_NAMES:
        with Hosts() as h:
            M = d6_bad_name_folder(h, name)
            got = pluginroot().in_place(M, name)
            assert got is None, ("a name that is not one path component made a child", name, got)


def test_D6_C4_a_link_with_a_name_that_is_not_one_component_is_the_link_itself():
    """C4: a link to M for each such NAME resolves to M itself (root == M exactly), via link, on both hosts."""
    for name in D6_BAD_NAMES:
        with Hosts() as h:
            M = d6_bad_name_folder(h, name)
            h.local({"links": {name: M}})
            for host in D6_HOSTS:
                got = h.resolve(name, host)
                assert got["root"] == M and got["via"] == "link", ("the link itself", repr(name), host, got)


def test_D6_C4_a_directory_marketplace_with_a_name_that_is_not_one_component_is_the_install():
    """C4: a Claude directory marketplace at M, NAME declared in hunsu.json with marketplace "dev", and a user-scope install
    record: the install, not os.path.join(M, NAME)."""
    for name in D6_BAD_NAMES:
        with Hosts() as h:
            M = d6_bad_name_folder(h, name)
            h.claude_directory_market("dev", M)
            h.declare(name, "dev")
            path = made(os.path.join(h.claude, "plugins", "cache", "dev", "d6-install", "1.0.0"))
            write(os.path.join(path, ".claude-plugin", "plugin.json"), {"name": name, "version": "1.0.0"})
            h.installed["%s@dev" % name] = [{"scope": "user", "installPath": path, "version": "1.0.0"}]
            write(os.path.join(h.claude, "plugins", "installed_plugins.json"), {"version": 2, "plugins": h.installed})
            got = h.resolve(name)
            assert same(got["root"], path), ("the install record", repr(name), got)
            assert not same(got["root"], os.path.join(M, name)), (repr(name), got)


def test_D6_C5_a_codex_marketplace_or_name_that_is_not_one_component_is_no_cache_path():
    """C5: a declared marketplace "../m" (or a NAME "../probe"), enabled in config.toml, whose path under plugins/cache
    reaches a copy with a manifest outside its place: no root on codex, with a reason."""
    for market, name in (("../m", "probe"), ("m", "../probe")):
        with Hosts() as h:
            h.declare(name, market)
            copy = made(os.path.join(h.codex, "plugins", "cache", market, name, "1.0.0"))
            write(os.path.join(copy, ".codex-plugin", "plugin.json"), {"name": name, "version": "1.0.0"})
            h.config["%s@%s" % (name, market)] = True
            h.write_config()
            assert os.path.isdir(copy), "fixture"
            got = h.resolve(name, "codex")
            assert got["root"] is None and got["reason"], ("a cache path from a name that is not one component", market, name, got)


def test_D6_C5_a_codex_copy_holding_a_catalog_is_the_copy_itself():
    """C5, a guard shown, not red: an ordinary Codex copy holding a catalog selecting ./plugin (a manifest there naming
    probe) resolves to the copy itself — no catalog inside a host's copy chooses the payload."""
    with Hosts() as h:
        h.declare("probe", "m")
        copy = h.codex_install("probe", "m", "1.0.0")
        d6_market(copy, ("claude", "codex"))
        got = h.resolve("probe", "codex")
        assert same(got["root"], copy) and not same(got["root"], os.path.join(copy, "plugin")), got


def test_D6_C6_a_claude_install_path_holding_a_catalog_is_taken_where_it_is():
    """C6, a guard shown, not red: an installPath holding .claude-plugin/marketplace.json that selects ./plugin (with a
    manifest there naming probe) resolves to the installPath itself."""
    with Hosts() as h:
        h.declare("probe", "m")
        path = h.claude_install("probe", "m", "1.0.0")
        d6_market(path, ("claude",))
        got = h.resolve("probe")
        assert same(got["root"], path) and not same(got["root"], os.path.join(path, "plugin")), got


def test_D6_C7_a_child_symlink_that_stays_inside_the_folder_is_followed():
    """C7 (a), a control, not red: M/probe -> real (relative) and, separately, M/probe -> <abs>/M/real, with M/real's
    catalog selecting ./plugin: in_place(M, "probe"), a link to M and a directory marketplace at M give M/real/plugin."""
    for absolute in (False, True):
        with Hosts() as h:
            M = made(os.path.join(h.base, "M"))
            payload = d6_market(made(os.path.join(M, "real")), ("claude",))
            d6_symlink(os.path.abspath(os.path.join(M, "real")) if absolute else "real", os.path.join(M, "probe"))
            assert d6_inside(os.path.join(M, "probe"), M), "fixture"
            assert same(pluginroot().in_place(M, "probe"), payload), absolute
            h.local({"links": {"probe": M}})
            for host in D6_HOSTS:
                got = h.resolve("probe", host)
                assert same(got["root"], payload) and got["via"] == "link", (absolute, host, got)
            h.local({})
            h.claude_directory_market("dev", M)
            h.declare("probe", "dev")
            h.claude_install("probe", "dev", "1.0.0")
            got = h.resolve("probe")
            assert same(got["root"], payload) and got["via"] == "directory-marketplace", (absolute, got)


def test_D6_C7_a_link_whose_own_path_is_a_symlink_to_a_checkout_reads_the_checkouts_catalog():
    """C7 (b), a control, not red: hunsu.local.json links probe to L, L -> <abs>/checkout with its catalog selecting
    ./plugin: the checkout's payload — the folder is wherever its link points."""
    with Hosts() as h:
        co = made(os.path.join(h.base, "checkout"))
        payload = d6_market(co, ("claude",))
        d6_symlink(os.path.abspath(co), os.path.join(h.base, "L"))
        h.local({"links": {"probe": "../L"}})
        for host in D6_HOSTS:
            got = h.resolve("probe", host)
            assert same(got["root"], payload) and got["via"] == "link", (host, got)


def test_D6_C7_a_plain_child_with_its_own_catalog_resolves_as_before():
    """C7 (c), a control, not red: a plain M/probe directory with its own catalog: in_place, the link and the directory
    marketplace give M/probe/plugin."""
    with Hosts() as h:
        M = made(os.path.join(h.base, "M"))
        payload = d6_market(made(os.path.join(M, "probe")), ("claude",))
        assert same(pluginroot().in_place(M, "probe"), payload)
        h.local({"links": {"probe": M}})
        for host in D6_HOSTS:
            got = h.resolve("probe", host)
            assert same(got["root"], payload) and got["via"] == "link", (host, got)
        h.local({})
        h.claude_directory_market("dev", M)
        h.declare("probe", "dev")
        h.claude_install("probe", "dev", "1.0.0")
        got = h.resolve("probe")
        assert same(got["root"], payload) and got["via"] == "directory-marketplace", got


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
