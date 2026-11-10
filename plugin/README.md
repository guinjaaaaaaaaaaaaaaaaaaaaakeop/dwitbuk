# dwitbuk

Placed eyes and a ledger of findings. The eyes read a contract, a diff and a record and speak only with a quote from
each side; who places them — the runner (a verifier before a gate), the environment, or a person (late eyes) — sets
the moment and the scope, and the author of the work never places them. A finding outlives the run that raised it, is
never judged by its author, and recurs until disposed. It never fixes; it finds.

## Install

Requires **Python 3.11 or later**. CLI and hook examples invoke `python3`; ensure that command resolves to a supported interpreter.

```
claude plugin marketplace add guinjaaaaaaaaaaaaaaaaaaaaakeop/dwitbuk
claude plugin install dwitbuk@dwitbuk
```

Codex: `codex plugin marketplace add guinjaaaaaaaaaaaaaaaaaaaaakeop/dwitbuk`, `codex plugin add dwitbuk@dwitbuk` (the
skill is `$dwitbuk:review`).

What a host installs is this directory and nothing else: the engine, the eyes worker, the hooks, the commands, the skill,
the manifests, this README and the LICENSE. The source repository's tests and development records stay in the repository.

## Shared guidance and hosts

[skills/review/SKILL.md](skills/review/SKILL.md) is the shared installed procedure for Claude Code and Codex. Both use
this same file. The Python CLI works from either host; replace these quoted paths with the plugin directory (the
installed copy, or `plugin/` in a source checkout) and the project directory:

```sh
python3 "/path/to/dwitbuk/dwitbuk.py" follow --target "/path/to/project"
python3 "/path/to/dwitbuk/eyes_worker.py" --help
```

The existing Claude `commands/` files invoke specific CLI actions and show their output. In particular,
`/dwitbuk:review` collects a review; it does not stand in for the entire review/disposition skill. Keep each action's
semantics when adapting entry points. Installation, permissions and hook configuration remain host-specific in their
manifests and host settings; `eyes_worker.py --host claude` or `--host codex` selects the worker adapter.

The source repository's maintainer guidance (its `AGENTS.md`) is not part of this plugin and is not injected into a
project that installs it.

### Plugin roots

A reporter's `{plugin:NAME}` uses [pluginroot.py](pluginroot.py), the family's shared resolver, vendored
byte-identical. `AGENT_HOST=codex` selects Codex; every other value selects Claude Code. Claude's home is
`HUNSU_CLAUDE_DIR`, else `CLAUDE_CONFIG_DIR`, else `~/.claude`; Codex's is `HUNSU_CODEX_DIR`, else
`AGENT_CODEX_HOME`, else `CODEX_HOME`, else `~/.codex`.

A `hunsu.local.json` link wins (relative to the project): its catalog's local payload, else `<link>/<NAME>`, else
the link itself. A missing link directory stops resolution. Otherwise `hunsu.json` declares the marketplace and
version; `hunsu.local.json`'s `dev` may override the marketplace. Claude uses a directory marketplace in place
(catalog, else `<path>/<NAME>`), else an existing install for this project's local scope, project scope, then user
scope. Codex requires an enabled `config.toml` entry and a cache directory with a plugin manifest: one copy wins;
several require one matching the declared version, otherwise resolution stops and names them.

In-place lookup reads the folder's own catalog, then its child's. A catalog outside the folder never chooses the
payload: each catalog and its source must stay inside the folder it is read for by real path, and a child's catalog
is read only when the child stays inside its parent. An escaping child is used as named, without its catalog.
A name that is not one path component makes no child; Codex cache paths require one-component marketplace and
plugin names. Install records are taken as the host keeps them, without reading catalogs inside the installed copy.

Without a declared marketplace, exactly one marketplace with an applicable installation may supply the copy;
several require a declaration. It never borrows another host's or marketplace's copy. A found version differing
from the declaration keeps its root and prints a note naming both versions and the root. For each reporter run,
that note also becomes a `plugin-version` objection, with the reporter's name as its `where`.

## Commands

Each runs the engine and shows its output. `dwitbuk.py --help` for arguments.

### `/dwitbuk:review`

Collect `dwitbuk/findings@1` from the reporters the lock declares (chongdae `report`, mangsang `impact --findings` and
`cq --findings`, hunsu `check --findings`, …), carry dispositions and recurrence, write `reviews/<id>.json`. No
reporters: the review says so and is late eyes and dispositions only.

New objections are listed in full. Charges still open from the previous review appear as one
`standing, unchanged since <previous>` group, with their finding indices and the `dispose` command;
`follow` lists them whole. With standing charges the last line separates `N new objection(s)` from
`S standing, unchanged since <previous>`, with their kind counts, and names `follow` and the person's
`dispose` command. Otherwise the last line remains `N objection(s)`.
A carried reporter failure with `heard-in` gets a line saying the reporter has answered since that review:
the failure is not current, and stays open until a person disposes it.

### `/dwitbuk:dispose`

Record a disposition of a finding — a person's (`--as accepted|dismissed --why "…" --by NAME`) or one no person read
(`--as … --delegated WHY --by NAME`, recording the person’s hand-off); observations refuse it (they are not debt). The
disposition copies the finding's own `text` and `where` at disposal time (`finding_text`), and `--quote` may add a
verbatim quote from the record or the tree that grounds it — so a person reading the review later sees the pair
(finding, reason) side by side and can weigh whether the reason addresses the finding, without resolving ids across
reviews. Disposing a quote-grounded finding (`contradiction`, `anomaly`) without `--quote` warns, not refuses.
`--by` names the person whose words `--why` carries. With `--delegated` no person read the finding, so `by` stays `null`;
`--by NAME` there names who handed it off (`delegated-by`) and `--approved-in source:ID` where they said so — a session
disposing at the person's request says whose request it was.
Both `--why` and `--delegated` require `--by`; without it the command refuses to write.
An agent never disposes a finding on its own judgment or records a delegation nobody gave.

### `/dwitbuk:follow`

The latest review's objections that nobody disposed of, each whole — `where`, the full text, `files` and the
record/tree quotes when the finding has them — grouped by kind with a count, behind the `<review>/<n>` handle `dispose`
takes. A carried charge is listed under the kind of the charge it carries, with `raised in <review>/<n>` and when it
was first seen. A carry with `heard-in` also says `reporter <where> has answered since <review>:
not a current failure; a person disposes it`. A disposal round reads the charges here, not in `reviews/*.json`. The last line stays `undisposed findings: N`;
the exit code is 1 while any is open. `follow --path FILE` (relative to `--target`) keeps only those whose `where` or
`files` name that file as a whole token (`src/a.html:12`, `doc.md#Heading`) — what is open on a file before editing it

`follow --path FILE --brief` is the same question as a reader's line: at most two lines — `N open objection(s) on this
file: <kind> — <text>` (the first charge, cut near 120 characters) and `+N more` when there are more — and nothing at
all (exit 0) when nothing is open on the file, so a reader is never told "0". This plugin declares it as the `note`
read in `reads` (beside `file`, the whole `follow --path`), which jokbo runs at the agent's first look at a file

### as chongdae's `verifier`

The worker prompt names the running copy's `skills/review/SKILL.md` by absolute path when it exists,
for both hosts and `--prompt-only`; the packet's `instructions` remain this request's whole procedure.
The packet and its request binding are unchanged.

Quote weighing reads every candidate file whole, with no size cap: the tests, touched files and files
named by `where`, restricted to regular files inside the target by real path. Backticked elided spans
(`…` or three or more dots, optionally bracketed) match pieces in order without overlap in one text:
one packet string field or one file. Pieces spread across texts do not match.
If a span is absent from everything read but a candidate could not be read, the finding stays with
`unchecked`, naming the span, each unreadable file and its exception type: it stands unweighed.
A reject counted as accept because its findings were unfounded carries an
`accepted only because the eyes' reject rested on finding(s) dropped as unfounded: …` non-claim
naming each kind and location. A reject with no grounded finding likewise says so and counts the
findings dropped for missing quotes. These notes are removed if the required-file rule below
turns the accept into no verdict.

The same eyes before a gate: `eyes_worker.py --request <chongdae request> --response ...` reads the task's contract,
touched files and the builder's report and answers `dwitbuk/review@1` — accept, or reject with quoted findings — plus
`worker` (host, model, turns, cost) with the whole stream kept as `<response>.transcript.jsonl`: an accept with no
findings is auditable (what did the eyes read?), not a bare word. The worker reads that stream back: what the eyes
read goes beside the verdict as `read` (`files` a Claude session opened with Read/Grep/Glob, `commands` a Codex session ran
with their exit codes, `answered-before-reading` when the first answer came before any of it), and an accept that read
nothing of the tree — or only the diff (`git diff`/`status`/`show`/`log`) while the contract names behaviour (the slice has
tests, or code among its files) — once the required files described below have been opened, stays an accept with a `non-claims` line saying so: "accepted without reading the tree …"
or "accepted without reading the touched files or the tests: the eyes read the diff only …". A second verifier on
cache-build (guin-site run a0ec) answered accept first, ran one `git diff`, and answered the same — 607 output tokens on the
input the first verifier rejected — and the record said only "accept". Declared as the `eyes` role in this plugin's
plugin.json (`roles`), so a project writes `"verifier": "dwitbuk:eyes"` in hunsu.json and the lock carries the argv;
or in the plan's `providers.verifier`. The builder never places it. The packet tells the eyes to read the hands'
own non-claims (`built.non-claims`, and the tests writer's `tests_non_claims`) against the code — an accept is recorded as
having read them, and they are not charged again — and, when chongdae ran commands itself (`take`/`retry --checked`),
that `checked` is evidence chongdae observed, unlike a claim in `built.verified`.

The packet's `touched` is the request's `touched` less `.chongdae/` and `.claude/`. A record path the task's scope names
— `mangsang/`, `hunsu.json` — reaches the eyes named, with its diff, under the same size cut. The diff is cut at 80000
characters; files without a git diff are added whole only below 40000 bytes. `not_in_diff`, present only when non-empty,
lists touched paths whose change is not wholly in that diff, in touched order: their section was cut or lies past the cut,
or a file without a git diff was too large. The eyes are told to Read them under target.

`must_open`, present only when non-empty, names each touched regular file whose current text the packet does not show
whole, in touched order. A modified file's diff shows hunks; a large change can be cut; a binary cannot be shown as text.
Small files dumped whole and uncut new-file text diffs need no separate opening. Deleted files and directories are not
in the list. The eyes are told to open every file in `must_open` under target before accepting, including on a recheck.
Opening means Read or Grep of that file, or a command that ran successfully (or has no recorded exit) and has a shell
word that, taken relative to the target unless absolute, resolves by real path to that file (`./a.py` and an absolute
or real path count). Git's view of the change, an echo or a listing does not count; nor does a directory search or Glob.

An accept whose recorded session did not open each required file is not an accept: `verdict: null`, `answered: "accept"`,
`unread` listing those paths, no findings, and a summary starting `not an accept:` that names them in backticks and keeps
the earlier summary. chongdae asks the verifier again. With no recorded session nothing counts as opened, and the summary
says so. A reject with a grounded, founded finding is unchanged. Once every required file was opened, or there are none,
the accept and its non-claims stand as described above.
`read` (`files`, `commands`, `answered-before-reading`) is a stable field a runner should keep with the verdict:
the recorded evidence for the required openings and the accept's non-claims.

`tests_non_claims` reaches the eyes as `{"whose": "the tests writer's statements about its own tests — not the builder's
report …", "statements": {task: [sentence, …]}}`, and the instructions say a finding about the builder may not quote it as
the builder's (a verifier quoted the tests writer's "I did not run the whole suite" as `built.non-claims` and rejected a
build whose full suite had passed). The answer is then weighed against the request: each backticked span of a finding's
`record_quote` must occur in the request — the builder's report, the contract, the brief, the touched files, the tests, a
file `where` names. A span found nowhere, or only in another hand's field (`tests_non_claims`, `checked`) while `where`
names `built`, makes the finding unfounded; so does a `claim-unverified` about a command `checked` shows chongdae ran with
exit 0 and nothing changed since, unless it quotes the contract sentence the check is said not to decide. Unfounded
findings leave the verdict's grounds and stay visible under `unfounded` (each with why); a reject that rested only on them
is counted as accept, said in `summary`, subject to the required openings above.

`checked` (from chongdae, stable): a list of `{"command": "python3 tests/run.py --all", "exit": 0, "tail": [last lines],
"at": time, "changed_since": [files changed after it ran]}`, plus `"expect": "fail"` and `"outcome"` on an expected red run
(`--checked-red`). A pass is `exit` 0 with no `expect`; `command` is the string chongdae ran (a list is joined with spaces)

### as chongdae's `reviewer`

The review placed by the runner: a review that waits to be asked for is never asked for (a site went 22 runs without
one). Declare `"reviewer": ["python3", "{plugin:dwitbuk}/dwitbuk.py", "review", "--target", "."]` in hunsu.json
`roles` (an argv, like `coherence` — not `dwitbuk:review`, which would be judged as a worker's prompt) and lock;
chongdae runs it when a run ends (`close`, `complete`), and `reviews/<id>.json` goes into that run's close commit. One
review per run, since the previous one's head

### SessionStart hook

When objections are open, the full line names the latest review, the distinct open count and kinds,
and the `follow` and `dispose` commands. A person disposes each; an agent never disposes one on its own.
Each charge counts once, under its own kind; carries are said as already in the count.

With a session id, the hook keeps the latest review and a digest of the open charges per session in
`.dwitbuk/session-start.json`, machine-local, retaining at most 64 sessions. The full line is said once
per session; later starts (resume, compact, clear) while nothing changed get a short line without the
count: `dwitbuk: <review>'s undisposed objection(s) are as this session was told — unchanged`,
followed by `follow` and the reminder that a person disposes each. A changed review or open set
makes the next line full again. With no session id, every start gets the full line and nothing is
written. Unreadable or unwritable state falls back to the full line and never fails the hook.

Nothing open, no reviews, or a worker session: silent, with nothing written. Under hunsu's probe
(`HUNSU_SURVEY=1`) it gives standing text describing these rules without an id, count or path,
and writes nothing.

### Stop hook

The eyes placed by the environment: when the project sets `settings.dwitbuk.stop-eyes: true` in hunsu.json (read
there, with this machine's overlay from hunsu.local.json on top; a lock that carries it still counts), a session that
tries to end with a dirty tree gets its diff read (lens `fresh`, the plan as contract if there is one). Current, bound
findings refuse the stop once and reach the session; when a review exists, they are added there first. A stale or
unmatched response, or a failed consume such as a busy review lock, says nothing was decided and does not block the stop.
One model call per stop with changes — the
team's switch, not the plugin's default. Inside a worker session (`AGENT_WORKER=1`: the eyes, a judge, a builder) the
hook does nothing, since the host runs the project's hooks in those sessions too

The stop hook launches the worker's default `claude` adapter, also when a Codex hook invokes it.
Explicit worker calls can choose `--host codex`; the hook does not automatically select it from the session host.

### `/dwitbuk:eyes`

`eyes request --contract PATH` reads the diff against that document (a spec, a PR text) instead of the default
`plan/PLAN.md`. Repeat `--lens` for several lenses: `--lens contract --lens record --lens fresh` writes one packet
per lens, named `eyes-contract-request.json`, `eyes-record-request.json` and `eyes-fresh-request.json` under `--out`.
Without `--lens`, the packet is `eyes-request.json`. Run `eyes_worker.py` for each packet, using the matching
`eyes-<lens>-response.json` filename, then `eyes consume --dir DIR`. `fresh` yields `anomaly` findings with a tree
quote only; other findings require both a record and a tree quote. Requests include the diff, run records, contract
and open findings; the worker reads them in a fresh host session. Claude's turn bound is described under [Limits](#limits).

Late-eyes packets carry a source fingerprint; answers carry the fingerprint of the complete request in `request`.
The worker checks source freshness before and after its call, and `consume` checks the paired request, target, answer
binding and current source before writing any finding. A missing binding, replaced request, different target or changed
source refuses the whole consume: create a fresh request and rerun the eyes. This also applies to older unbound answers.
`--prompt-only` includes the required request fingerprint in the answer schema for a native reader. Source comparison
uses contents, executable bits and symlinks of git-visible files, including initialized submodules and directly nested
ignored repositories; without git it scans the tree. The selected contract and run records read into a late-eyes packet
are included explicitly. The binding covers what the packet packed from each run: its goal and status, the packed
tasks and non-claims. A `did`, a new task or a new run does not stale it; a change to a packed run's goal or status,
a packed task or non-claim does. Other records and the packet output directory are excluded, so recording a review does not stale itself. Use a dedicated packet directory, never a
source directory. A repository below an ignored parent directory is not discovered automatically.

The packet also names the review it was bound to. `consume` adds findings there while it is the latest and no
completed run recorded it at close, or into the latest eyes review already made for that bound review. Otherwise it
writes a new review naming the bound review in `eyes-of`, carrying the latest review's open charges and keeping its
`since` and `head`. A packet packed when no review existed is bound to none: its findings go into a new review whose
`eyes-of` is null, never into an ordinary review written after it. If no new findings remain, it writes nothing. A
closed run's close review is never rewritten.

`review`, `dispose` and `eyes` serialize mutations within one checkout. A competing command exits 4 and asks for a retry;
it cannot overwrite findings from the command in progress. Readers remain available, and JSON replacement is atomic.
The lock lives in `.dwitbuk/review.lock`; it is released when the process exits. Stop-eyes calls use separate scratch
directories under `.dwitbuk/` so overlapping calls cannot replace one another's packets or transcripts.

## Files in your project

| path | committed | what |
|---|---|---|
| `.dwitbuk/session-start.json` | no | machine-local session notification state, at most 64 sessions |
| `reviews/<id>.json` | yes | a review: `since`, `head`, findings (kind, where, text, layer, first-seen, disposition). Which reporters were asked is the lock's `reporters` |

A reporter that reads the state as it is now — the environment's drift, the model's stale relations and questions — says
so with `"standing": true` on its findings document. A standing finding it stops reporting is gone, not owed: it is not
carried as `undisposed` (only when that reporter answered this review; one that failed says nothing about what is gone).
A reporter that reads events over a range (a run's record since a commit) does not say it, and its findings are carried
as before. An eyes finding stands on quotes from both sides, or — an `anomaly` — on the tree alone: one rule, for the
review and for the verifier. A verify request's `excluded` (files under the record paths the runner left out of
`touched`) sends their names to the eyes, never their changes. They are not this task's work and may be another
open task's; a task whose work is a record change scopes it and has it in `touched`, with its diff. A change in an
excluded file is not an undeclared edit or a record-vs-tree finding, and the eyes do not verify it here. A verify
request with `recheck` (the last reject's findings, the files changed since)
is a re-verification: the eyes check that each finding is resolved and that what changed breaks no contract sentence,
and do not re-read what they read at the last verdict for new findings. An accepting session still opens every
file in `must_open`.
A verify request's `since` — the commit each repository the work is in started from, the project's (`.`) and any nested
one's by its path (`engine`) — is where the diff starts: each touched file is diffed in its own repository from there, so
work committed during the task is in the diff (`git diff HEAD` showed it as nothing and the file as new; sagoforce 10-26:
every task committed, six of them in repositories the workspace's git ignores, and the eyes accepted 24 empty packets).

The latest review is the open set: it holds every open charge, each once. A finding seen again — the same kind, `where`
and text, the changing counts struck — inherits its disposition, from whichever earlier review answered it; an objection
that stops recurring without one is carried as `undisposed`: the charge's own text, whole, with `carries` (the charge it
is), `first-seen`, and `raised-in` (`<review>/<n>`, where it was raised in full) — a reference, not a new objection in
words of its own. A reporter-failure carry keeps `heard-in`, the first review where that reporter answered again.
A carry carried again keeps its `raised-in`; a charge reported again while carried is the reporter's
finding, one copy, with its first sighting. One charge is answered once: `dispose` writes the answer where the charge stands
now (the latest review, whichever copy's handle it was given) and nowhere else; every other copy, in any review, is answered
by it, and the earlier reviews stay as they were written. An observation that stops recurring simply stops. An
observation reported again is counted as unchanged only when the previous review stood on it, in full
or through an `unchanged` line's `held`. That sorted list contains the observation identity hashes
(first 12 SHA-256 hex characters); `seen-in` names the reviews holding the full text.
An observation absent from the previous review is written in full when reported again.
An older `unchanged` line without `held` keeps the earlier rule: its `seen-in` chain holds all
observations it reaches. A fact whose text changed is new and written in full.
Older reviews (an `unchanged` line per holding review, `undisposed` text cut behind a
prefix, the answer copied into every review, a `review-debt` line) are read as they are. `eyes request` puts its packets
under `--out` (default `dwitbuk-eyes/`); `eyes_worker.py` writes the response at `--response` and the transcript beside
it. Use the same packet directory for both so `consume` can pair them. Keep reviewer packets in a subdirectory such as
`reviews/eyes/`, rather than alongside the top-level `reviews/<id>.json` ledger files.

## Kinds of finding

Every finding carries a `layer`. An **objection** is a charge someone must answer — it is disposal debt: `follow`
counts it, `dispose` closes it. An **observation** is a fact of the record — kept in the review (shown under its own
heading with a count), but never debt: `dispose` refuses it ("an observation is a fact, not a charge") and `follow`
neither lists nor counts it. `delegated` is an observation by kind; a reporter may mark any of its own findings
`"layer": "observation"` and is trusted. Everything else — unknown kinds included — is an objection: fail closed. A
`layer` a reporter gives that is neither word (`"info"`, `null`) is an objection too, never read as no layer; only a
layer left out is left to the kind's rules. A grouped `non-claim` (below) keeps the reporter's observation only when
every non-claim it stands for carries it; one with no layer, an invalid one or an objection among them leaves it an
objection, and the by-nature rule below never lifts a non-claim the reporter called an objection. Before 2.0.2 grouping
dropped the reporter's layer, and a typed observation was raised as a charge.

Whether a contract reader's own non-claim is a limit its role sets ("I did not read the tree", "I propose no answers")
or work it left undone ("I did not inspect the clause I was sent") is not classified: the record has no type that tells
them apart, and the second need not name its anchor. No role, provenance or wording lifts an untyped one; until the
engine that records non-claims types them, each stays a charge and a disposal answers it.

From reporters, in their own words: chongdae's `outside-run` (grouped per directory here), `unattributed`, `delegated`
(observation: `(verifier accepted)` / `(no verifier)`), `non-claim` (one per run and first clause, its tasks said in words —
`[tasks T1, T2]` — and, when other runs share the clause, each task beside its own run: `[tasks: T1 (run-a); also in other
runs: T3 (run-b)]`. 1.14.0 wrote `[task T1; in 2 runs: run-a, run-b]`, the runs sharing the clause text, and it read as T1
in both: a guin-site review named a task beside a run it was not in. Before 1.14.0 an `[xN]`, read as a count of tasks: "no
check decides this task [x2]" stood for eight tasks in two runs, and three charges were told as "5건". Each form is struck
from the charge's identity, so a review that wrote `[xN]` or 1.14.0's form still answers it, and a carry keeps neither; grouped across runs, a run's charge had a
new identity whenever a review's span changed and never kept its answer; a declared setting's note, and "no check
decides this task" on a task no check could decide by nature — a plan-domain task or one declaring `domain` doc/record, the
test writer's or the quibble's, or one whose files (touched and adopted, else its `scope`) are all documents (`.md`, `.txt`
…) or under the lock's `record-paths` — are observations, and such a charge raised before 1.14.0 is not carried; an objection answered in an earlier review
is carried with its answer and counted, not listed again),
`left-open` (a task open when its run closed, or rejected and never retried), `stage-finding` (what a role hired
before or after a task found, with its quote), `verifier-reject` (a verdict that stopped an attempt, quoted from both
sides), `delegation-stamp` (one reason stamped on 3+ judgments); mangsang's `stale`, `broken`, and from its `cq
--findings` reporter `cq-failed`, `cq-unanswerable`, `cq-unquestioned`; hunsu's `drift`, `unreviewed`. dwitbuk's own:
`undisposed` (an open charge carried, once, by reference), `unchanged` (observations earlier reviews hold in full,
counted in one line), `contradiction` and `anomaly` (late eyes), `no-reporters`, `reporter-failed` (a reporter gave no findings; a carry’s `heard-in` names its first later answer, so the failure is no longer current but remains open for a person), `plugin-version` (a reporter plugin differs from its declared version). `review-debt` (the
previous review's open count) is no longer written: the carried charges are the debt, each once, and the line restated
their count in every review; older reviews keep theirs, read as an observation.

`eyes_worker.py --prompt-only --request <file> --response <file>` prints the worker instructions, request and answer
schema and exits — for a session that dispatches its host's own subagent
instead of this worker (a `native:` provider in chongdae). The subagent's answer is then written by the session; this
worker never ran.

## Limits

- `--max-turns` bounds the Claude host only; `codex exec` has no turn limit to give, so a Codex eyes session ends when
  it ends.

- A review keeps each finding's `layer`, not who decided it. An open "no check decides this task" charge that no
  reporter repeats stops being carried once its tasks are uncheckable by nature (the rule written for charges raised
  before 1.14.0); a reporter's explicit objection on such a run, left undisposed and then no longer reported, stops there
  too. Telling the two apart needs the layer's provenance kept in the review — a new key, not part of 2.0.2.

- The engine never computes findings from another product's directory; it runs the reporters the lock declares and
  keeps what answers in the type. A reporter's `{plugin:NAME}` is the copy this project runs: a `hunsu.local.json`
  link, else the install from the marketplace `hunsu.json` declares for it (a directory marketplace in place) — never
  the first install record with that name, which on a machine with several projects is another project's older copy (a
  site's first review ran 1.1.0 reporters that way and reported 65 false `broken`/`drift`). It reads run records only
  to pack them for the eyes.
- A link, and a directory marketplace (which the host runs in place), are read as marketplace directories: the plugin's
  root is the source the catalog names (`.claude-plugin/marketplace.json`, else the local path in
  `.agents/plugins/marketplace.json`) when a plugin manifest is there — a source checkout keeps its payload in `plugin/`.
  Next it checks the child's catalog, subject to the real-path containment rules in [Plugin roots](#plugin-roots).
  Otherwise a link resolves to `<link>/<name>`, else the link, and a directory marketplace to
  `<path>/<name>`, else its install record.
- Reporter plugin-path lookup follows the selected host's enabled installations and the project's declarations;
  see [Plugin roots](#plugin-roots). A cache directory alone is not an enabled Codex installation.
- The engine reads records and git, never code for meaning. Meaning is read by late eyes — a fresh session with
  Read/Grep/Glob on Claude, or the Codex adapter's default read-only sandbox, and a fixed answer schema. Other than
  tree-only `anomaly` findings, a finding without a quote from each side is dropped on consume. `AGENT_CODEX_SANDBOX`
  can override the sandbox passed by the adapter. The reader uses the selected host's account.
- "Same kind of non-claim" is the first clause of the sentence, not a judgment — except a provider's own (`(provider) …`),
  kept whole: it leads with the contract sentence and says the gap after the dash, and cut there it read as a bare quote. A
  disposal written for the cut form (before 1.13.0) answers the whole sentence.

- `eyes_worker.py` starts its host session through `hostcall.py` — one host call for every worker of this family (hunsu's judge, mangsang's judge, dwitbuk's eyes,
  hacheong's members), vendored: the same file in each plugin, since a plugin imports no other plugin. The maintainers' copy check says when the copies drift.
  Each worker child starts as its own host (`AGENT_HOST=claude-code` or `codex`, `AGENT_WORKER=1`), without the parent
  session's ids (`CODEX_THREAD_ID`, `CLAUDE_CODE_SESSION_ID`, `CHONGDAE_SESSION`, …); the rest of the environment is kept.

- **What the eyes leave out of a diff** — the products' records and the environment — comes from the lock's `record-paths`
  (each plugin's `records` declaration); without it, the names as they were. An entry ending in `/` is a directory and
  everything in it; any other entry is that exact file — never a prefix (`hunsu.py` beside `hunsu.json` is source) and
  never a directory that took a declared file's name (`hunsu.json/child.py` is source). mangsang's `mangsang/` stays in a late-eyes
  diff on purpose: a confirmed quote is a claim about the tree. dwitbuk declares `records: ["reviews/", ".dwitbuk/"]`.

- **The late eyes' diff is bounded.** It is cut at 80000 characters and says so (`diff_truncated`); git is asked for no
  more once that is passed. Without a base, an unresolved merge conflict appears as git prints it: a combined
  `diff --cc` section, or the line `* Unmerged path PATH` for a modify/delete conflict. Paths are given to git in
  batches, and across batches a combined section can come after other paths' sections, where one git call would put it
  first; nothing is lost or repeated. Git output that dwitbuk cannot attribute to a path stops the request before any
  packet is written.

## Versions

Semver, and a version names one content: hosts copy a plugin at install and do not look again while the version stands.
**patch**: behavior or wording, every interface unchanged. **minor**: a new command, skill, field, hook or artifact key;
what exists keeps working. **major**: an artifact type, lock or record that other products read changes shape, or a
supported Python or host version is dropped (an `engines` floor rises, as `python` from 3.9 to 3.11 did in 2.0.0). Since
2.1.0 the source repository keeps this plugin in its `plugin/` directory and its catalogs name that directory; the
commands, hooks, roles and reads an installation runs keep their 2.0.2 names and arguments.
2.2.0 adds fields and one module and removes nothing: the verify packet's `not_in_diff` and the accept's unread
non-claim, a late-eyes packet's `source.records` (now a digest of what it packed; `true` from 2.1.0 keeps the old rule)
and `source.review`, a review's `eyes-of`, the `plugin-version` finding, and [pluginroot.py](pluginroot.py).
2.2.1 changes behavior only: no catalog outside a folder chooses its plugin root — a child that leaves the folder by real
path is used as named without reading its catalog, and a name that is not one path component makes no child or Codex
cache path (see [Plugin roots](#plugin-roots)).
2.3.0 adds the verify packet's `must_open` and an answer's `answered` and `unread`, and changes what an accept is: one
whose recorded session left a `must_open` file unopened comes back with no verdict, and the 2.2.0 unread non-claim is no
longer written (see [as chongdae's `verifier`](#as-chongdaes-verifier)). A verify packet no longer carries
`excluded_diff`: the excluded record paths reach the eyes by name, never with another task's changes.
2.4.0 adds a verify finding's `unchecked`, a carry's `heard-in`, an `unchanged` line's `held` and the SessionStart hook's
`.dwitbuk/session-start.json`, and changes `dispose`: `--why` and `--delegated` each need `--by`, and a disposal that names no
one is refused. Quote weighing reads whole files and matches elided spans piecewise; `review` lists new objections in full
and groups the standing ones; the hook's full line is said once per session (see [Commands](#commands)).
