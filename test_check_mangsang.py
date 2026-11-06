"""Tests for check_mangsang.py, each on a disposable copy of this checkout (its git-visible files minus run and review
records, committed in a fresh repository): the live tree is never changed. The copy's model is damaged the way a real
change would damage it — a record removed, a question or relation retired with the engine's own commands, a registered
code anchor edited, a new payload or root-suite file committed, a registered invariant's scope narrowed — and the guard
must fail. With the model intact it must hold, and its reads leave the copy as it was.

  python3 test_check_mangsang.py --engine /path/to/the/installed/mangsang.py [--report OUT.json]

Without an engine (--engine or $MANGSANG_ENGINE) every test is a SKIP, never a pass.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LEFT_OUT = (".chongdae/", "reviews/", ".dwitbuk/", ".mangsang/")   # run and review records, machine state: not the source
ENGINE = None
REPORT = []
DLG = "test fixture: a disposable copy's damage, not a judgment about the project"


class Skip(Exception):
    pass


def git(cwd, *a):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env)


class Copy:
    """A disposable checkout: the files git sees here (tracked, or new and not ignored), committed in a fresh repository."""
    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="dwitbuk-model-")
        listed = git(HERE, "ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout.split("\0")
        for rel in (p for p in listed if p and not p.startswith(LEFT_OUT) and os.path.isfile(os.path.join(HERE, p))):
            dest = os.path.join(self.dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(os.path.join(HERE, rel), dest)
        assert os.path.isdir(os.path.join(self.dir, "mangsang")), "the copy holds the model"
        git(self.dir, "init", "-q", "-b", "main"); git(self.dir, "add", "-A"); git(self.dir, "commit", "-q", "-m", "copy")
        return self

    def __exit__(self, *a):
        shutil.rmtree(self.dir, ignore_errors=True)

    def path(self, *parts):
        return os.path.join(self.dir, *parts)

    def checker(self, engine=None):
        done = subprocess.run([sys.executable, "-B", self.path("check_mangsang.py"), "--engine", engine or ENGINE, "--target", self.dir],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        return done.returncode, done.stdout + done.stderr

    def engine(self, *a):
        done = subprocess.run([sys.executable, "-B", ENGINE, *a, "--target", self.dir], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        return done.returncode, done.stdout + done.stderr

    def relations(self):
        folder = self.path("mangsang", "relations")
        return [json.load(open(os.path.join(folder, n), encoding="utf-8")) for n in sorted(os.listdir(folder))]


def commit_new(c, files):
    """Write each new file into the copy and commit it: a tracked file, as `check` sees one after a real change."""
    for rel, text in files.items():
        dest = c.path(*rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
    git(c.dir, "add", "-A")
    done = git(c.dir, "commit", "-q", "-m", "new files")
    assert done.returncode == 0, done.stdout + done.stderr


def invariant_line(output, qid):
    """The engine `check` line of one invariant."""
    return next((l.strip() for l in output.splitlines() if re.match(r"\s*\S+\s+%s\s" % re.escape(qid), l)), "")


def record(case, code, out, **more):
    REPORT.append({"case": case, "checker_exit": code, "failed_lines": [l for l in out.splitlines() if l.startswith(("FAILED", "UNUSABLE"))][:12],
                   "last_line": out.strip().splitlines()[-1] if out.strip() else "", **more})


def revise(c, qid, change):
    """Revise one declared invariant's verify with the engine's own `cq revise`, signed as the fixture it is."""
    with open(c.path("mangsang", "cq", qid + ".json"), encoding="utf-8") as fh:
        verify = json.load(fh)["verify"]
    change(verify)
    done = c.engine("cq", "revise", qid, "--verify", json.dumps(verify), "--delegated", DLG)
    assert done[0] == 0, done
    return verify


def failed_lines(out):
    return [l.strip() for l in out.splitlines() if l.strip().startswith("FAILED")]


class RecordingEngine:
    """A copy of the installed engine's plugin, its mangsang.py logging each argv it is run with, outside the checkout."""
    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="dwitbuk-engine-")
        root = os.path.join(self.dir, "plugin")
        shutil.copytree(os.path.dirname(ENGINE), root, ignore=shutil.ignore_patterns("__pycache__"))
        self.log = os.path.join(self.dir, "argv.jsonl")
        self.path = os.path.join(root, os.path.basename(ENGINE))
        with open(self.path, encoding="utf-8") as fh:
            text = fh.read()
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("import sys as _s, json as _j\nwith open(%r, 'a', encoding='utf-8') as _f: _f.write(_j.dumps(_s.argv[1:]) + '\\n')\n" % self.log + text)
        return self

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]

    def __exit__(self, *a):
        shutil.rmtree(self.dir, ignore_errors=True)


def need_engine():
    if not ENGINE:
        raise Skip("no engine: --engine /path/to/the/installed/mangsang.py or $MANGSANG_ENGINE")


def test_the_intact_model_holds_and_the_guard_reads_without_writing():
    need_engine()
    with Copy() as c:
        code, out = c.checker()
        record("intact copy", code, out)
        assert code == 0 and "check_mangsang: holds" in out, out
        status = git(c.dir, "status", "--porcelain", "--untracked-files=all").stdout
        assert status == "", "the guard and the engine's reads left the copy as it was: %r" % status


def test_an_absent_model_fails_where_the_engine_alone_answers_green():
    need_engine()
    with Copy() as c:
        shutil.rmtree(c.path("mangsang"))
        engine = {cmd: c.engine(cmd)[0] for cmd in ("check", "cq", "impact")}
        code, out = c.checker()
        record("absent model", code, out, engine_alone=engine)
        assert engine == {"check": 0, "cq": 0, "impact": 0}, "the vacuous green this guard exists for: %r" % engine
        assert code == 1, out
        assert "required and absent" in out, "the engine's `check --require-model` failure, printed by the guard:\n" + out


def test_an_empty_model_fails():
    need_engine()
    with Copy() as c:
        shutil.rmtree(c.path("mangsang"))
        os.makedirs(c.path("mangsang", "concepts"))
        with open(c.path("mangsang", "registry.json"), "w", encoding="utf-8") as fh:
            fh.write("[]\n")
        engine = {cmd: c.engine(cmd)[0] for cmd in ("check", "cq", "impact")}
        code, out = c.checker()
        record("empty model", code, out, engine_alone=engine)
        assert code == 1, out
        assert "required and empty" in out, "the engine's `check --require-model` failure, printed by the guard:\n" + out


def test_a_lost_concept_fails():
    need_engine()
    with Copy() as c:
        os.unlink(c.path("mangsang", "concepts", "bound-late-answer.json"))
        cq = c.engine("cq")[0]
        code, out = c.checker()
        record("concept record removed (bound-late-answer)", code, out, engine_cq_exit=cq)
        line = invariant_line(out, "required-model")
        assert code == 1 and line.startswith("FAILED") and "concept:bound-late-answer" in line, "the engine's required-model line:\n" + out
        assert "concept missing: bound-late-answer" not in out, "the guard's own concept check is dropped; the engine says it:\n" + out


def test_a_retired_domain_question_fails():
    need_engine()
    with Copy() as c:
        done = c.engine("cq", "retire", "finding-kept", "--why", "fixture", "--delegated", DLG)
        assert done[0] == 0, done
        cq = c.engine("cq")[0]
        code, out = c.checker()
        record("domain question retired with the engine (finding-kept)", code, out, engine_cq_exit=cq)
        line = invariant_line(out, "required-model")
        assert code == 1 and line.startswith("FAILED") and re.search(r"question finding-kept is retired", line), "the engine's required-model line:\n" + out
        assert "domain question missing or retired: finding-kept" not in out, "the guard's own question check is dropped:\n" + out
        assert cq != 0, "the engine says the concept is unquestioned"


def test_a_lost_test_projection_fails():
    need_engine()
    with Copy() as c:
        gone = [r["id"] for r in c.relations() if r["predicate"] == "realizes" and r["dst"] == "concept:serialized-review-mutation"
                and r["src"].startswith("test_dwitbuk.py:")]
        assert gone, "the copy has the projection to lose"
        for rid in gone:
            assert c.engine("retire", rid, "--why", "fixture")[0] == 0
        check = c.engine("check")[0]
        code, out = c.checker()
        record("test projection retired with the engine (serialized-review-mutation)", code, out, retired=gone, engine_check_exit=check)
        assert check != 0, "the engine's projection invariant fails too"
        assert code == 1 and invariant_line(out, "projected").startswith("FAILED"), "the engine's projected line:\n" + out
        assert "projection missing:" not in out, "the guard's own projection check is dropped:\n" + out


def test_a_lost_verifies_fails():
    need_engine()
    with Copy() as c:
        gone = [r["id"] for r in c.relations() if r["predicate"] == "verifies" and r["dst"] == "plugin/dwitbuk.py:ReviewLock"]
        assert gone
        for rid in gone:
            assert c.engine("retire", rid, "--why", "fixture")[0] == 0
        check = c.engine("check")[0]
        code, out = c.checker()
        record("verifies retired with the engine (ReviewLock)", code, out, retired=gone, engine_check_exit=check)
        assert check != 0
        assert code == 1 and invariant_line(out, "verified-review-lock").startswith("FAILED"), "the engine's verified-review-lock line:\n" + out
        assert "verifies missing:" not in out, "the guard's own coverage check is dropped:\n" + out


def test_an_edited_registered_code_anchor_is_stale():
    need_engine()
    with Copy() as c:
        path = c.path("plugin", "dwitbuk.py")
        text = open(path, encoding="utf-8").read()
        edited = text.replace('needed = ("where", "tree_quote", "why") if f.get("kind") == "anomaly"',
                              'needed = ("where", "tree_quote") if f.get("kind") == "anomaly"', 1)
        assert edited != text, "the copy has the anchor to edit"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(edited)
        impact = c.engine("impact")
        code, out = c.checker()
        stale = sorted(set(re.findall(r"\bR-[0-9a-f]{8}\b", impact[1])))
        verifies = sorted(r["id"] for r in c.relations() if r["predicate"] == "verifies" and r["dst"] == "plugin/dwitbuk.py:grounded")
        record("registered code anchor edited (plugin/dwitbuk.py:grounded)", code, out, engine_impact_exit=impact[0], stale_relations=stale,
               verifies_on_anchor=verifies, impact_last_line=impact[1].strip().splitlines()[-1] if impact[1].strip() else "")
        assert impact[0] != 0 and "stale" in impact[1], impact
        assert verifies and set(verifies) <= set(stale), "the test that proves grounded is asked again: %r of %r" % (verifies, stale)
        assert code == 1 and re.search(r"FAILED\s+impact: exit [1-9]", out), out


def test_a_coverage_invariant_moved_to_another_symbol_fails_the_guard():
    need_engine()
    with Copy() as c:
        moved = {"kind": "coverage", "predicate": "verifies", "anchors": "plugin/dwitbuk.py:cmd_dispose", "as": "dst"}   # verified, so the engine holds
        done = c.engine("cq", "revise", "verified-layer", "--verify", json.dumps(moved), "--delegated", DLG)
        assert done[0] == 0, done
        check = c.engine("check")
        code, out = c.checker()
        record("verified-layer moved to cmd_dispose with the engine", code, out, engine_check_exit=check[0],
               engine_line=invariant_line(check[1], "verified-layer"))
        assert check[0] == 0, "the engine alone holds: cmd_dispose has a verifies\n" + check[1]
        assert code == 1 and ("coverage invariant verified-layer asks for a verifies on plugin/dwitbuk.py:cmd_dispose; "
                              "declared: a verifies on plugin/dwitbuk.py:cmd_review") in out, out


def test_a_new_payload_file_fails_the_engine_check_wherever_it_lands():
    need_engine()
    code_files = ("plugin/resolver.py", "plugin/commands/helper.py", "plugin/skills/review/tool.py")
    markdown = ("plugin/commands/new.md", "plugin/skills/other/SKILL.md", "plugin/skills/review/templates/SKILL.md")   # beside the named excepts
    caught = code_files + markdown
    with Copy() as c:
        commit_new(c, {**{f: "def resolve():\n    return None\n" for f in code_files}, **{f: "# new\n" for f in markdown}})
        check = c.engine("check")
        line = invariant_line(check[1], "registered-payload")
        code, out = c.checker()
        record("new payload files committed (%s)" % ", ".join(caught), code, out, engine_check_exit=check[0], engine_line=line)
        assert check[0] == 1 and line.startswith("FAILED") and "%d unregistered tracked file(s)" % len(caught) in line, check[1]
        assert all(f in line for f in caught), line
        assert code == 1 and re.search(r"FAILED\s+check: exit 1", out), out


def test_a_new_root_suite_fails_the_engine_check():
    need_engine()
    caught = ("test_resolver.py", "tests/test_resolver.py")
    with Copy() as c:
        commit_new(c, {f: "def test_resolve():\n    assert True\n" for f in caught})
        check = c.engine("check")
        line = invariant_line(check[1], "registered-source")
        code, out = c.checker()
        record("new root suites committed (%s)" % ", ".join(caught), code, out, engine_check_exit=check[0], engine_line=line)
        assert check[0] == 1 and line.startswith("FAILED") and all(f in line for f in caught), check[1]
        assert code == 1 and re.search(r"FAILED\s+check: exit 1", out), out


def test_the_exact_file_source_scope_misses_a_new_suite_and_the_guard_fails_it():
    need_engine()
    with Copy() as c:
        old = {"kind": "registered", "paths": ["test_dwitbuk.py", "AGENTS.md", "MODEL.md"]}   # registered-source before this repair
        done = c.engine("cq", "revise", "registered-source", "--verify", json.dumps(old), "--delegated", DLG)
        assert done[0] == 0, done
        commit_new(c, {"test_resolver.py": "def test_resolve():\n    assert True\n"})
        check = c.engine("check")
        code, out = c.checker()
        record("registered-source back to its exact files, new root suite committed", code, out, engine_check_exit=check[0],
               engine_line=invariant_line(check[1], "registered-source"))
        assert check[0] == 0, "the gap this repair closes: the engine alone never sees the new suite\n" + check[1]
        assert code == 1 and "registered scope narrowed: registered-source no longer asks about test" in out, out


def test_a_widened_payload_except_fails_the_guard():
    need_engine()
    with Copy() as c:
        with open(c.path("mangsang", "cq", "registered-payload.json"), encoding="utf-8") as fh:
            verify = json.load(fh)["verify"]
        verify["except"] = verify["except"] + ["plugin/*.py"]
        done = c.engine("cq", "revise", "registered-payload", "--verify", json.dumps(verify), "--delegated", DLG)
        assert done[0] == 0, done
        commit_new(c, {"plugin/resolver.py": "def resolve():\n    return None\n"})
        check = c.engine("check")
        code, out = c.checker()
        record("registered-payload except widened by plugin/*.py, new payload file committed", code, out, engine_check_exit=check[0],
               engine_line=invariant_line(check[1], "registered-payload"))
        assert check[0] == 0, "the widened except hides the new file from the engine\n" + check[1]
        assert code == 1 and "registered scope narrowed: registered-payload excepts plugin/*.py, which the declared scope does not name" in out, out


def test_the_scope_page_must_name_each_declared_except():
    need_engine()
    with Copy() as c:
        path = c.path("MODEL.md")
        text = open(path, encoding="utf-8").read()
        edited = text.replace("`test_check_mangsang.py`", "the guard's suite")
        assert edited != text
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(edited)
        code, out = c.checker()
        record("MODEL.md stops naming a declared except", code, out)
        assert code == 1 and "MODEL.md does not name registered-source's declared except test_check_mangsang.py" in out, out


def test_the_scope_page_must_name_each_covered_concept():
    need_engine()
    with Copy() as c:
        path = c.path("MODEL.md")
        text = open(path, encoding="utf-8").read().replace("`fail-closed-layer`", "fail-closed layers")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        code, out = c.checker()
        record("MODEL.md stops naming a covered concept", code, out)
        assert code == 1 and "MODEL.md does not name the covered concept fail-closed-layer" in out, out


def test_no_usable_engine_is_exit_2():
    need_engine()
    with Copy() as c:
        code, out = c.checker(engine=c.path("no-such", "mangsang.py"))
        assert code == 2 and "no mangsang engine" in out, out
        fake = c.path("fake", "mangsang.py")
        os.makedirs(os.path.dirname(fake))
        with open(fake, "w", encoding="utf-8") as fh:
            fh.write("raise SystemExit(0)\n")
        code2, out2 = c.checker(engine=fake)
        record("no usable engine (missing; a mangsang.py with no mangsang manifest)", code2, out2, missing_exit=code)
        assert code2 == 2 and "not beside a mangsang plugin manifest" in out2, out2


def test_the_guard_runs_the_engine_check_with_require_model():
    need_engine()
    with Copy() as c, RecordingEngine() as eng:
        code, out = c.checker(engine=eng.path)
        calls = eng.calls()
        record("intact copy, the engine's argv recorded", code, out, engine_calls=calls)
        assert code == 0 and "check_mangsang: holds" in out, out
        checks = [a for a in calls if a and a[0] == "check"]
        assert checks and all("--require-model" in a for a in checks), "every engine check the guard runs is check --require-model: %r" % calls
        assert any(a and a[0] == "cq" for a in calls) and any(a and a[0] == "impact" for a in calls), "cq and impact as now: %r" % calls
        assert git(c.dir, "status", "--porcelain", "--untracked-files=all").stdout == ""


def _narrowed(c, case, change, kind, name):
    revise(c, "required-model", change)
    check = c.engine("check", "--require-model")
    code, out = c.checker()
    record(case, code, out, engine_check_exit=check[0], engine_line=invariant_line(check[1], "required-model"))
    assert check[0] == 0, "the engine alone holds: required-model asks only what it now names\n" + check[1]
    want = "required scope narrowed: required-model no longer names %s %s" % (kind, name)
    assert code == 1 and want in out, "want %r:\n%s" % (want, out)


def test_a_required_model_dropping_a_new_concept_fails_the_guard():
    need_engine()
    with Copy() as c:
        _narrowed(c, "required-model revised without concept selected-host-plugin-root",
                  lambda v: v["concepts"].remove("selected-host-plugin-root"), "concept", "selected-host-plugin-root")


def test_a_required_model_dropping_an_old_concept_fails_the_guard():
    need_engine()
    with Copy() as c:
        _narrowed(c, "required-model revised without concept bound-late-answer",
                  lambda v: v["concepts"].remove("bound-late-answer"), "concept", "bound-late-answer")


def test_a_required_model_dropping_a_question_fails_the_guard():
    need_engine()
    with Copy() as c:
        _narrowed(c, "required-model revised without question touched-seen",
                  lambda v: v["questions"].remove("touched-seen"), "question", "touched-seen")


def test_a_required_model_dropping_an_invariant_fails_the_guard():
    need_engine()
    with Copy() as c:
        _narrowed(c, "required-model revised without invariant documented-closed-reviews",
                  lambda v: v["invariants"].remove("documented-closed-reviews"), "invariant", "documented-closed-reviews")


def test_a_required_model_dropping_a_core_relation_fails_the_guard():
    need_engine()
    with Copy() as c:
        def drop(v):
            before = len(v["relations"])
            v["relations"] = [r for r in v["relations"] if r.get("dst") != "concept:verifier-sees-touched"]
            assert len(v["relations"]) == before - 1, "the copy names the core to drop"
        revise(c, "required-model", drop)
        check = c.engine("check", "--require-model")
        code, out = c.checker()
        record("required-model revised without the core relation of verifier-sees-touched", code, out, engine_check_exit=check[0])
        assert check[0] == 0, check[1]
        lines = [l for l in out.splitlines() if "required scope narrowed: required-model no longer names relation" in l]
        assert code == 1 and lines and any("plugin/dwitbuk.py:verify_packet" in l or "verifier-sees-touched" in l for l in lines), out


def test_a_required_model_of_another_kind_fails_the_guard():
    need_engine()
    with Copy() as c:
        done = c.engine("cq", "revise", "required-model", "--verify", json.dumps({"kind": "resolved"}), "--delegated", DLG)
        assert done[0] == 0, done
        check = c.engine("check", "--require-model")
        code, out = c.checker()
        record("required-model revised to kind resolved", code, out, engine_check_exit=check[0])
        assert check[0] == 0, "the engine alone holds: a resolved invariant under that name\n" + check[1]
        assert code == 1 and any("required-model" in l for l in failed_lines(out)), out


def test_a_retired_required_model_fails_the_guard():
    need_engine()
    with Copy() as c:
        done = c.engine("cq", "retire", "required-model", "--why", "fixture", "--delegated", DLG)
        assert done[0] == 0, done
        check = c.engine("check", "--require-model")
        code, out = c.checker()
        record("required-model retired with the engine", code, out, engine_check_exit=check[0])
        assert check[0] == 0, "the engine alone holds with nothing required\n" + check[1]
        assert code == 1 and any("required-model" in l for l in failed_lines(out)), out


def test_projected_dropping_the_plugin_root_prefix_fails_the_guard():
    need_engine()
    with Copy() as c:
        revise(c, "projected", lambda v: v["media"]["code"].remove("plugin/pluginroot.py:"))
        check = c.engine("check", "--require-model")
        code, out = c.checker()
        record("projected revised without code medium plugin/pluginroot.py:", code, out, engine_check_exit=check[0])
        assert check[0] == 0, "the engine alone holds: another code projection still stands\n" + check[1]
        want = "projection scope narrowed: projected no longer asks medium code for plugin/pluginroot.py:"
        assert code == 1 and want in out, "want %r:\n%s" % (want, out)


def test_projected_with_a_medium_the_declaration_does_not_name_fails_the_guard():
    need_engine()
    with Copy() as c:
        revise(c, "projected", lambda v: v["media"]["test"].append("test_check_mangsang.py:"))
        check = c.engine("check", "--require-model")
        code, out = c.checker()
        record("projected revised to accept test_check_mangsang.py: as a test medium", code, out, engine_check_exit=check[0])
        assert check[0] == 0, check[1]
        assert code == 1 and any("projected" in l for l in failed_lines(out)), "projected's media equal the declared media:\n" + out


def test_a_new_concept_removed_whole_with_the_engine_fails_the_guard():
    need_engine()
    concept = "concept:selected-host-plugin-root"
    with Copy() as c:
        gone = [r["id"] for r in c.relations() if concept in (r.get("src"), r.get("dst"))]
        assert gone, "the copy has the concept's relations"
        for rid in gone:
            assert c.engine("retire", rid, "--why", "fixture")[0] == 0
        assert c.engine("cq", "retire", "plugin-root-chosen", "--why", "fixture", "--delegated", DLG)[0] == 0

        def drop(v):
            v["concepts"].remove("selected-host-plugin-root")
            v["questions"].remove("plugin-root-chosen")
            v["relations"] = [r for r in v["relations"] if r.get("dst") != concept]
        revise(c, "required-model", drop)
        os.unlink(c.path("mangsang", "concepts", "selected-host-plugin-root.json"))
        engine = {cmd: c.engine(cmd, *(["--require-model"] if cmd == "check" else []))[0] for cmd in ("check", "cq", "impact")}
        code, out = c.checker()
        record("selected-host-plugin-root removed whole with the engine", code, out, engine_alone=engine, retired=gone)
        assert engine == {"check": 0, "cq": 0, "impact": 0}, "the engine alone holds a model without it: %r" % engine
        assert code == 1 and any("selected-host-plugin-root" in l or "plugin-root-chosen" in l for l in failed_lines(out)), out


def main():
    global ENGINE
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=os.environ.get("MANGSANG_ENGINE"))
    ap.add_argument("--report", help="write each case's outcome as JSON here")
    args = ap.parse_args()
    ENGINE = os.path.abspath(args.engine) if args.engine else None
    failed = skipped = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print("PASS", name)
        except Skip as why:
            skipped += 1
            print("SKIP", name, "--", why)
        except (Exception, SystemExit) as err:
            failed += 1
            print("FAIL", name, "--", "%s: %s" % (type(err).__name__, str(err)[:2000]))
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump({"engine": ENGINE, "cases": REPORT, "failed": failed, "skipped": skipped}, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    print("all passed" if not failed and not skipped else "%d failed, %d skipped" % (failed, skipped))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
