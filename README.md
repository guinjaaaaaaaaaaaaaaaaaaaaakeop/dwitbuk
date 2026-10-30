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

## Shared guidance and hosts

[skills/review/SKILL.md](skills/review/SKILL.md) is the shared installed procedure for Claude Code and Codex. Both use
this same file. The Python CLI works from either host; replace these quoted paths with the plugin and project directories:

```sh
python3 "/path/to/dwitbuk/dwitbuk.py" follow --target "/path/to/project"
python3 "/path/to/dwitbuk/eyes_worker.py" --help
```

The existing Claude `commands/` files invoke specific CLI actions and show their output. In particular,
`/dwitbuk:review` collects a review; it does not stand in for the entire review/disposition skill. Keep each action's
semantics when adapting entry points. Installation, permissions and hook configuration remain host-specific in their
manifests and host settings; `eyes_worker.py --host claude` or `--host codex` selects the worker adapter.

[AGENTS.md](AGENTS.md) holds source-repository maintenance guidance. It is not automatically injected into a project
that installs this plugin. Codex discovers repository guidance along its project path. [Codex guidance loading](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
Claude Code's direct `AGENTS.md` support depends on version and settings; [CLAUDE.md](CLAUDE.md) contains only
`@AGENTS.md` as a compatibility import, so the maintainer rules still have one source. [Claude memory and imports](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools).

## Commands

Each runs the engine and shows its output. `dwitbuk.py --help` for arguments.

### `/dwitbuk:review`

Collect `dwitbuk/findings@1` from the reporters the lock declares (chongdae `report`, mangsang `impact --findings` and
`cq --findings`, hunsu `check --findings`, …), carry dispositions and recurrence, write `reviews/<id>.json`. No
reporters: the review says so and is late eyes and dispositions only

### `/dwitbuk:dispose`

Record a disposition of a finding — a person's (`--as accepted|dismissed --why "…" --by NAME`) or one no person read
(`--as … --delegated WHY`, recorded as a delegation like a gate); observations refuse it (they are not debt). The
disposition copies the finding's own `text` and `where` at disposal time (`finding_text`), and `--quote` may add a
verbatim quote from the record or the tree that grounds it — so a person reading the review later sees the pair
(finding, reason) side by side and can weigh whether the reason addresses the finding, without resolving ids across
reviews. Disposing a quote-grounded finding (`contradiction`, `anomaly`) without `--quote` warns, not refuses.
`--by` names the person whose words `--why` carries. With `--delegated` no person read the finding, so `by` stays `null`;
`--by NAME` there names who handed it off (`delegated-by`) and `--approved-in source:ID` where they said so — a session
disposing at the owner's request says whose request it was (before 1.14.0 the name was refused, and twelve delegated
disposals on a site read `by: null`, the owner's words only in each reason's prose)

### `/dwitbuk:follow`

The latest review's objections that nobody disposed of, each whole — `where`, the full text, `files` and the
record/tree quotes when the finding has them — grouped by kind with a count, behind the `<review>/<n>` handle `dispose`
takes. A carried charge is listed under the kind of the charge it carries, with `raised in <review>/<n>` and when it
was first seen. A disposal round reads the charges here, not in `reviews/*.json`. The last line stays `undisposed findings: N`;
the exit code is 1 while any is open. `follow --path FILE` (relative to `--target`) keeps only those whose `where` or
`files` name that file as a whole token (`src/a.html:12`, `doc.md#Heading`) — what is open on a file before editing it

`follow --path FILE --brief` is the same question as a reader's line: at most two lines — `N open objection(s) on this
file: <kind> — <text>` (the first charge, cut near 120 characters) and `+N more` when there are more — and nothing at
all (exit 0) when nothing is open on the file, so a reader is never told "0". This plugin declares it as the `note`
read in `reads` (beside `file`, the whole `follow --path`), which jokbo runs at the agent's first look at a file

### as chongdae's `verifier`

The same eyes before a gate: `eyes_worker.py --request <chongdae request> --response ...` reads the task's contract,
touched files and the builder's report and answers `dwitbuk/review@1` — accept, or reject with quoted findings — plus
`worker` (host, model, turns, cost) with the whole stream kept as `<response>.transcript.jsonl`: an accept with no
findings is auditable (what did the eyes read?), not a bare word. The worker reads that stream back: what the eyes
read goes beside the verdict as `read` (`files` a Claude session opened with Read/Grep/Glob, `commands` a Codex session ran
with their exit codes, `answered-before-reading` when the first answer came before any of it), and an accept that read
nothing of the tree — or only the diff (`git diff`/`status`/`show`/`log`) while the contract names behaviour (the slice has
tests, or code among its files) — stays an accept with a `non-claims` line saying so: "accepted without reading the tree …"
or "accepted without reading the touched files or the tests: the eyes read the diff only …". A second verifier on
cache-build (guin-site run a0ec) answered accept first, ran one `git diff`, and answered the same — 607 output tokens on the
input the first verifier rejected — and the record said only "accept". Declared as the `eyes` role in this plugin's
plugin.json (`roles`), so a project writes `"verifier": "dwitbuk:eyes"` in hunsu.json and the lock carries the argv;
or in the plan's `providers.verifier`. The builder never places it. The packet tells the eyes to read the hands'
own non-claims (`built.non-claims`, and the tests writer's `tests_non_claims`) against the code — an accept is recorded as
having read them, and they are not charged again — and, when chongdae ran commands itself (`take`/`retry --checked`),
that `checked` is evidence chongdae observed, unlike a claim in `built.verified`.

`tests_non_claims` reaches the eyes as `{"whose": "the tests writer's statements about its own tests — not the builder's
report …", "statements": {task: [sentence, …]}}`, and the instructions say a finding about the builder may not quote it as
the builder's (a verifier quoted the tests writer's "I did not run the whole suite" as `built.non-claims` and rejected a
build whose full suite had passed). The answer is then weighed against the request: each backticked span of a finding's
`record_quote` must occur in the request — the builder's report, the contract, the brief, the touched files, the tests, a
file `where` names. A span found nowhere, or only in another hand's field (`tests_non_claims`, `checked`) while `where`
names `built`, makes the finding unfounded; so does a `claim-unverified` about a command `checked` shows chongdae ran with
exit 0 and nothing changed since, unless it quotes the contract sentence the check is said not to decide. Unfounded
findings leave the verdict's grounds and stay visible under `unfounded` (each with why); a reject that rested only on them
is an accept, said in `summary`.

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

One fact when there is one: `dwitbuk: N undisposed objection(s) in <review> (kinds)` and the `follow`/`dispose`
commands. The kinds are counted by one rule, the same as `review`'s last line: each distinct open charge once (two copies
of one charge are one), under the kind of the charge it makes — a carry (`undisposed`) under the kind it carries — then how
many of them are carries, said as already in the count: `cq-failed 2, non-claim 10; 3 of them carried, already in the
count` (a bare "; 3 carried" can be read as three more). Open is: layer objection, no disposition, and no disposition of the same charge in
any review — what the reviews the runner placed still need from a person. Nothing open, no reviews, or a worker session:
silent. Never blocks, never writes. Under hunsu's probe (`HUNSU_SURVEY=1`, an empty project) it answers its standing text
— the line as a template (`N undisposed objection(s) in <review> (<kind> N, …)`, the two commands, when it is silent), no
id, count or path — so hunsu's judge reads what dwitbuk tells a session, not the nothing an empty project gets

### Stop hook

The eyes placed by the environment: when the project sets `settings.dwitbuk.stop-eyes: true` in hunsu.json (read
there, with this machine's overlay from hunsu.local.json on top; a lock that carries it still counts), a session that
tries to end with a dirty tree gets its diff read (lens `fresh`, the plan as contract if there is one). Current, bound
findings refuse the stop once and reach the session; when a review exists, they are added there first. A stale or
unmatched response, or a failed consume such as a busy review lock, says nothing was decided and does not block the stop.
One model call per stop with changes — the
team's switch, not the plugin's default. Inside a worker session (`AGENT_WORKER=1`: the eyes, a judge, a builder) the
hook does nothing, since the host runs the project's hooks in those sessions too

The stop hook currently launches the worker's default `claude` adapter, including when invoked by a Codex hook.
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
are included explicitly. Other records and the packet output directory are excluded, so recording a review does not stale itself. Use a dedicated packet directory, never a
source directory. A repository below an ignored parent directory is not discovered automatically.

`review`, `dispose` and `eyes` serialize mutations within one checkout. A competing command exits 4 and asks for a retry;
it cannot overwrite findings from the command in progress. Readers remain available, and JSON replacement is atomic.
The lock lives in `.dwitbuk/review.lock`; it is released when the process exits. Stop-eyes calls use separate scratch
directories under `.dwitbuk/` so overlapping calls cannot replace one another's packets or transcripts.

## Files in your project

| path | committed | what |
|---|---|---|
| `reviews/<id>.json` | yes | a review: `since`, `head`, findings (kind, where, text, layer, first-seen, disposition). Which reporters were asked is the lock's `reporters` |

A reporter that reads the state as it is now — the environment's drift, the model's stale relations and questions — says
so with `"standing": true` on its findings document. A standing finding it stops reporting is gone, not owed: it is not
carried as `undisposed` (only when that reporter answered this review; one that failed says nothing about what is gone).
A reporter that reads events over a range (a run's record since a commit) does not say it, and its findings are carried
as before. An eyes finding stands on quotes from both sides, or — an `anomaly` — on the tree alone: one rule, for the
review and for the verifier. A verify request's `excluded` (files under the record paths the runner left out of
`touched`) reaches the eyes with its diff and a sentence: left out by rule, not by omission — no record-vs-tree finding;
when the task's work is that change (update a plugin, lock the environment), it is verified as the slice's work. A verify
request with `recheck` (the last reject's findings, the files changed since)
is a re-verification: the eyes check that each finding is resolved and that what changed breaks no contract sentence,
and do not re-read what they read at the last verdict for new findings.
A verify request's `since` — the commit each repository the work is in started from, the project's (`.`) and any nested
one's by its path (`engine`) — is where the diff starts: each touched file is diffed in its own repository from there, so
work committed during the task is in the diff (`git diff HEAD` showed it as nothing and the file as new; sagoforce 10-26:
every task committed, six of them in repositories the workspace's git ignores, and the eyes accepted 24 empty packets).

The latest review is the open set: it holds every open charge, each once. A finding seen again — the same kind, `where`
and text, the changing counts struck — inherits its disposition, from whichever earlier review answered it; an objection
that stops recurring without one is carried as `undisposed`: the charge's own text, whole, with `carries` (the charge it
is), `first-seen`, and `raised-in` (`<review>/<n>`, where it was raised in full) — a reference, not a new objection in
words of its own. A carry carried again keeps its `raised-in`; a charge reported again while carried is the reporter's
finding, one copy, with its first sighting. One charge is answered once: `dispose` writes the answer where the charge stands
now (the latest review, whichever copy's handle it was given) and nowhere else; every other copy, in any review, is answered
by it, and the earlier reviews stay as they were written. An observation that stops recurring simply stops. An
observation is written in full once: the reviews after it count everything already on record in one `unchanged` line
whose `seen-in` lists the reviews that hold it, and read those to recognize it again — so a project's hundred delegated
relations are on record once, not in every review (they were 58 KB of every 96 KB review on a site), and what a review
writes in full is what is new since the last one. A fact whose text changed is a new fact, written in full: a relation
judged again is a new judgment. Older reviews (an `unchanged` line per holding review, `undisposed` text cut behind a
prefix, the answer copied into every review, a `review-debt` line) are read as they are. `eyes request` puts its packets
under `--out` (default `dwitbuk-eyes/`); `eyes_worker.py` writes the response at `--response` and the transcript beside
it. Use the same packet directory for both so `consume` can pair them. Keep reviewer packets in a subdirectory such as
`reviews/eyes/`, rather than alongside the top-level `reviews/<id>.json` ledger files.

## Kinds of finding

Every finding carries a `layer`. An **objection** is a charge someone must answer — it is disposal debt: `follow`
counts it, `dispose` closes it. An **observation** is a fact of the record — kept in the review (shown under its own
heading with a count), but never debt: `dispose` refuses it ("an observation is a fact, not a charge") and `follow`
neither lists nor counts it. `delegated` is an observation by kind; a reporter may mark any of its own findings
`"layer": "observation"` and is trusted. Everything else — unknown kinds included — is an objection: fail closed.

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
counted in one line), `contradiction` and `anomaly` (late eyes), `no-reporters`, `reporter-failed`. `review-debt` (the
previous review's open count) is no longer written: the carried charges are the debt, each once, and the line restated
their count in every review; older reviews keep theirs, read as an observation.

`eyes_worker.py --prompt-only --request <file> --response <file>` prints the worker instructions, request and answer
schema and exits — for a session that dispatches its host's own subagent
instead of this worker (a `native:` provider in chongdae). The subagent's answer is then written by the session; this
worker never ran.

## Limits

- `--max-turns` bounds the Claude host only; `codex exec` has no turn limit to give, so a Codex eyes session ends when
  it ends.

- The engine never computes findings from another product's directory; it runs the reporters the lock declares and
  keeps what answers in the type. A reporter's `{plugin:NAME}` is the copy this project runs: a `hunsu.local.json`
  link, else the install from the marketplace `hunsu.json` declares for it (a directory marketplace in place) — never
  the first install record with that name, which on a machine with several projects is another project's older copy (a
  site's first review ran 1.1.0 reporters that way and reported 65 false `broken`/`drift`). It reads run records only
  to pack them for the eyes.
- Reporter plugin-path lookup currently checks project-local links, then Claude's installation and marketplace
  records; it does not query Codex's plugin registry. For plugins installed only in Codex, supply their actual roots
  through `hunsu.local.json` links before resolving `{plugin:NAME}` reporter arguments.
- The engine reads records and git, never code for meaning. Meaning is read by late eyes — a fresh session with
  Read/Grep/Glob on Claude, or the Codex adapter's default read-only sandbox, and a fixed answer schema. Other than
  tree-only `anomaly` findings, a finding without a quote from each side is dropped on consume. `AGENT_CODEX_SANDBOX`
  can override the sandbox passed by the adapter. The reader uses the selected host's account.
- "Same kind of non-claim" is the first clause of the sentence, not a judgment — except a provider's own (`(provider) …`),
  kept whole: it leads with the contract sentence and says the gap after the dash, and cut there it read as a bare quote. A
  disposal written for the cut form (before 1.13.0) answers the whole sentence.

- `eyes_worker.py` starts its host session through `hostcall.py` — one host call for every worker of this family (hunsu's judge, mangsang's judge, dwitbuk's eyes,
  hacheong's members), vendored: the same file in each plugin, since a plugin imports no other plugin. The umbrella checkout's `tools/same-file.py` says when the copies drift.
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

## Versioning

Semver, and a version names one content: every change to the source — code, skill or command text, hooks, this README —
bumps the version in all three manifests (`plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`) and the
marketplace entries before it is used anywhere. Hosts copy a plugin at install and do not look again while the version
stands, so an unbumped edit is a copy nobody can tell from the old one. **patch**: behavior or wording, every interface
unchanged. **minor**: a new command, skill, field, hook or artifact key; what exists keeps working. **major**: an artifact
type, lock or record that other products read changes shape, or a supported Python or host version is dropped (an
`engines` floor rises, as `python` from 3.9 to 3.11 does). hunsu's `check` fails a linked plugin whose source differs
from the installed copy under one version; for a locally linked plugin, `hunsu install --refresh <plugin>` re-snapshots
after the bump.

### Release and adoption

Documentation and shared instruction edits also need a patch bump when interfaces stay unchanged.
Keep the version equal in `plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`,
and `.claude-plugin/marketplace.json` (both `metadata.version` and this product's `plugins[].version`).
`.agents/plugins/marketplace.json` currently has no version field; verify its product name and source path,
but do not invent a version field there.

Before publication, run the relevant checks in **Self-check** for behavior changes; for documentation-only
changes, verify links, command examples, imports and manifest consistency, plus `git diff --check`.
Publish the checked commit using this repository's existing release convention. Publication does not update
consumer installations: update the plugin through the host's supported workflow, reconcile the consuming
project's declared environment and lock if managed, and start a new host session to apply the installation.
Report publication, project adoption and live-host verification separately. Refreshing a locally linked
plugin is not an update procedure for every remote installation.

## Self-check

`python3 test_dwitbuk.py` — a temp project; every stop, rejection and kind of finding fires once, with recorded
provider responses where a model would have answered. No model calls.
