"""dwitbuk — placed eyes and a ledger of findings.

  review [--since COMMIT] [--target DIR]   collect `dwitbuk/findings@1` from the reporters the lock declares (hunsu.lock.json `reporters`),
                                           carry dispositions and recurrence from the last review, write reviews/<id>.json
  dispose <review>/<finding> --as accepted|dismissed --why WHY [--by NAME] [--quote QUOTE]
                                           the disposition copies the finding's own text and where at disposal time; --quote grounds it in the record/tree
  follow [--target DIR]                    findings from earlier reviews that nobody disposed of
  eyes request --out DIR [--since COMMIT] [--contract PATH] [--lens NAME]...
                                           late eyes: a packet (diff, run records, plan or contract, open findings) for a bounded read-only
                                           session; one packet per lens (contract | record | fresh), or one without
  eyes consume --dir DIR [--by WHO]        its answer, validated (a quote from the record and one from the tree, or no finding), into the latest review

The same eyes, placed earlier: as a chongdae `verifier` provider (`eyes_worker.py --request <chongdae request> --response ...`)
they read the task's contract, the files it touched and the builder's report, and answer `dwitbuk/review@1` — accept, or reject
with quoted findings — before the gate. The hands never place the eyes; the runner, the environment or a person does.

A review is a record like a run: `reviews/<id>.json`, committed. dwitbuk finds; it never fixes. It owns the *type* of a finding
(`dwitbuk/finding@1`: kind, where, text, files?) and the follow-through; products report on their own records in that type
(chongdae `report`, mangsang `impact --findings`, hunsu `check --findings` …), declared as `reporters` in hunsu.json and locked.
dwitbuk never reads a product's directory to compute findings. Kinds it adds itself:
  undisposed    a finding from an earlier review with no disposition yet
  unchanged     observations an earlier review holds in full (`seen-in`), counted here instead of written again
  contradiction late eyes: the record says one thing, the tree or the plan another — quoted from both sides
  anomaly       late eyes: what a stranger would question in the tree, with a tree quote only
  no-reporters  nothing is declared: the review is late eyes and dispositions only, and says so
  review-debt   the previous review still holds undisposed objections; the debt re-accuses itself until they are disposed

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
OBSERVATION_KINDS = {"delegated"}   # facts of the record, not charges: nobody should dispose them


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
    for key, entries in load(os.path.join(home, "plugins", "installed_plugins.json")).get("plugins", {}).items():
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
    """Run every reporter the lock declares; keep what answers in the type. A reporter that does not is itself a finding."""
    reporters = load(os.path.join(target, "hunsu.lock.json")).get("reporters") or {}
    findings = []
    if not reporters:
        findings.append({"kind": "no-reporters", "where": "hunsu.lock.json", "source": "dwitbuk",
                         "text": "no reporters declared (hunsu.json `reporters`, then lock): this review is late eyes and dispositions only; no run, relation or environment record was read"})
    for name, argv in reporters.items():
        try:
            done = subprocess.run(resolve_argv(target, argv, since), cwd=target, capture_output=True, text=True, encoding="utf-8", errors="replace")
            doc = json.loads(done.stdout)
            assert doc.get("artifact-type") == "dwitbuk/findings@1" and isinstance(doc.get("findings"), list)
        except (SystemExit, OSError, ValueError, AssertionError) as err:
            findings.append({"kind": "reporter-failed", "where": name, "source": "dwitbuk", "text": "reporter %s gave no dwitbuk/findings@1: %s" % (name, str(err)[:200])})
            continue
        for f in doc["findings"]:
            if f.get("kind") and f.get("where") is not None and f.get("text"):
                findings.append({"kind": f["kind"], "where": f["where"], "text": f["text"], "source": doc.get("source", name),
                                 **({"files": f["files"]} if "files" in f else {}),
                                 **({"layer": f["layer"]} if f.get("layer") in ("observation", "objection") else {})})
    return findings, sorted(reporters)


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

    raw, sources = collect(target, base if base != "no-git" else None)
    # type-level presentation: outside-run per directory, non-claims by first clause so repeats show — kinds, not products
    by_dir = {}
    groups = {}
    for f in raw:
        if f["kind"] == "outside-run" and f.get("files"):
            for p in f["files"]:
                by_dir.setdefault(os.path.dirname(p) or ".", []).append(os.path.basename(p))
        elif f["kind"] == "non-claim":
            key = re.sub(r"^\S+(?: \([^)]*\))?: ", "", f["text"]).split(";")[0]   # the first clause, whole — a cut sentence is a different sentence
            groups.setdefault(key, []).append(f["where"])
        else:
            findings.append(f)
    for folder, names in sorted(by_dir.items()):
        where = folder + "/" if folder != "." else ""
        shown = ", ".join(names[:4]) + (" … (+%d)" % (len(names) - 4) if len(names) > 4 else "")
        findings.append({"kind": "outside-run", "where": where + shown, "files": [os.path.join(folder, n).replace("\\", "/") if folder != "." else n for n in names],
                         "text": "%d file(s) changed since %s; no completed run recorded touching them" % (len(names), base or "the beginning")})
    for key, where in groups.items():
        findings.append({"kind": "non-claim", "where": ", ".join(sorted(set(where))), "text": key + ("  [x%d]" % len(where) if len(where) > 1 else "")})

    for f in findings:
        f["layer"] = layer(f)   # observation: a fact of the record; objection: a charge to dispose. Fail closed on unknown kinds.

    # review-debt: the previous review still holds undisposed objections — the new review accuses itself of the debt.
    # No gate, no block; the record just refuses to let the debt look settled.
    if prior:
        owed = sum(1 for f in prior[-1].get("findings", []) if layer(f) == "objection" and not f.get("disposition"))
        if owed:
            findings.append({"kind": "review-debt", "where": prior[-1]["id"], "source": "dwitbuk", "layer": "objection",
                             "text": "previous review %s still has %d undisposed objection(s)" % (prior[-1]["id"], owed)})

    # 5. the latest review is the open set. A finding seen again inherits its disposition; one that stopped recurring without
    #    a disposition is carried as `undisposed` so it cannot vanish silently. Older reviews are history — and only
    #    objections are debt: an observation that stops recurring simply stops; review-debt is recomputed each review.
    if prior:
        # a finding's identity is kind + where + its text: several stage-findings share one `where` (one quibble round), and
        # with (kind, where) alone only one of them inherited its disposition — the others came back as new debt
        last = {identity(f): f for f in prior[-1].get("findings", [])}
        carried = carried_observations(prior)
        kept, unchanged = [], {}
        for f in findings:
            old = last.pop(identity(f), None)
            if old:
                f["first-seen"] = old.get("first-seen", prior[-1]["id"])
                if old.get("disposition"):
                    f["disposition"] = old["disposition"]
            # an observation is a fact of the record; written in full once, it is counted after that, with the review that
            # holds it — a site's 120 relations confirmed by delegation were 58 KB of every review, forever
            written_in = prior[-1]["id"] if old else carried.get(identity(f), (None, None))[1]
            if written_in and layer(f) == "observation" and f.get("kind") != "unchanged":
                unchanged.setdefault(written_in, {})[f["kind"]] = unchanged.get(written_in, {}).get(f["kind"], 0) + 1
                continue
            kept.append(f)
        findings[:] = kept
        for rid_, kinds_ in sorted(unchanged.items()):
            n = sum(kinds_.values())
            findings.append({"kind": "unchanged", "layer": "observation", "where": rid_, "seen-in": rid_, "count": n,
                             "text": "%d observation(s) written in %s and unchanged since (%s)" % (n, rid_, ", ".join("%s %d" % kv for kv in sorted(kinds_.items())))})
        for (kind, where, _), old in last.items():
            if layer(old) != "objection" or kind == "review-debt":
                continue
            if not old.get("disposition") and kind != "undisposed":
                findings.append({"kind": "undisposed", "where": where, "layer": "objection",
                                 "text": "%s (first seen %s): %s" % (kind, old.get("first-seen", prior[-1]["id"]), old["text"][:80]),
                                 "first-seen": old.get("first-seen", prior[-1]["id"])})
            elif kind == "undisposed" and not old.get("disposition"):
                findings.append(old)

    import secrets, time
    rid = "review-%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), secrets.token_hex(2))   # sorts by time on one machine, still unique across machines
    save(os.path.join(target, REVIEWS, rid + ".json"), {"artifact-type": "dwitbuk/review@1", "id": rid, "since": base, "head": head, "reporters": sources, "findings": findings})
    obs = [(i, f) for i, f in enumerate(findings) if layer(f) == "observation"]
    for i, f in enumerate(findings):
        if layer(f) == "objection":
            print("  %-12s %d  %s — %s" % (f["kind"], i, f["where"], f["text"]))
    if obs:
        print("observations (facts of the record, not disposal debt): %d" % len(obs))
        for i, f in obs:
            print("  %-12s %d  %s — %s" % (f["kind"], i, f["where"], f["text"]))
    counts = {}
    for f in findings:
        if layer(f) == "objection":
            counts[f["kind"]] = counts.get(f["kind"], 0) + 1
    print("%s: %d objection(s) (%s), %d observation(s) since %s"
          % (rid, sum(counts.values()), ", ".join("%s %d" % kv for kv in sorted(counts.items())) or "none", len(obs), base or "the beginning"))
    return 0


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
                if f.get("seen-in") in by_id:
                    queue.append(by_id[f["seen-in"]])
            elif layer(f) == "observation":
                out.setdefault(identity(f), (f, r.get("id")))
    return out


def lock_commit(target):
    """The commit that first added hunsu.lock.json — where a project's record begins; None without git or a lock."""
    out = git(target, "log", "--diff-filter=A", "--format=%h", "--", "hunsu.lock.json") or ""
    return out.strip().splitlines()[-1] if out.strip() else None


def identity(f):
    """What makes a finding the same finding across reviews: its kind, where, and its text with the numbers that change
    between reviews (counts, `[xN]`, "since <rev>") struck — a reworded finding is a different one."""
    text = re.sub(r"\[x\d+\]|\b\d+ file\(s\)|since [0-9a-f]{7,}|\(first seen [^)]*\)", "", f.get("text", "")).strip()
    return (f.get("kind"), f.get("where"), text)


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
    disp = {"as": args.as_, "why": args.why, "by": args.by} if args.why else {"as": args.as_, "delegated": args.delegated, "by": None}
    # the disposal carries the charge it answers, copied at disposal time: (finding_text, why) is self-contained for a
    # later judge — no re-resolving indices across reviews to learn what was answered
    disp["finding_text"] = f["text"]
    disp["where"] = f["where"]
    if args.quote:
        disp["quote"] = args.quote
    elif f.get("kind") in ("contradiction", "anomaly") or f.get("record_quote") or f.get("tree_quote"):
        print("warning: this finding is grounded in quotes; a disposal that answers no quote is harder to audit later (--quote QUOTE)")
    f["disposition"] = disp
    save(path, r)
    print("disposed %s as %s%s" % (args.finding, args.as_, " (delegated)" if args.delegated else ""))
    return 0


EYES_KINDS = {"record-vs-tree": "a run's report (done, verified, touched, summary) and what the diff shows disagree",
              "plan-vs-code": "a plan sentence the code in the diff contradicts",
              "claim-unverified": "a `verified` check that could not have decided the claim it is cited for",
              "anomaly": "what a stranger would question in the tree itself — no record to quote, so `record_quote` is empty and `tree_quote` carries it"}
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
    touched = [t for t in request.get("touched") or [] if not t.startswith((RUNS + "/", REVIEWS + "/"))]
    diff = ""
    for path in touched:
        d = git(target, "diff", "HEAD", "--", path)
        if d:
            diff += d
        elif os.path.isfile(os.path.join(target, path)) and os.path.getsize(os.path.join(target, path)) < 40000:
            diff += "+++ %s (new file)\n" % path + io.open(os.path.join(target, path), encoding="utf-8", errors="replace").read() + "\n"
    return {"artifact-type": "dwitbuk/eyes-request@1", "mode": "verify", "target": target, "run": request.get("run"), "task": request.get("task"),
            "brief": request.get("brief", ""), "contract": request.get("contract", {}), "checks": request.get("checks", []),
            "tests": request.get("tests", []), "touched": touched, "touched_since": request.get("touched_since", []), "diff": diff[:80000], "built": request.get("built"),
            "attempts": request.get("attempts", []), "kinds": EYES_KINDS,
            "instructions": ("You are the verifier of one slice, before its gate. The checks passed; that is a premise, not a verdict. Read the contract "
                             "sections against the diff (Read the touched files and the tests under target when the diff is not enough). "
                             "Reject when a contract sentence is contradicted by the code, or when a claim in `built.verified` could not have been "
                             "decided by the check cited (a test that does not exercise the sentence, a key that selects nothing). "
                             "`touched` is what the builder changed; `touched_since` changed after it answered (a person's plan edits, say) and is not the builder's — do not hold the builder's report to it. "
                             "Every finding quotes both sides: `record_quote` from the contract or the builder's report, `tree_quote` from the diff or a file. "
                             "No quote from both sides, no finding — and no finding means accept. Do not review style. Change no files.")}


def cmd_eyes(args):
    """The judge pattern: dwitbuk packs what a reader would need and validates the answer; the reading is a fresh, read-only host session."""
    target = args.target
    if args.mode == "request":
        prior = reviews(target)
        base = args.since or (prior[-1]["since"] if prior else None)   # what the latest review covered
        head = (git(target, "rev-parse", "HEAD") or "no-git").strip()
        left_out = [RUNS, REVIEWS, ".mangsang", "hunsu*", ".claude"]   # records and machine/host state; everything a run may touch stays in — mangsang/ relations included: a confirmed quote is a claim about the tree
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
        open_ = [{"kind": f["kind"], "where": f["where"], "text": f["text"]} for f in (prior[-1]["findings"] if prior else []) if not f.get("disposition")]
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
        needed = ("where", "tree_quote", "why") if f.get("kind") == "anomaly" else ("where", "record_quote", "tree_quote", "why")
        if f.get("kind") not in EYES_KINDS or not all(str(f.get(k, "")).strip() for k in needed):
            rejected.append(json.dumps(f, ensure_ascii=False)[:160])
            continue
        key = (f["kind"], " ".join(str(f["tree_quote"]).split()))
        if key in quoted:
            continue   # two lenses quoting the same line found the same thing; one finding
        quoted.add(key)
        if f["kind"] == "anomaly":
            kept.append({"kind": "anomaly", "where": f["where"], "text": "%s — tree: \u201c%s\u201d" % (f["why"], f["tree_quote"]), "by": args.by})
        else:
            kept.append({"kind": "contradiction", "where": f["where"], "text": "%s: %s — record: \u201c%s\u201d — tree: \u201c%s\u201d" % (f["kind"], f["why"], f["record_quote"], f["tree_quote"]),
                         "by": args.by})
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


def cmd_follow(args):
    latest = reviews(args.target)[-1:]   # the open set is the latest review; observations are facts, not debt — not listed, not counted
    open_ = [(r["id"], i, f) for r in latest for i, f in enumerate(r.get("findings", [])) if not f.get("disposition") and layer(f) == "objection"]
    for rid, i, f in open_:
        print("  open  %s/%d  %-12s %s — %s" % (rid, i, f["kind"], f["where"], f["text"][:90]))
    print("undisposed findings: %d" % len(open_))
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
            p.add_argument("--by", default="unknown")
            p.add_argument("--contract", default=None, help="request: a document to read the diff against instead of plan/PLAN.md (a spec, a PR text)")
            p.add_argument("--lens", action="append", default=None, help="request: one packet per lens — %s" % ", ".join(LENSES))
        if name == "review":
            p.add_argument("--since", default=None)
        if name == "dispose":
            p.add_argument("finding")
            p.add_argument("--as", dest="as_", choices=["accepted", "dismissed"], required=True)
            p.add_argument("--why", default=None, help="a person's words")
            p.add_argument("--by", default=None)
            p.add_argument("--delegated", default=None, help="no person read this finding: why it was handed off (recorded as such, like a gate)")
            p.add_argument("--quote", default=None, help="a verbatim quote from the record or the tree that grounds this disposal")
    args = ap.parse_args(argv)
    return {"review": cmd_review, "dispose": cmd_dispose, "follow": cmd_follow, "eyes": cmd_eyes}[args.cmd](args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
