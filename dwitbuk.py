"""dwitbuk — placed eyes and a ledger of findings.

  review [--since COMMIT] [--target DIR]   collect `dwitbuk/findings@1` from the reporters the lock declares (hunsu.lock.json `reporters`),
                                           carry dispositions and recurrence from the last review, write reviews/<id>.json
  dispose <review>/<finding> --as accepted|dismissed (--why WHY --by NAME | --delegated WHY [--by NAME]) [--approved-in SOURCE:ID] [--quote QUOTE]
                                           the disposition copies the finding's own text and where at disposal time; --quote grounds it in the record/tree;
                                           with --delegated, --by is who handed it off (`delegated-by`; `by` stays null: no person read it)
  follow [--path FILE] [--target DIR]      the latest review's undisposed objections, whole and grouped by kind; --path: only those
                                           whose `where` or `files` name FILE (ask before editing it); --brief (with --path): at most two
                                           lines, `N open objection(s) on this file: <kind> — <text>` and `+N more`; nothing open: no output
  eyes request --out DIR [--since COMMIT] [--contract PATH] [--lens NAME]...
                                           late eyes: a packet (diff, run records, plan or contract, open findings) for a bounded read-only
                                           session; one packet per lens (contract | record | fresh), or one without
  eyes consume --dir DIR                   its answer, validated (a quote from the record and one from the tree, or no finding), into the latest review

The same eyes, placed earlier: as a chongdae `verifier` provider (`eyes_worker.py --request <chongdae request> --response ...`)
they read the task's contract, the files it touched and the builder's report, and answer `dwitbuk/review@1` — accept, or reject
with quoted findings — before the gate. The hands never place the eyes; the runner, the environment or a person does.

A review is a record like a run: `reviews/<id>.json`, committed. dwitbuk finds; it never fixes. It owns the *type* of a finding
(`dwitbuk/finding@1`: kind, where, text, files?) and the follow-through; products report on their own records in that type
(chongdae `report`, mangsang `impact --findings`, hunsu `check --findings` …), declared as `reporters` in hunsu.json and locked.
dwitbuk never reads a product's directory to compute findings. Kinds it adds itself:
  undisposed    an open charge from an earlier review that nothing reported again: carried once, whole, naming where it was
                raised (`raised-in`) — the latest review holds every open charge, and one disposal answers it
  unchanged     observations earlier reviews hold in full (`seen-in`, a list), counted in one line instead of written again
  contradiction late eyes: the record says one thing, the tree or the plan another — quoted from both sides
  anomaly       late eyes: what a stranger would question in the tree, with a tree quote only
  no-reporters  nothing is declared: the review is late eyes and dispositions only, and says so
  review-debt   (older reviews only) the previous review's open count; no longer written — the carried charges are the debt

Every finding carries a `layer`: an *objection* is a charge someone must answer (dispose); an *observation* is a fact of the
record — `delegated`, or any kind a reporter itself marks `"layer": "observation"` — kept in the review but never disposal
debt. Unknown kinds are objections: fail closed.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys

REVIEWS = "reviews"
RUNS = ".chongdae"
OBSERVATION_KINDS = {"delegated", "review-debt"}   # facts of the record, not charges: nobody should dispose them. The debt (in
# older reviews) was a count of charges the review already carried one by one: disposing it as well was the same charge answered twice


def record_paths(target):
    """What the eyes leave out of a diff — the products' records and the environment: `record-paths` in hunsu.lock.json (each
    plugin's `records`), else the siblings' names as they were before the lock carried them; always chongdae's runs (dwitbuk
    reads them for its packets), its own reviews, and hunsu's files."""
    declared = load(os.path.join(target, "hunsu.lock.json")).get("record-paths")
    others = sorted({p for ps in declared.values() for p in ps}) if isinstance(declared, dict) else [".mangsang/", ".dwitbuk/"]
    return tuple(sorted(set(others) | {RUNS + "/", REVIEWS + "/", "hunsu", ".claude/"}))


def layer(f):
    """An explicit layer wins (a reporter may mark its own kind informational); by kind, `delegated` is an observation;
    everything else — unknown kinds included — is an objection. Fail closed: a kind nobody classified is a charge."""
    return f["layer"] if f.get("layer") in ("observation", "objection") else ("observation" if f.get("kind") in OBSERVATION_KINDS else "objection")


def load(path, default=None):
    if not os.path.exists(path):
        return {} if default is None else default
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def git(target, *a):
    done = subprocess.run(["git", *a], cwd=target, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return done.stdout if done.returncode == 0 else None


def install_entry(entries, target):
    """The host keeps one install record per (scope, project). The one that applies to `target` is its own project-scope
    record, else the user-scope one, else — for a project that only enabled the plugin — the first; entries[0] was the first
    project that ever installed it, which loads a different copy once versions diverge."""
    want = os.path.realpath(target)
    for e in entries:
        if e.get("scope") == "project" and e.get("projectPath") and os.path.realpath(e["projectPath"]) == want:
            return e
    for e in entries:
        if e.get("scope") == "user":
            return e
    return entries[0] if entries else {}


def plugin_root(target, name):
    links = load(os.path.join(target, "hunsu.local.json")).get("links", {})
    if name in links:
        root = links[name]
        return os.path.join(root, name) if os.path.isdir(os.path.join(root, name)) else root
    home = os.environ.get("HUNSU_CLAUDE_DIR") or os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    installed = load(os.path.join(home, "plugins", "installed_plugins.json")).get("plugins", {})
    # the copy this project runs: from the marketplace its manifest declares (or the one `hunsu dev` put it in development
    # from) — matched by name alone, the first record belonged to whichever project installed it first, and a review once
    # ran another project's 1.1.0 reporters that way
    market = load(os.path.join(target, "hunsu.local.json")).get("dev", {}).get(name) \
        or (load(os.path.join(target, "hunsu.json")).get("plugins", {}).get(name) or {}).get("marketplace")
    if market:
        src = (load(os.path.join(home, "plugins", "known_marketplaces.json")).get(market) or {}).get("source") or {}
        if src.get("source") == "directory" and os.path.isdir(os.path.join(src.get("path", ""), name)):
            return os.path.join(src["path"], name)   # a directory marketplace is loaded in place by the host: the source, not a snapshot
        entries = installed.get("%s@%s" % (name, market)) or []
        want = os.path.realpath(target)
        mine = [e for e in entries if e.get("scope") == "user" or (e.get("projectPath") and os.path.realpath(e["projectPath"]) == want)]
        if mine:
            return install_entry(mine, target).get("installPath")
        raise SystemExit("plugin %s@%s is declared for this project but not installed for it here — `hunsu install`" % (name, market))
    for key, entries in installed.items():
        if key.split("@")[0] == name and entries:
            return install_entry(entries, target).get("installPath")
    raise SystemExit("plugin %r is not linked (hunsu.local.json) or installed here" % name)


def resolve_argv(target, argv, since):
    out = []
    skip = False
    for a in argv:
        if skip:
            skip = False
            continue
        if a == "{since}":
            if since:
                out.append(since)
            else:
                out.pop()   # the flag before it: a reporter with nothing to be "since"
            continue
        for m in set(re.findall(r"\{plugin:([\w.-]+)\}", a)):
            a = a.replace("{plugin:%s}" % m, plugin_root(target, m).replace(os.sep, "/"))
        out.append(a)
    if out and out[0] in ("python", "python3") and not shutil.which(out[0]):
        out[0] = next((c for c in ("python3", "python") if shutil.which(c)), None) or sys.executable   # locks written on macOS say python3, on some hosts only python exists — the reporter should not die over the name
    return out


def collect(target, since):
    """Run every reporter the lock declares; keep what answers in the type. A reporter that does not is itself a finding.
    Returns (findings, reporters, heard): `heard` is the reporters (the lock's names) that did answer — a `standing` reporter (one that
    reads the current state, `"standing": true` on its findings document) that answered and no longer reports a finding
    has said the finding is gone."""
    reporters = load(os.path.join(target, "hunsu.lock.json")).get("reporters") or {}
    findings, heard = [], set()
    if not reporters:
        findings.append({"kind": "no-reporters", "where": "hunsu.lock.json",
                         "text": "no reporters declared (hunsu.json `reporters`, then lock): this review is late eyes and dispositions only; no run, relation or environment record was read"})
    for name, argv in reporters.items():
        try:
            done = subprocess.run(resolve_argv(target, argv, since), cwd=target, capture_output=True, text=True, encoding="utf-8", errors="replace")
            doc = json.loads(done.stdout)
            assert doc.get("artifact-type") == "dwitbuk/findings@1" and isinstance(doc.get("findings"), list)
        except (SystemExit, OSError, ValueError, AssertionError) as err:
            findings.append({"kind": "reporter-failed", "where": name, "text": "reporter %s gave no dwitbuk/findings@1: %s" % (name, str(err)[:200])})
            continue
        heard.add(name)
        for f in doc["findings"]:
            if f.get("kind") and f.get("where") is not None and f.get("text"):
                findings.append({"kind": f["kind"], "where": f["where"], "text": f["text"],
                                 **({"files": f["files"]} if "files" in f else {}),   # read below to group by directory; not saved
                                 **({"standing": True, "reporter": name} if doc.get("standing") is True else {}),
                                 **({"layer": f["layer"]} if f.get("layer") in ("observation", "objection") else {})})
    return findings, sorted(reporters), heard


def reviews(target):
    root = os.path.join(target, REVIEWS)
    return [load(os.path.join(root, n)) for n in sorted(os.listdir(root)) if n.endswith(".json")] if os.path.isdir(root) else []


def runs(target):
    """(name, plan, state) per run. A run's tasks are one file each under tasks/ (older runs kept them in state.json); session
    runs define tasks in the task file (`def`). Non-claims live on tasks; the reader sees them as "task: text"."""
    root = os.path.join(target, RUNS)
    out = []
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if not name.startswith("run-"):
            continue
        plan, state = load(os.path.join(root, name, "plan.json")), load(os.path.join(root, name, "state.json"))
        tasks = state.get("tasks") or {}
        folder = os.path.join(root, name, "tasks")
        if os.path.isdir(folder):
            for f in sorted(os.listdir(folder)):
                if f.endswith(".json"):
                    tasks[f[:-5]] = load(os.path.join(folder, f))
        state["tasks"] = tasks
        plan["tasks"] = plan.get("tasks", []) + [ts["def"] for ts in tasks.values() if "def" in ts]
        state["non-claims"] = list(state.get("non-claims", [])) + ["%s: %s" % (tid, n) for tid, ts in tasks.items() for n in ts.get("non-claims", [])]
        out.append((name, plan, state))
    return out


def cmd_review(args):
    target = args.target
    prior = reviews(target)
    base = args.since or (prior[-1]["head"] if prior else lock_commit(target))   # a first review starts where the record does: the lock
    head = (git(target, "rev-parse", "HEAD") or "no-git").strip()
    findings = []

    raw, sources, heard = collect(target, base if base != "no-git" else None)
    # type-level presentation: outside-run per directory, non-claims by first clause so repeats show — kinds, not products.
    # A non-claim stays one finding per run: grouped across runs, its `where` listed whichever runs this review happened to
    # span, so the same run's non-claim had a new identity in the next review and never inherited its disposition — the
    # same "no check decides this task" was answered ten times on one site in a day. What it stands for is said in words —
    # `[tasks a, b; in 2 runs: run-…, run-…]`, the run's tasks and the runs sharing the clause — and identity() strikes it:
    # an `[x2]` (1.13.0) read as a count of tasks, "no check decides this task [x2]" stood for eight tasks in two runs, and
    # two such lines and one more were told to the owner as "5건" (guin-site 10-15, reviews 666e and 4a23)
    by_dir = {}
    groups = {}
    defs = run_tasks(target)
    for f in raw:
        if f["kind"] == "outside-run" and f.get("files"):
            for p in f["files"]:
                by_dir.setdefault(os.path.dirname(p) or ".", []).append(os.path.basename(p))
        elif f["kind"] == "non-claim" and not str(f["where"]).startswith("settings."):
            key = re.sub(r"^\S+(?: \([^)]*\))?: ", "", f["text"])
            # the first clause, whole — a cut sentence is a different sentence. Not a provider's own: it leads with the contract
            # sentence it could not decide and says why after the dash, and cut there it read as a bare quote (36 such charges
            # in one guin-site review, the gap they named gone); only the "— N task(s): …" a reporter appends is dropped
            key = re.sub(r" — \d+ task\(s\): .*$", "", key) if key.startswith("(provider) ") else key.split(";")[0].split(" — ")[0]
            groups.setdefault(key, {}).setdefault(f["where"], []).append(f)
        else:
            if f["kind"] == "non-claim":
                # a finding about a setting the project declared (`settings.<product>.<key>` in hunsu.json): the reviewer is told
                # what the declaration leaves out, and the declaration is the project's own, answered where it was written
                f.setdefault("layer", "observation")
            findings.append(f)
    for folder, names in sorted(by_dir.items()):
        where = folder + "/" if folder != "." else ""
        shown = ", ".join(names[:4]) + (" … (+%d)" % (len(names) - 4) if len(names) > 4 else "")
        findings.append({"kind": "outside-run", "where": where + shown,
                         "text": "%d file(s) changed since %s; no completed run recorded touching them" % (len(names), base or "the beginning")})
    for key, by_run in groups.items():
        for where, fs in sorted(by_run.items()):
            f = {"kind": "non-claim", "where": where, "text": key + bearing(fs, by_run)}
            if key == NO_CHECK and all(uncheckable_by_nature(defs.get(where, {}), t, target) for x in fs for t in task_ids(x["text"])):
                # a contract, design or plan document (domain plan) has no check that could decide prose, a test task's tests
                # are what the build is checked against, and a task that wrote only documents or records (a Done line in
                # ATPROTO.md, `hunsu lock`) has nothing a check could run on: said, not a charge — a session's code task with
                # no check still is one
                f["layer"] = "observation"
            findings.append(f)

    for f in findings:
        f["layer"] = layer(f)   # observation: a fact of the record; objection: a charge to dispose. Fail closed on unknown kinds.

    # 5. the latest review is the open set. A finding seen again inherits its disposition; an open charge that stopped
    #    recurring is carried into this review once, whole, as a reference to where it was raised (`raised-in`) — not re-raised
    #    as a new objection with its own wording. Older reviews are history. Only objections are debt: an observation that stops
    #    recurring simply stops. There is no debt line: the carried charges are the debt, each once (a `review-debt` line
    #    restated their count in every review, guin-site 2026-10-05..06, and the same eight charges stood in five reviews).
    if prior:
        # a finding's identity is kind + where + its text: several stage-findings share one `where` (one quibble round), and
        # with (kind, where) alone only one of them inherited its disposition — the others came back as new debt. Keyed by the
        # charge, a carry and the reporter's own copy of the same charge, found again, are one finding, not two
        last = {charge(f): (i, f) for i, f in enumerate(prior[-1].get("findings", []))}
        settled = answered(prior)
        carried = carried_observations(prior)
        origin = raised(prior)
        kept, unchanged = [], {}
        for f in findings:
            i_old, old = last.pop(charge(f), None) or last.pop(cut_charge(f), (None, None))
            if old:
                f["first-seen"] = old.get("first-seen", prior[-1]["id"])
                if old.get("disposition"):
                    f["disposition"] = old["disposition"]
            if not f.get("disposition") and (charge(f) in settled or cut_charge(f) in settled):
                f["disposition"] = settled.get(charge(f)) or settled[cut_charge(f)]   # answered in any earlier review, not only the last: one charge, one answer
            # an observation is a fact of the record; written in full once, it is counted after that, with the review that
            # holds it — a site's 120 relations confirmed by delegation were 58 KB of every review, forever
            written_in = prior[-1]["id"] if old else carried.get(identity(f), (None, None))[1]
            if written_in and layer(f) == "observation" and f.get("kind") != "unchanged":
                unchanged.setdefault(written_in, {})[f["kind"]] = unchanged.get(written_in, {}).get(f["kind"], 0) + 1
                continue
            kept.append(f)
        findings[:] = kept
        if unchanged:
            # one line for everything already on record, however many reviews hold it: one line per holding review was 12-15
            # lines at the head of every review on a site, all of them the same as the review before's
            by_kind = {}
            for kinds_ in unchanged.values():
                for k, n in kinds_.items():
                    by_kind[k] = by_kind.get(k, 0) + n
            held = sorted(unchanged)
            findings.append({"kind": "unchanged", "layer": "observation", "where": "%d earlier review(s)" % len(held), "seen-in": held,
                             "text": "%d observation(s) written in full in %d earlier review(s) and unchanged since (%s)"
                                     % (sum(by_kind.values()), len(held), ", ".join("%s %d" % kv for kv in sorted(by_kind.items())))})
        for i_old, old in last.values():
            if layer(old) != "objection" or old.get("kind") == "review-debt":
                continue
            if old.get("disposition") or charge(old) in settled:
                continue
            if old.get("standing") and old.get("reporter") in heard:
                continue   # its reporter reads the state as it is now, answered, and no longer sees it: the condition is gone
            if no_check_by_nature(old, defs, target):
                # raised before a documents-or-records task was known to be uncheckable by nature: a fact, not a charge, so it
                # stops here like an observation — guin-site review a3c2 carried three such (a first post's Done line, a plugin
                # lock, a Cirrus note), each an objection for a day before a session accepted it by delegation
                continue
            findings.append(carry(old, "%s/%d" % (prior[-1]["id"], i_old), prior[-1]["id"], origin))

    import secrets, time
    rid = "review-%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), secrets.token_hex(2))   # sorts by time on one machine, still unique across machines
    # the review is `since`, `head` and the findings: which reporters were asked is the lock's to say (a `reporters` list was
    # written here and read by nothing; `source` on each finding, `files` on outside-run, `count` on unchanged — the same)
    save(os.path.join(target, REVIEWS, rid + ".json"), {"artifact-type": "dwitbuk/review@1", "id": rid, "since": base, "head": head, "findings": findings})
    obs = [(i, f) for i, f in enumerate(findings) if layer(f) == "observation"]
    answered_ = [(i, f) for i, f in enumerate(findings) if layer(f) == "objection" and f.get("disposition")]
    carried_ = 0
    for i, f in enumerate(findings):
        if layer(f) == "objection" and not f.get("disposition"):
            if f.get("raised-in"):
                carried_ += 1
                print("  %-12s %d  %s — %s  (carried: raised in %s)" % (kind_of(f), i, f["where"], f["text"], f["raised-in"]))
            else:
                print("  %-12s %d  %s — %s" % (f["kind"], i, f["where"], f["text"]))
    if carried_:
        print("carried from earlier reviews, each once: %d (not raised again; one disposal answers each)" % carried_)
    if answered_:
        # seen again, answered before: carried with its disposition — the record keeps it, the reader is not asked again
        print("already answered, carried with their disposition: %d (%s)" % (len(answered_), ", ".join(str(i) for i, _ in answered_)))
    if obs:
        print("observations (facts of the record, not disposal debt): %d" % len(obs))
        for i, f in obs:
            print("  %-12s %d  %s — %s" % (f["kind"], i, f["where"], f["text"]))
    open_ = distinct([f for f in findings if layer(f) == "objection" and not f.get("disposition")])
    print("%s: %d objection(s) (%s), %d observation(s) since %s" % (rid, len(open_), count_text(open_), len(obs), base or "the beginning"))
    return 0


def task_ids(text):
    """The tasks a chongdae non-claim names: `T1: …` or `… — 2 task(s): T1, T2`."""
    m = re.search(r" — \d+ task\(s\): (.+)$", text)
    if m:
        return [t.strip() for t in m.group(1).split(",")]
    m = re.match(r"^(\S+?)(?: \([^)]*\))?: ", text)
    return [m.group(1)] if m else []


def bearing(fs, by_run):
    """What a grouped non-claim stands for, in words: the tasks of this run that bear it, and — when other runs share the
    clause — how many runs and which: `  [tasks T1, T2; in 2 runs: run-a, run-b]`. Struck from identity (BEARING), like the
    `[xN]` it replaces, so the charge is the same charge however many tasks or runs come to bear it."""
    tasks = []
    for x in fs:
        tasks += [t for t in task_ids(x["text"]) if t not in tasks]
    parts = (["task%s %s" % ("s" if len(tasks) > 1 else "", ", ".join(tasks))] if tasks else []) + \
            (["in %d runs: %s" % (len(by_run), ", ".join(sorted(by_run)))] if len(by_run) > 1 else [])
    return "  [%s]" % "; ".join(parts) if parts else ""


OLD_REPEAT = re.compile(r"\s*\[x\d+\]")
BEARING = r"\[x\d+\]|\[(?:tasks? [^\]]*|in \d+ runs: [^\]]*)\]"   # `[x2]` (before 1.14.0) and the words that replaced it


NO_CHECK = "no check decides this task"   # chongdae's non-claim on a task added without checks (first clause)
DOC_SUFFIXES = (".md", ".markdown", ".mdx", ".txt", ".rst", ".adoc")
NO_CHECK_DOMAINS = {"plan", "doc", "docs", "record", "records"}   # a task that declares itself prose or record (chongdae `add --domain`)


def run_tasks(target):
    """{run: {task id: the task's definition, with `touched`/`adopted`/`scope` from its record}} — what review needs to tell a
    task no check could decide from one nobody checked."""
    out = {}
    for name, plan, state in runs(target):
        tasks = {}
        for t in plan.get("tasks", []):
            ts = (state.get("tasks") or {}).get(t.get("id")) or {}
            tasks[t.get("id")] = dict(t, touched=ts.get("touched") or [], **{"non-claims": ts.get("non-claims") or []},
                                      adopted=[p for a in ts.get("adopted") or [] if isinstance(a, dict) for p in a.get("files") or []])
        out[name] = tasks
    return out


def documents_or_records(paths, target):
    """Every path is a document (Markdown, text) or under the records and environment the lock declares (`record-paths`:
    hunsu's files, mangsang/, reviews/ …). An empty list is not: a task that says nothing of its files fails closed."""
    recs = record_paths(target)
    def one(p):
        p = str(p).replace("\\", "/")
        p = p[2:] if p.startswith("./") else p
        return p.lower().endswith(DOC_SUFFIXES) or any(p.startswith(r) or p == r.rstrip("/") for r in recs)
    return bool(paths) and all(one(p) for p in paths)


def uncheckable_by_nature(tasks, tid, target=None):
    """A task no check can decide by what it is: a plan-domain task (a contract, a design, a decision — prose) or one that
    declares itself documents or records (`domain`), the test writer's task (its tests are the check the build answers to),
    the quibble's (its answer is questions on the contract), or a task whose files — what it touched and adopted, else its
    declared `scope` — are all documents or records (guin-site 10-12: `first-post-done` wrote a Done line in ATPROTO.md,
    `plugin-lock` ran `hunsu lock`, `cirrus-enter-doc` noted an upstream issue; each was charged "no check decides this
    task"). Unknown tasks are not: fail closed."""
    t = tasks.get(tid) or {}
    if t.get("domain") in NO_CHECK_DOMAINS or t.get("role") in ("nitpick", "quibble"):
        return True
    files = list(t.get("touched") or []) + list(t.get("adopted") or [])
    return target is not None and documents_or_records(files or t.get("scope") or [], target)


def no_check_by_nature(old, defs, target):
    """An open "no check decides this task" charge (or a carry of one) whose run's tasks that bear it are all uncheckable by
    nature now — a charge raised before that was known. Its text no longer names the tasks (grouped by clause), so the run's
    records say which tasks carry the non-claim."""
    kind, where, text = charge(old)
    if kind != "non-claim" or text != NO_CHECK or where not in defs:
        return False
    bearing = [tid for tid, t in defs[where].items() if any(str(n).startswith(NO_CHECK) for n in t.get("non-claims") or [])]
    return bool(bearing) and all(uncheckable_by_nature(defs[where], tid, target) for tid in bearing)


def carried_observations(prior):
    """identity -> (finding, the review that holds it in full), for every observation the latest review stands on: its own,
    and — following each `unchanged` line's `seen-in` back — those an earlier review wrote in full and later reviews only
    counted. So an observation is written once, however many reviews follow, and still recognized as the same fact."""
    by_id = {r.get("id"): r for r in prior}
    out, seen, queue = {}, set(), [prior[-1]]
    while queue:
        r = queue.pop(0)
        if r.get("id") in seen:
            continue
        seen.add(r.get("id"))
        for f in r.get("findings", []):
            if f.get("kind") == "unchanged":
                seen_in = f.get("seen-in")
                queue.extend(by_id[x] for x in (seen_in if isinstance(seen_in, list) else [seen_in]) if x in by_id)
            elif layer(f) == "observation":
                out.setdefault(identity(f), (f, r.get("id")))
    return out


def raised(prior):
    """{charge: (handle, finding)}: the latest review that holds each charge as raised — the reporter's or the eyes' own
    finding, whole — not as a carry. A carry points there (`raised-in`), so its text is the charge's, never a re-wording."""
    out = {}
    for r in prior:
        for i, f in enumerate(r.get("findings", [])):
            if layer(f) == "objection" and f.get("kind") != "undisposed":
                out[identity(f)] = ("%s/%d" % (r.get("id"), i), f)
    return out


CHARGE_KEYS = ("files", "record_quote", "tree_quote")


def carry(old, handle, rid, origin):
    """An open charge the previous review held and nothing reported again, carried into the new review once: its own text
    whole (an `undisposed` line once cut it at 80 characters behind a prefix of its own — "no completed r"), the charge it
    is (`carries`), when it was first seen and where it was raised. A carry already carried keeps all of that; one written
    before `raised-in` existed is pointed at the charge as raised, and gets its whole text back from there."""
    if old.get("kind") == "undisposed":
        c = {k: v for k, v in old.items() if k != "disposition"}
        if not c.get("raised-in") and tuple(c.get("carries") or ()) in origin:
            c["raised-in"], src = origin[tuple(c["carries"])]
            c["text"] = src["text"]
            c.update({k: src[k] for k in CHARGE_KEYS if k in src})
        c["text"] = OLD_REPEAT.sub("", c.get("text", ""))
        return c
    # an `[xN]` written before 1.14.0 is struck from the carried text: it read as a count of tasks (the charge is `carries`)
    return {"kind": "undisposed", "layer": "objection", "where": old["where"], "text": OLD_REPEAT.sub("", old["text"]),
            **{k: old[k] for k in CHARGE_KEYS if k in old},
            "carries": list(identity(old)), "first-seen": old.get("first-seen", rid), "raised-in": handle}


def kind_of(f):
    """The kind of charge a finding makes: a carry's is the kind of the charge it carries."""
    return f["carries"][0] if f.get("kind") == "undisposed" and f.get("carries") else f.get("kind")


def open_charges(target):
    """(latest review id, [(index, finding)]) — the latest review's objections no disposal answers. A disposal is written
    once, where the charge stood when it was answered; every other copy of that charge, in any review, is answered by it."""
    rs = reviews(target)
    if not rs:
        return None, []
    settled = answered(rs)
    return rs[-1]["id"], [(i, f) for i, f in enumerate(rs[-1].get("findings", []))
                          if layer(f) == "objection" and not f.get("disposition") and charge(f) not in settled]


def distinct(open_):
    """Open objections, one per charge: two copies of one charge are one thing owed."""
    seen, out = set(), []
    for f in open_:
        if charge(f) not in seen:
            seen.add(charge(f))
            out.append(f)
    return out


def count_text(open_):
    """The one count of open charges, the same in `review`'s last line and the SessionStart line: each distinct charge once,
    under the kind of the charge it makes — a carry (`undisposed`) under the kind it carries — and then how many of those are
    carried from earlier reviews, said as included: `cq-failed 2, non-claim 10; 3 of them carried, already in the count`. The
    review counted a carry as `undisposed` and the session line as its charge's kind, so one review read "non-claim 7,
    undisposed 3" at close and "non-claim 10" at the next session start (guin-site review a3c2); and a bare "; 3 carried"
    can be read as three more."""
    open_ = distinct(open_)
    counts = {}
    for f in open_:
        k = kind_of(f) or "?"
        counts[k] = counts.get(k, 0) + 1
    carried = sum(1 for f in open_ if f.get("kind") == "undisposed")
    return (", ".join("%s %d" % kv for kv in sorted(counts.items())) or "none") + ("; %d of them carried, already in the count" % carried if carried else "")


def lock_commit(target):
    """The commit that first added hunsu.lock.json — where a project's record begins; None without git or a lock."""
    out = git(target, "log", "--diff-filter=A", "--format=%h", "--", "hunsu.lock.json") or ""
    return out.strip().splitlines()[-1] if out.strip() else None


def identity(f):
    """What makes a finding the same finding across reviews: its kind, where, and its text with the numbers that change
    between reviews (counts, which tasks and runs bear a grouped non-claim — `[tasks …; in N runs: …]`, `[xN]` before it —
    "since <rev>") struck — a reworded finding is a different one."""
    text = re.sub(BEARING + r"|\b\d+ file\(s\)|since [0-9a-f]{7,}|\(first seen [^)]*\)", "", f.get("text", "")).strip()
    return (f.get("kind"), f.get("where"), text)


def charge(f):
    """The charge a finding makes, across reviews: its identity — or, for an `undisposed` carry, the identity of the finding
    it carries. Every copy of one charge is answered by one disposal."""
    return tuple(f["carries"]) if f.get("kind") == "undisposed" and f.get("carries") else identity(f)


def cut_charge(f):
    """The charge a provider's non-claim made before 1.13.0, when grouping cut it at ` — ` to the bare quote it leads with:
    a disposal written then answers the whole sentence now. None for any other finding."""
    kind, where, text = charge(f) if f.get("kind") != "undisposed" else (None, None, "")
    if kind != "non-claim" or not text.startswith("(provider) ") or " — " not in text:
        return None
    return (kind, where, text.split(";")[0].split(" — ")[0].strip())


def answered(prior):
    """{charge: disposition} over every earlier review, the latest answer winning."""
    out = {}
    for r in prior:
        for f in r.get("findings", []):
            if f.get("disposition") and layer(f) == "objection":
                out[charge(f)] = f["disposition"]
    return out


def cmd_dispose(args):
    rid, _, idx = args.finding.rpartition("/")
    path = os.path.join(args.target, REVIEWS, rid + ".json")
    r = load(path)
    if not r or not idx.isdigit() or int(idx) >= len(r.get("findings", [])):
        raise SystemExit("no finding %s" % args.finding)
    f = r["findings"][int(idx)]
    if layer(f) == "observation":
        raise SystemExit("dispose: %s is an observation — an observation is a fact, not a charge; there is nothing to dispose" % args.finding)
    if bool(args.why) == bool(args.delegated):
        raise SystemExit("dispose: --why WHY --by NAME (a person's words) or --delegated WHY (no person read this; why it was handed off) — one of the two")
    if args.approved_in is not None and not re.match(r"^[\w.-]+:\S+$", args.approved_in):
        raise SystemExit("dispose: --approved-in %r: where the person agreed, as source:ID (a mangsang source, `source:at-63`) or KIND:REF" % args.approved_in)
    # a delegated disposal: no person read the finding (`by` stays null), but someone handed it off — `--by` with --delegated
    # names who (`delegated-by`), `--approved-in` where they said so. Refused until 1.14.0, so all twelve of guin-site review
    # a3c2's disposals read `by: null`, the owner's "뒷북 검토 진행" kept only in each reason's prose
    disp = {"as": args.as_, "why": args.why, "by": args.by} if args.why else \
        {"as": args.as_, "delegated": args.delegated, "by": None, **({"delegated-by": args.by} if args.by else {})}
    if args.approved_in:
        disp["approved-in"] = args.approved_in
    # the disposal carries the charge it answers, copied at disposal time: a person reading the review later sees (finding, reason)
    # side by side, without resolving indices across reviews to learn what was answered
    disp["finding_text"] = f["text"]
    disp["where"] = f["where"]
    if args.quote:
        disp["quote"] = args.quote
    elif f.get("kind") in ("contradiction", "anomaly") or f.get("record_quote") or f.get("tree_quote"):
        print("warning: this finding is grounded in quotes; a disposal that quotes nothing back is harder for the next reader to weigh (--quote QUOTE)")
    # one charge, one answer, written once: where the charge stands now — the latest review, which `follow` reads — or, when
    # the latest does not hold it, the copy named. Every other copy, in every review, is answered by it (`answered`); copying
    # the answer into each was "the same charge answered in 5 other place(s)" for one charge carried through five reviews
    rs = reviews(args.target)
    here_rid, here_i = rid, int(idx)
    if rs and rs[-1]["id"] != rid:
        j = next((j for j, g in enumerate(rs[-1].get("findings", [])) if layer(g) == "objection" and charge(g) == charge(f)), None)
        if j is not None:
            here_rid, here_i = rs[-1]["id"], j
            r, path = rs[-1], os.path.join(args.target, REVIEWS, rs[-1]["id"] + ".json")
    r["findings"][here_i]["disposition"] = disp
    save(path, r)
    first = r["findings"][here_i].get("first-seen")
    print("disposed %s as %s%s%s%s" % (args.finding, args.as_, (" (delegated%s%s)" % (" by %s" % args.by if args.by else ", nobody named as handing it off (--by NAME)",
                                                                                   "; approved in %s" % args.approved_in if args.approved_in else ""))
                                       if args.delegated else "",
                                       " — recorded at %s/%d, where the charge stands now" % (here_rid, here_i) if (here_rid, here_i) != (rid, int(idx)) else "",
                                       " — one answer for the charge first seen in %s" % first if first and first != here_rid else ""))
    return 0


EYES_KINDS = {"record-vs-tree": "a run's report (done, verified, touched, summary) and what the diff shows disagree",
              "plan-vs-code": "a plan sentence the code in the diff contradicts",
              "claim-unverified": "a `verified` check that could not have decided the claim it is cited for",
              "anomaly": "what a stranger would question in the tree itself — no record to quote, so `record_quote` is empty and `tree_quote` carries it"}
def grounded(f):
    """An eyes finding stands only on quotes: from both sides — the record and the tree — except an `anomaly`, which has no
    record to quote by definition and stands on the tree alone. The one rule for every place a finding is kept or dropped
    (the verify path once required a record quote of every finding and turned a true anomaly into an accept)."""
    needed = ("where", "tree_quote", "why") if f.get("kind") == "anomaly" else ("where", "record_quote", "tree_quote", "why")
    return f.get("kind") in EYES_KINDS and all(str(f.get(k, "")).strip() for k in needed)


LENSES = {"contract": "Read only the diff against the contract (plan or the given document). Ignore the run records.",
          "record": "Read only the run records against the tree. Ignore the plan.",
          "fresh": "You know nothing of the intent. Report what a stranger reading this diff would question — anomalies with a tree quote."}
FINDING = {"type": "object", "additionalProperties": False, "required": ["kind", "where", "record_quote", "tree_quote", "why"],
           "properties": {"kind": {"enum": sorted(EYES_KINDS)}, "where": {"type": "string"}, "record_quote": {"type": "string"},
                          "tree_quote": {"type": "string"}, "why": {"type": "string"}}}
EYES_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["findings"], "properties": {"findings": {"type": "array", "items": FINDING}}}
REVIEW_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["verdict", "findings"],
                 "properties": {"verdict": {"enum": ["accept", "reject"]}, "findings": {"type": "array", "items": FINDING}}}


def verify_packet(request):
    """A chongdae build request (stage verify) -> the eyes packet for a verdict. The contract, what the task touched (as a diff), the
    builder's own report. The reader is told what decides: a sentence the code contradicts, or a claim no check could have decided."""
    target = request["target"]
    touched = [t for t in request.get("touched") or [] if not t.startswith(record_paths(target))]
    diff = ""
    for path in touched:
        d = git(target, "diff", "HEAD", "--", path)
        if d:
            diff += d
        elif os.path.isfile(os.path.join(target, path)) and os.path.getsize(os.path.join(target, path)) < 40000:
            diff += "+++ %s (new file)\n" % path + io.open(os.path.join(target, path), encoding="utf-8", errors="replace").read() + "\n"
    # what chongdae left out of `touched` by rule — the environment (hunsu's files) and the products' records — with its diff: a
    # task whose whole work is `hunsu lock` or `mangsang confirm` has `touched: []`, and a verifier told nothing about these read
    # the changed tree as an undeclared edit (four rejects in five on the same task, guin-site 2026-09-28)
    excluded = [p for p in ((request.get("excluded") or {}).get("record-paths") or []) if not p.startswith(RUNS + "/")]
    excluded_diff = "".join(git(target, "diff", "HEAD", "--", p) or "" for p in excluded)
    domain = request.get("domain")
    return {"artifact-type": "dwitbuk/eyes-request@1", "mode": "verify", "target": target, "run": request.get("run"), "task": request.get("task"),
            "brief": request.get("brief", ""), "contract": request.get("contract", {}), "checks": request.get("checks", []),
            "tests": request.get("tests", []), "touched": touched, "touched_since": request.get("touched_since", []), "diff": diff[:80000], "built": request.get("built"),
            **({"excluded": excluded, "excluded_diff": excluded_diff[:40000]} if excluded else {}),
            "attempts": request.get("attempts", []), "kinds": EYES_KINDS, **({"domain": domain} if domain else {}),
            # whose words these are, in the data itself: a verifier read the tests writer's "I did not run the whole suite" as
            # `built.non-claims` and rejected a build whose full suite had passed (guin-site run a0ec, cache-build, 10-15)
            **({"tests_non_claims": {"whose": TESTS_NON_CLAIMS_WHOSE, "statements": request["tests_non_claims"]}} if request.get("tests_non_claims") else {}),
            **({"checked": request["checked"]} if request.get("checked") else {}),
            **({"recheck": request["recheck"]} if request.get("recheck") else {}),
            "instructions": ("You are the verifier of one slice, before its gate. The checks passed; that is a premise, not a verdict. Read the contract "
                             "sections against the diff (Read the touched files and the tests under target when the diff is not enough). "
                             "Reject when a contract sentence is contradicted by the code, or when a claim in `built.verified` could not have been "
                             "decided by the check cited (a test that does not exercise the sentence, a key that selects nothing). "
                             "`touched` is what the builder changed; `touched_since` changed after it answered (a person's plan edits, say) and is not the builder's — do not hold the builder's report to it. "
                             "`built.non-claims` are the builder's own list of what it did not check"
                             + (", and `tests_non_claims.statements` the tests writer's (" + ", ".join(sorted(request["tests_non_claims"]))
                                + ") about its own tests — what they do not decide. `tests_non_claims` is never the builder's report: a finding about "
                                "the builder (`where` naming `built`) may not quote it as the builder's, and a sentence found only there is not "
                                "something the builder said" if request.get("tests_non_claims") else "")
                             + ". Read the code at each — a contract sentence a non-claim leaves undecided and the code "
                             "contradicts is a finding. Your accept is recorded as having read them; they are not charged again after it. "
                             + ("`checked` lists commands chongdae itself ran on the tree and saw exit 0 (`tail` is their output's end; `changed_since` "
                                "the files changed after) — evidence chongdae observed, unlike a claim in `built.verified`: a check it shows passing "
                                "is not a finding that it fails, unless what changed since could break it; whether it decides the sentence is still "
                                "yours to judge. " if request.get("checked") else "")
                             + ("`excluded` lists files under the products' record paths that differ from HEAD — the environment (hunsu's manifest, lock and "
                                "judgments) and records such as mangsang/ — which are never in `touched`, by rule, not by omission: a change there is not an "
                                "undeclared edit and no record-vs-tree finding. When the brief or contract says the task's work is that change (update a plugin, "
                                "lock the environment, relate concepts), read it in `excluded_diff` as the slice's work and verify it against them. "
                                if excluded else "") +
                             "Every finding quotes both sides: `record_quote` from the contract or the builder's report, `tree_quote` from the diff or a file — "
                             "put each quoted sentence in backticks, verbatim, and name in `where` the field it is from (`built.verified[0]`, "
                             "`contract.Q1`): a quoted span the named field does not hold is dropped as unfounded — "
                             "except an `anomaly` (something wrong in the tree that no record speaks to), which quotes the tree only. "
                             "No grounded finding, no reject — and no finding means accept. A behavior the code had before this slice, which the brief or "
                             "contract says to carry over as it was, is not a finding against this slice: say it in `summary` if it looks wrong. "
                             "Do not review style. Change no files."
                             + (" This is a re-verification: the last verdict rejected this slice with `recheck.findings`, and `recheck.changed_since` "
                                "lists the files changed since that verdict. Check two things only: that each of those findings is resolved (still true: "
                                "report it again, quoted), and that what changed since breaks no contract sentence. What was there at the last verdict "
                                "and is unchanged was read then — do not read it again for new findings; say in `summary` if something outside "
                                "that scope still looks wrong." if request.get("recheck") else "")
                             + (" This slice is a refactoring: placement may change, behavior and explanation may not. Also reject when a docstring, a comment or a "
                                "public name that the diff removes does not reappear where its code went (record_quote: the removed text from the diff's `-` lines; "
                                "tree_quote: the new place, or the `+` lines that lack it), or when a moved function's body differs from the original beyond the move."
                                if domain == "refactor" else ""))}


TESTS_NON_CLAIMS_WHOSE = "the tests writer's statements about its own tests — not the builder's report (that is `built`)"
QUOTE_SPAN = re.compile(r"`([^`\n]+)`")
FIELD_PATH = re.compile(r"^[A-Za-z_][\w-]*(?:\.[\w-]+|\[\d+\])*$")
OTHER_HANDS = ("tests_non_claims", "checked")   # the tests writer's words and chongdae's own runs: never the builder's report
PACKET_META = ("artifact-type", "mode", "target", "kinds", "instructions")   # what dwitbuk wrote, not the record


def strings(v):
    """Every string leaf of a JSON value."""
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from strings(x)


def flat(text):
    return " ".join(str(text).split())


def quoted_spans(f, packet):
    """The verbatim spans a finding's `record_quote` puts in backticks — field names (`built.non-claims`) left out, they are
    where, not what. Trailing punctuation the eyes add around a sentence is struck."""
    out = []
    for sp in QUOTE_SPAN.findall(str(f.get("record_quote") or "")):
        sp = flat(sp).strip(" \"'\u201c\u201d\u2018\u2019")
        sp = sp.rstrip(".,;:") if len(sp.rstrip(".,;:")) >= 4 else sp
        if len(sp) < 4 or (FIELD_PATH.match(sp) and re.split(r"[.\[]", sp)[0] in packet):
            continue
        out.append(sp)
    return out


def unfounded(f, packet):
    """Why a verify finding stands on nothing in the request, or None. Each backticked span of its `record_quote` must occur in
    the request: in the builder's own fields, the contract, the brief, or the files the slice touched, its tests and the files
    `where` names (the eyes Read them) — or, only
    when `where` does not name `built`, in another hand's (`tests_non_claims`, `checked`). A span found nowhere, or found only
    in the tests writer's words while the finding charges the builder, is unfounded (guin-site run a0ec, cache-build: "`I did
    not run the whole suite.`" quoted as `built.non-claims` was `tests_non_claims.cache-tests[8]`; the builder had run the full
    suite and it passed). And a `claim-unverified` about a check chongdae itself ran on this tree and saw exit 0 (`checked`,
    nothing changed since) is unfounded unless it quotes the contract sentence the check is said not to decide — whether the
    check ran and passed is what chongdae observed; whether it decides a sentence stays the eyes'."""
    own = [s_ for k, v in packet.items() if k not in OTHER_HANDS + PACKET_META for s_ in strings(v)]
    target = packet.get("target") or "."
    named = re.findall(r"[\w.-]+(?:/[\w.-]+)*\.\w+", str(f.get("where") or ""))   # `plan/PLAN.md:260-264; src/a.ts:36`: a file the eyes Read
    for rel in list(packet.get("tests") or []) + list(packet.get("touched") or []) + named:
        path = os.path.join(target, rel)
        if os.path.realpath(path) != os.path.realpath(target) and not os.path.realpath(path).startswith(os.path.realpath(target) + os.sep):
            continue
        if os.path.isfile(path) and os.path.getsize(path) < 200000:
            own.append(io.open(path, encoding="utf-8", errors="replace").read())
    own = flat("\n".join(own))
    other = flat("\n".join(s_ for k in OTHER_HANDS for s_ in strings(packet.get(k))))
    charges_builder = re.search(r"\bbuilt\b", str(f.get("where") or "")) is not None
    spans = quoted_spans(f, packet)
    for sp in spans:
        if sp in own:
            continue
        if sp in other:
            if charges_builder:
                return "quotes `%s` as the builder's, but it is only in %s — %s" % (
                    sp, " / ".join(k for k in OTHER_HANDS if sp in flat("\n".join(strings(packet.get(k))))), TESTS_NON_CLAIMS_WHOSE)
            continue
        return "quotes `%s`, which is nowhere in the request" % sp
    if f.get("kind") == "claim-unverified":
        contract = flat("\n".join(strings(packet.get("contract"))))
        about_contract = any(sp in contract for sp in spans)
        said = flat("%s %s" % (f.get("where") or "", f.get("record_quote") or ""))
        for c in packet.get("checked") or []:
            cmd = flat(" ".join(c["command"]) if isinstance(c.get("command"), list) else c.get("command") or "")
            if cmd and c.get("exit") == 0 and not c.get("expect") and not c.get("changed_since") and cmd in said and not about_contract:
                return "chongdae itself ran `%s` on this tree and saw exit 0 (`checked`), nothing changed since" % cmd
    return None


def weigh(out, packet):
    """A verify answer, its grounded findings weighed against the request: an unfounded one (`unfounded`) is dropped from the
    verdict's grounds and kept beside it under `unfounded`, with why; a reject that rested only on unfounded findings is an
    accept, and says so in `summary`."""
    kept, notes = [], []
    for f in out.get("findings") or []:
        why = unfounded(f, packet)
        (notes.append(dict(f, unfounded=why)) if why else kept.append(f))
    out["findings"] = kept
    if notes:
        out["unfounded"] = notes
        if out.get("verdict") == "reject" and not kept:
            out["verdict"] = "accept"
            out["summary"] = "rejected only on unfounded finding(s) (%s); counted as accept%s" % (
                "; ".join(n["unfounded"] for n in notes), " — the eyes said: " + out["summary"] if out.get("summary") else "")
    return out


def cmd_eyes(args):
    """The judge pattern: dwitbuk packs what a reader would need and validates the answer; the reading is a fresh, read-only host session."""
    target = args.target
    if args.mode == "request":
        prior = reviews(target)
        base = args.since or (prior[-1]["since"] if prior else None)   # what the latest review covered
        head = (git(target, "rev-parse", "HEAD") or "no-git").strip()
        left_out = [p.rstrip("/") + ("*" if not p.endswith("/") else "") if p == "hunsu" else p.rstrip("/") for p in record_paths(target) if p != "mangsang/"]   # records and machine/host state; everything a run may touch stays in — mangsang/ relations included: a confirmed quote is a claim about the tree
        excl = ["--", "."] + [":!" + x for x in left_out]
        diff = (git(target, "diff", base, *excl) if base else git(target, "diff", *excl)) or ""
        names = [n.strip().replace("\\", "/") for n in ((git(target, "diff", "--name-only", base, "--", ".") if base else "") or "").splitlines()]
        untracked = [n.strip().replace("\\", "/") for n in (git(target, "ls-files", "--others", "--exclude-standard", "--", ".") or "").splitlines()]
        new_files = {}   # a diff shows nothing of files git does not track yet; the change includes them
        for n in untracked:
            if n and not n.startswith(tuple(x.rstrip("*") for x in left_out)) and os.path.getsize(os.path.join(target, n)) < 20000:
                new_files[n] = io.open(os.path.join(target, n), encoding="utf-8", errors="replace").read()
        moved = {n.split("/")[-2] for n in names + untracked if "/" in n}   # run dirs with a changed or new file since base
        runs_ = []
        for name, plan, state in runs(target):
            if base and name not in moved and state.get("status") == "complete":
                continue   # untouched since `since`: its record was already in front of eyes
            runs_.append({"run": name, "goal": plan.get("goal"), "status": state.get("status"),
                          "tasks": [{"id": t.get("id"), "brief": t.get("brief"), "closes": t.get("closes", []), "checks": t.get("checks", []),
                                     "state": {k: v for k, v in state.get("tasks", {}).get(t.get("id"), {}).items() if k in ("status", "confirmed", "accepted", "touched", "attempts", "response")}}
                                    for t in plan.get("tasks", [])],
                          "non-claims": state.get("non-claims", [])})
        plan_path = os.path.join(target, args.contract) if args.contract else os.path.join(target, "plan", "PLAN.md")
        plan_text = io.open(plan_path, encoding="utf-8").read() if os.path.exists(plan_path) else ""
        open_ = [{"kind": kind_of(f), "where": f["where"], "text": f["text"]} for _, f in open_charges(target)[1]]
        packet = {"artifact-type": "dwitbuk/eyes-request@1", "target": os.path.abspath(target).replace(os.sep, "/"), "since": base, "head": head,
                  "diff": diff[:80000], "diff_truncated": len(diff) > 80000, "diff_leaves_out": left_out, "new_files": new_files,
                  "runs": runs_, "plan": plan_text[:40000], "open_findings": open_,
                  "kinds": EYES_KINDS,
                  "instructions": ("You are late eyes on a change nobody read as a pull request. Read the diff against the run records and the plan. "
                                   "Report only contradictions you can quote from both sides: `record_quote` is a sentence from a run's record or the plan, "
                                   "`tree_quote` is a line from the diff (or a file under target you Read). `where` names the run/task or plan section and the file. "
                                   "Absence from the diff is not evidence about paths in `diff_leaves_out`. "
                                   "No quote from both sides, no finding. Do not repeat `open_findings`. Do not review style or suggest improvements. Change no files.")}
        os.makedirs(args.out, exist_ok=True)
        for lens in args.lens or [None]:
            if lens and lens not in LENSES:
                raise SystemExit("unknown lens %s (known: %s)" % (lens, ", ".join(LENSES)))
            doc = dict(packet, lens=lens, instructions=packet["instructions"] + (" Lens: " + LENSES[lens] if lens else ""))
            save(os.path.join(args.out, "eyes-%s-request.json" % lens if lens else "eyes-request.json"), doc)
        print("eyes packet(s) -> %s (%s; diff %d chars, %d runs, contract %d chars, %d open findings). Run eyes_worker.py on each, then `eyes consume --dir %s`"
              % (args.out, ", ".join(args.lens) if args.lens else "no lens", len(diff), len(runs_), len(plan_text), len(open_), args.out))
        return 0
    # consume: validated findings go into the latest review as `contradiction`; the rejected ones are printed, not stored
    prior = reviews(target)
    if not prior:
        raise SystemExit("no review to add to — `dwitbuk review` first")
    answers = [load(os.path.join(args.dir, n)) for n in sorted(os.listdir(args.dir)) if n.startswith("eyes") and n.endswith("-response.json")]
    if not any("findings" in a for a in answers):
        raise SystemExit("no eyes*-response.json with `findings` in %s" % args.dir)
    kept, rejected, quoted = [], [], set()
    for f in (f for a in answers for f in a.get("findings", [])):
        if not grounded(f):
            rejected.append(json.dumps(f, ensure_ascii=False)[:160])
            continue
        key = (f["kind"], " ".join(str(f["tree_quote"]).split()))
        if key in quoted:
            continue   # two lenses quoting the same line found the same thing; one finding
        quoted.add(key)
        if f["kind"] == "anomaly":
            kept.append({"kind": "anomaly", "where": f["where"], "text": "%s — tree: \u201c%s\u201d" % (f["why"], f["tree_quote"])})
        else:
            kept.append({"kind": "contradiction", "where": f["where"], "text": "%s: %s — record: \u201c%s\u201d — tree: \u201c%s\u201d" % (f["kind"], f["why"], f["record_quote"], f["tree_quote"])})
    r = prior[-1]
    have = {identity(f) for f in r["findings"]}
    kept = [f for f in kept if identity(f) not in have]
    r["findings"] += kept
    save(os.path.join(target, REVIEWS, r["id"] + ".json"), r)
    for f in kept:
        print("  %-13s  %s — %s" % (f["kind"], f["where"], f["text"][:160]))
    for line in rejected:
        print("  rejected (no quote from both sides / unknown kind): %s" % line)
    print("eyes: %d finding(s) added to %s · %d rejected" % (len(kept), r["id"], len(rejected)))
    return 0


def names_path(f, path):
    """Whether a finding's `where` or `files` names this path: as a whole token (`src/a.html:12`, `doc.md#Heading`, a list
    `a.py, b.py`), never as a prefix of a longer name (`a.py` does not name `a.pyc` or `lib/a.py`)."""
    if path in (f.get("files") or []):
        return True
    return re.search(r"(?<![\w./-])" + re.escape(path) + r"(?![\w/-]|\.\w)", str(f.get("where", ""))) is not None


def cmd_follow(args):
    rid, open_ = open_charges(args.target)   # the open set is the latest review; observations are facts, not debt — not listed, not counted
    open_ = [(rid, i, f) for i, f in open_]
    path = None
    if args.path:
        path = os.path.relpath(os.path.abspath(args.path), os.path.abspath(args.target)) if os.path.isabs(args.path) else os.path.normpath(args.path)
        path = path.replace(os.sep, "/")
        every, open_ = len(open_), [o for o in open_ if names_path(o[2], path)]
    if args.brief:
        # a reader's line at its first look at a file (jokbo `reads`): the first charge, cut, and a count — or nothing at all,
        # so a reader is never told "0". Full outputs pasted into a context were ignored; the whole charge stays in plain `follow`
        if not args.path:
            raise SystemExit("--brief answers for one file: give --path")
        if open_:
            f = open_[0][2]
            text = " ".join(str(f["text"]).split())
            print("%d open objection(s) on this file: %s \u2014 %s" % (len(open_), kind_of(f), text if len(text) <= 120 else text[:119].rstrip() + "\u2026"))
            if len(open_) > 1:
                print("+%d more (`dwitbuk follow --path %s`)" % (len(open_) - 1, path))
        return 1 if open_ else 0
    # whole, grouped by kind: a disposal round reads the charge itself here, not in reviews/*.json
    kinds = {}
    for o in open_:
        kinds.setdefault(kind_of(o[2]), []).append(o)   # a carry under the kind of the charge it carries
    for kind, group in kinds.items():
        print("%s (%d)" % (kind, len(group)))
        for rid, i, f in group:
            print("  open  %s/%d  %s" % (rid, i, f["where"]) + ("  (carried: raised in %s, first seen %s)" % (f["raised-in"], f.get("first-seen")) if f.get("raised-in") else ""))
            print("        %s" % f["text"])
            if f.get("files"):
                print("        files: %s" % ", ".join(f["files"]))
            for q in ("record_quote", "tree_quote"):
                if f.get(q):
                    print("        %s: \u201c%s\u201d" % (q.split("_")[0], f[q]))
    print("undisposed findings: %d" % len(open_) + (" naming %s (%d in all)" % (path, every) if path else ""))
    return 1 if open_ else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dwitbuk", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("review", "dispose", "follow", "eyes"):
        p = sub.add_parser(name)
        p.add_argument("--target", default=".")
        if name == "eyes":
            p.add_argument("mode", choices=["request", "consume"])
            p.add_argument("--out", default="dwitbuk-eyes")
            p.add_argument("--dir", default="dwitbuk-eyes")
            p.add_argument("--since", default=None)
            p.add_argument("--contract", default=None, help="request: a document to read the diff against instead of plan/PLAN.md (a spec, a PR text)")
            p.add_argument("--lens", action="append", default=None, help="request: one packet per lens — %s" % ", ".join(LENSES))
        if name == "review":
            p.add_argument("--since", default=None)
        if name == "follow":
            p.add_argument("--path", default=None, help="only open objections whose `where` or `files` name this file (relative to --target)")
            p.add_argument("--brief", action="store_true", help="with --path: at most two lines (the first charge cut at ~120 chars, then +N more); nothing open: no output, exit 0")
        if name == "dispose":
            p.add_argument("finding")
            p.add_argument("--as", dest="as_", choices=["accepted", "dismissed"], required=True)
            p.add_argument("--why", default=None, help="a person's words")
            p.add_argument("--by", default=None, help="with --why: the person whose words they are; with --delegated: who handed the finding off (`delegated-by`)")
            p.add_argument("--approved-in", dest="approved_in", default=None, metavar="SOURCE:ID", help="where the person agreed (a mangsang source, `source:at-63`)")
            p.add_argument("--delegated", default=None, help="no person read this finding: why it was handed off (recorded as such, like a gate)")
            p.add_argument("--quote", default=None, help="a verbatim quote from the record or the tree that grounds this disposal")
    args = ap.parse_args(argv)
    return {"review": cmd_review, "dispose": cmd_dispose, "follow": cmd_follow, "eyes": cmd_eyes}[args.cmd](args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
