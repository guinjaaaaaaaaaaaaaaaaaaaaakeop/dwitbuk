"""dwitbuk's model guard for the eight core contracts in MODEL.md. The installed mangsang engine's
`check --require-model`, `cq` and `impact` decide model presence and the declared invariants; this guard keeps their
required scope aligned with this project's declarations.

  python3 check_mangsang.py --engine /path/to/the/installed/mangsang.py [--target DIR] [--json]

Read-only. It never registers, confirms, reconfirms or rewrites a record, and it fails if the engine's reads changed one.
Exit 0: the model holds. Exit 1: a declared scope, question binding, invariant kind or coverage anchor differs,
MODEL.md omits a declared concept/path/except, a relation lacks evidence, records change during reads, or the engine's
`check --require-model`, `cq` or `impact` fails. The engine decides absent/empty models, required content, projections,
coverage and registration. Exit 2: no usable engine (no such file, or not a mangsang plugin's engine).
Source-only: not part of the installed plugin in plugin/.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "mangsang"

# what MODEL.md says the model covers; dropping any of it is a scope change made here and there, not a silent loss
CONCEPTS = ("quote-grounded-finding", "bound-late-answer", "one-answer-per-charge", "serialized-review-mutation", "fail-closed-layer",
            "verifier-sees-touched", "closed-review-kept", "selected-host-plugin-root")
QUESTIONS = {"finding-kept": "quote-grounded-finding", "late-answer-taken": "bound-late-answer",
             "charge-answered": "one-answer-per-charge", "concurrent-mutation": "serialized-review-mutation",
             "charge-or-fact": "fail-closed-layer", "touched-seen": "verifier-sees-touched",
             "closed-review-written": "closed-review-kept", "plugin-root-chosen": "selected-host-plugin-root"}
CORE = {"quote-grounded-finding": "plugin/dwitbuk.py:grounded", "bound-late-answer": "plugin/dwitbuk.py:check_eyes",
        "one-answer-per-charge": "plugin/dwitbuk.py:cmd_dispose", "serialized-review-mutation": "plugin/dwitbuk.py:ReviewLock",
        "fail-closed-layer": "plugin/dwitbuk.py:layer", "verifier-sees-touched": "plugin/dwitbuk.py:verify_packet",
        "closed-review-kept": "plugin/dwitbuk.py:closed_reviews", "selected-host-plugin-root": "plugin/pluginroot.py:resolve"}
# the symbol a test proves directly for each concept: the test calls it (or its bare command dispatch) and asserts on what it
# returns or writes; a test that reaches a symbol only through another is a realizes, not a verifies. No test calls check_eyes
# so (the late-eyes test reaches it through `eyes consume`), and the only direct calls of layer read layers review already
# wrote: cmd_eyes and cmd_review stand for those concepts (their fingerprints read check_eyes and layer), and check_eyes,
# layer and carry are covered by realizes only (MODEL.md)
VERIFIED = {**CORE, "bound-late-answer": "plugin/dwitbuk.py:cmd_eyes", "fail-closed-layer": "plugin/dwitbuk.py:cmd_review",
            "closed-review-kept": "plugin/dwitbuk.py:cmd_eyes"}
SLUGS = {"grounded": "quote-grounded-finding", "check-eyes": "bound-late-answer", "cmd-dispose": "one-answer-per-charge",
         "review-lock": "serialized-review-mutation", "layer": "fail-closed-layer", "verify-packet": "verifier-sees-touched",
         "closed-reviews": "closed-review-kept", "plugin-root": "selected-host-plugin-root"}
# what each coverage invariant asks: moving one to another symbol is a scope change made here and in MODEL.md, not a silent one
COVERAGE = {**{"verified-%s" % k: ("verifies", VERIFIED[c]) for k, c in SLUGS.items()},
            **{"documented-%s" % k: ("documents", CORE[c]) for k, c in SLUGS.items()}}
INVARIANTS = {"required-model": "required", "registered-payload": "registered", "registered-source": "registered", "projected": "projection", "resolved": "resolved",
              **{qid: "coverage" for qid in COVERAGE}}
# the registered invariants' declared scope (MODEL.md, Registered and excepted): the tracked prefixes each must keep asking
# about, and every file or glob it may leave out. Under these a new tracked file fails the engine's `check` until it is
# registered or excepted with a reason; a dropped path or an extra except would let one in silently, so either is a scope
# change made here, in MODEL.md and in the record together
SCOPE = {
    "registered-payload": {"paths": ("plugin/",),
                           "except": ("plugin/LICENSE", "plugin/plugin.json", "plugin/.claude-plugin/plugin.json",
                                      "plugin/.codex-plugin/plugin.json", "plugin/commands/dispose.md", "plugin/commands/eyes.md",
                                      "plugin/commands/follow.md", "plugin/commands/review.md", "plugin/hooks/hooks.json",
                                      "plugin/hooks/codex.json", "plugin/hooks/session_start.py", "plugin/hostcall.py",
                                      "plugin/skills/review/SKILL.md")},
    "registered-source": {"paths": ("test", "AGENTS.md", "MODEL.md"), "except": ("test_check_mangsang.py",)},
}
MEDIA = {"doc": ("plugin/README.md#",), "code": ("plugin/dwitbuk.py:", "plugin/eyes_worker.py:", "plugin/hooks/stop_eyes.py:", "plugin/pluginroot.py:"),
         "test": ("test_dwitbuk.py:",)}
ENGINE_COMMANDS = ("check", "cq", "impact")
MANIFESTS = ("plugin.json", os.path.join(".claude-plugin", "plugin.json"), os.path.join(".codex-plugin", "plugin.json"))


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def records(target, kind):
    folder = os.path.join(target, MODEL, kind)
    out = []
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.endswith(".json"):
                out.append(load(os.path.join(folder, name)))
    return out


def tree_digest(target):
    """Every file under the model's records, by path and bytes: what a read must leave as it found it."""
    h, root = hashlib.sha256(), os.path.join(target, MODEL)
    for dirpath, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            p = os.path.join(dirpath, name)
            h.update(os.path.relpath(p, root).replace(os.sep, "/").encode() + b"\0")
            with open(p, "rb") as fh:
                h.update(fh.read() + b"\0")
    return h.hexdigest()


def guard(target):
    """The model's required content, read from its records. A list of problems; empty when it holds."""
    try:
        questions = {q.get("id"): q for q in records(target, "cq")}
        relations = records(target, "relations")
    except (OSError, ValueError) as err:
        return ["unreadable model record: %s" % err]
    problems = []
    for qid, concept in QUESTIONS.items():
        q = questions.get(qid)
        if q and not q.get("retired") and ((q.get("verify") or {}).get("kind") != "answered-by" or concept not in ((q.get("verify") or {}).get("concepts") or [])):
            problems.append("domain question %s is no longer answered by %s" % (qid, concept))
    for qid, kind in INVARIANTS.items():
        q = questions.get(qid)
        if not q or q.get("retired"):
            if qid == "required-model":
                problems.append("invariant missing or retired: %s" % qid)
        elif (q.get("verify") or {}).get("kind") != kind:
            problems.append("invariant %s is no longer of kind %s" % (qid, kind))
    for qid, (predicate, anchor) in COVERAGE.items():
        v = (questions.get(qid) or {}).get("verify") or {}
        if v.get("kind") == "coverage" and (v.get("predicate"), v.get("anchors")) != (predicate, anchor):
            problems.append("coverage invariant %s asks for a %s on %s; declared: a %s on %s" % (qid, v.get("predicate"), v.get("anchors"),
                                                                                                    predicate, anchor))
    for qid, scope in SCOPE.items():
        v = (questions.get(qid) or {}).get("verify") or {}
        if v.get("kind") != "registered":
            continue   # said above: missing, retired or of another kind
        paths, excepts = v.get("paths") or [], v.get("except") or []
        problems += ["registered scope narrowed: %s no longer asks about %s" % (qid, p) for p in scope["paths"] if p not in paths]
        problems += ["registered scope narrowed: %s excepts %s, which the declared scope does not name" % (qid, g)
                     for g in excepts if g not in scope["except"]]
    required = (questions.get("required-model") or {}).get("verify") or {}
    if required.get("kind") == "required":
        for part, names in (("concepts", CONCEPTS), ("questions", QUESTIONS),
                            ("invariants", [q for q in INVARIANTS if q != "required-model"])):
            problems += ["required scope narrowed: required-model no longer names %s %s" % (part[:-1], name)
                         for name in names if name not in (required.get(part) or [])]
        for concept, src in CORE.items():
            dst = "concept:" + concept
            if not any((r.get("src"), r.get("predicate"), r.get("dst")) == (src, "realizes", dst)
                       for r in (required.get("relations") or [])):
                problems.append("required scope narrowed: required-model no longer names relation %s realizes %s" % (src, dst))
    projected = (questions.get("projected") or {}).get("verify") or {}
    if projected.get("kind") == "projection":
        media = projected.get("media") or {}
        for medium, prefixes in MEDIA.items():
            problems += ["projection scope narrowed: projected no longer asks medium %s for %s" % (medium, p)
                         for p in prefixes if p not in (media.get(medium) or [])]
        for medium, prefixes in media.items():
            if medium not in MEDIA:
                problems.append("projection scope changed: projected names undeclared medium %s" % medium)
            else:
                problems += ["projection scope changed: projected asks medium %s for undeclared prefix %s" % (medium, p)
                             for p in prefixes if p not in MEDIA[medium]]
    for r in relations:
        if not str(r.get("evidence", "")).strip():
            problems.append("relation without evidence: %s" % r.get("id"))
    scope = os.path.join(target, "MODEL.md")
    if not os.path.isfile(scope):
        problems.append("MODEL.md missing: the model's scope is said nowhere")
    else:
        with open(scope, encoding="utf-8") as fh:
            text = fh.read()
        problems += ["MODEL.md does not name the covered concept %s" % n for n in CONCEPTS if "`%s`" % n not in text]
        problems += ["MODEL.md does not name %s's declared %s %s" % (qid, part[:-1] if part == "paths" else part, e)
                     for qid, scope in SCOPE.items() for part in ("paths", "except") for e in scope[part] if "`%s`" % e not in text]
    return problems


def engine_identity(engine, target):
    """(identity dict, problem or None). The engine must be a mangsang plugin's mangsang.py; its version is reported beside
    the version this project's lock pins (a difference is said, not refused: the caller chose the engine)."""
    ident = {"path": engine}
    if not os.path.isfile(engine) or os.path.basename(engine) != "mangsang.py":
        return ident, "no mangsang engine at %s" % engine
    root = os.path.dirname(os.path.abspath(engine))
    manifest = next((load(os.path.join(root, m)) for m in MANIFESTS if os.path.isfile(os.path.join(root, m))), None)
    if not isinstance(manifest, dict) or manifest.get("name") != "mangsang":
        return ident, "%s is not beside a mangsang plugin manifest" % engine
    with open(engine, "rb") as fh:
        ident["sha256"] = hashlib.sha256(fh.read()).hexdigest()
    ident["version"] = manifest.get("version")
    lock = os.path.join(target, "hunsu.lock.json")
    pinned = ((load(lock).get("plugins") or {}).get("mangsang") or {}).get("version") if os.path.isfile(lock) else None
    ident["locked"] = pinned
    ident["matches_lock"] = pinned is not None and pinned == ident["version"]
    ident["in_a_git_work_tree"] = subprocess.run(["git", "-C", root, "rev-parse", "--is-inside-work-tree"], capture_output=True,
                                                 text=True).stdout.strip() == "true"
    return ident, None


def run_engine(engine, target):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")   # no bytecode written into the installed engine's directory
    out = {}
    for cmd in ENGINE_COMMANDS:
        done = subprocess.run([sys.executable, "-B", engine, cmd, "--target", target] + (["--require-model"] if cmd == "check" else []), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env)
        text = (done.stdout + done.stderr).strip()
        out[cmd] = {"exit": done.returncode, "last": text.splitlines()[-1] if text else "", "output": text}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", default=os.environ.get("MANGSANG_ENGINE"),
                    help="the installed, released mangsang.py (default: $MANGSANG_ENGINE); never a working checkout's")
    ap.add_argument("--target", default=HERE, help="the project (default: this file's directory)")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    args = ap.parse_args(argv)
    target = os.path.abspath(args.target)
    problems = guard(target)
    if not args.engine:
        ident, unusable = {"path": None}, "no engine given: --engine /path/to/the/installed/mangsang.py (or $MANGSANG_ENGINE)"
    else:
        ident, unusable = engine_identity(os.path.abspath(args.engine), target)
    engine, changed = {}, False
    if not unusable:
        before = tree_digest(target)
        engine = run_engine(ident["path"], target)
        changed = tree_digest(target) != before
        if changed:
            problems.append("the engine's read changed the model's records")
    failed = [c for c, r in engine.items() if r["exit"] != 0]
    code = 2 if unusable else (1 if problems or failed else 0)
    if args.json:
        print(json.dumps({"target": target, "engine": ident, "unusable": unusable, "guard": problems,
                          "engine_results": {c: {"exit": r["exit"], "last": r["last"]} for c, r in engine.items()},
                          "exit": code}, indent=1, ensure_ascii=False))
        return code
    for p in problems:
        print("FAILED   %s" % p)
    if not problems:
        print("holds    the model: %d concepts, %d domain questions, %d invariants, required and projection scopes, "
              "the declared registered scope and MODEL.md" % (len(CONCEPTS), len(QUESTIONS), len(INVARIANTS)))
    if unusable:
        print("UNUSABLE %s" % unusable)
    else:
        print("engine   mangsang %s at %s (sha256 %s…; the lock pins %s%s)" % (ident["version"], ident["path"], ident["sha256"][:12],
              ident["locked"], "" if ident["matches_lock"] else " — a different version" ) + (" — inside a git work tree, not an installed copy?" if ident["in_a_git_work_tree"] else ""))
        for c, r in engine.items():
            print("%-8s %s: exit %d — %s" % ("ok" if r["exit"] == 0 else "FAILED", c, r["exit"], r["last"]))
            if r["exit"] != 0:
                print("\n".join("           " + l for l in r["output"].splitlines()))
    print("check_mangsang: %s" % ("holds" if code == 0 else "FAILED" if code == 1 else "no usable engine"))
    return code


if __name__ == "__main__":
    sys.exit(main())
