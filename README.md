# dwitbuk

Placed eyes and a ledger of findings. The eyes read a contract, a diff and a record and speak only with a quote from each side; who places them — the runner (a verifier before a gate), the environment, or a person (late eyes) — sets the moment and the scope, and the author of the work never places them. A finding outlives the run that raised it, is never judged by its author, and recurs until disposed. It never fixes; it finds.

## Install

```
claude plugin marketplace add guinjaaaaaaaaaaaaaaaaaaaaakeop/dwitbuk
claude plugin install dwitbuk@dwitbuk
```

Codex: `codex plugin marketplace add guinjaaaaaaaaaaaaaaaaaaaaakeop/dwitbuk`, `codex plugin add dwitbuk@dwitbuk` (the skill is `$dwitbuk:review`).

## Commands

Each runs the engine and shows its output. `dwitbuk.py --help` for arguments.

| command | does |
|---|---|
| `/dwitbuk:review` | Collect `dwitbuk/findings@1` from the reporters the lock declares (chongdae `report`, mangsang `impact --findings` and `cq --findings`, hunsu `check --findings`, …), carry dispositions and recurrence, write `reviews/<id>.json`. No reporters: the review says so and is late eyes and dispositions only |
| `/dwitbuk:dispose` | Record a disposition of a finding — a person's (`--as accepted\|dismissed --why "…" --by NAME`) or one no person read (`--as … --delegated WHY`, recorded as a delegation like a gate); observations refuse it (they are not debt). The disposition copies the finding's own `text` and `where` at disposal time (`finding_text`), and `--quote` may add a verbatim quote from the record or the tree that grounds it — so a later machine judge can ask of the pair (finding, reason): does the reason actually address the finding, without re-resolving ids across reviews? Disposing a quote-grounded finding (`contradiction`, `anomaly`) without `--quote` warns, not refuses |
| `/dwitbuk:follow` | Findings of the latest review that nobody disposed of |
| (as chongdae's `verifier`) | The same eyes before a gate: `eyes_worker.py --request <chongdae request> --response ...` reads the task's contract, touched files and the builder's report and answers `dwitbuk/review@1` — accept, or reject with quoted findings — plus `worker` (host, model, turns, cost) with the whole stream kept as `<response>.transcript.jsonl`: an accept with no findings is auditable (what did the eyes read?), not a bare word. Declared as the `eyes` role in this plugin's plugin.json (`roles`), so a project writes `"verifier": "dwitbuk:eyes"` in hunsu.json and the lock carries the argv; or in the plan's `providers.verifier`. The builder never places it |
| (Stop hook) | The eyes placed by the environment: when the project sets `settings.dwitbuk.stop-eyes: true` in hunsu.json (read there, so it works while a working source is tried with `hunsu dev`; a lock that carries it still counts), a session that tries to end with a dirty tree gets its diff read (lens `fresh`, the plan as contract if there is one); findings refuse the stop once and reach the session, and land in the latest review. One model call per stop with changes — the team's switch, not the plugin's default. Inside a worker session (`AGENT_WORKER=1`: the eyes, a judge, a builder) the hook does nothing, since the host runs the project's hooks in those sessions too |
| `/dwitbuk:eyes` | `--contract PATH` reads the diff against any document (a spec, a PR text) when there is no plan; `--lens contract|record|fresh` writes one packet per lens (a generic reader inherits the author's blind spot); `fresh` yields `anomaly` findings with a tree quote only. Late eyes: `request` packs the diff, the run records, the plan and the open findings for a bounded read-only session (`eyes_worker.py`); `consume` takes its answer into the latest review — only findings quoting both the record and the tree survive |

## Files in your project

| path | committed | what |
|---|---|---|
| `reviews/<id>.json` | yes | a review: `since`, `head`, `reporters` it collected from, findings (kind, where, text, source, first-seen, disposition) |

The latest review is the open set. A finding seen again — the same kind, `where` and text, the changing counts struck — inherits its disposition; an objection that stops recurring without one is carried as `undisposed`; an observation that stops recurring simply stops. `eyes request` puts its packet and the worker's transcript under `--out` (default `dwitbuk-eyes/`; a reviewer keeps them under `reviews/`).

## Kinds of finding

Every finding carries a `layer`. An **objection** is a charge someone must answer — it is disposal debt: `follow` counts it, `dispose` closes it. An **observation** is a fact of the record — kept in the review (shown under its own heading with a count), but never debt: `dispose` refuses it ("an observation is a fact, not a charge") and `follow` neither lists nor counts it. `delegated` is an observation by kind; a reporter may mark any of its own findings `"layer": "observation"` and is trusted. Everything else — unknown kinds included — is an objection: fail closed.

From reporters, in their own words: chongdae's `outside-run` (grouped per directory here), `unattributed`, `delegated` (observation: `(verifier accepted)` / `(no verifier)`), `non-claim` (grouped by first clause so repeats show), `left-open` (a task open when its run closed, or rejected and never retried), `stage-finding` (what a role hired before or after a task found, with its quote), `verifier-reject` (a verdict that stopped an attempt, quoted from both sides), `delegation-stamp` (one reason stamped on 3+ judgments); mangsang's `stale`, `broken`, and from its `cq --findings` reporter `cq-failed`, `cq-unanswerable`, `cq-unquestioned`; hunsu's `drift`, `unreviewed`. dwitbuk's own: `undisposed`, `contradiction` and `anomaly` (late eyes), `no-reporters`, `reporter-failed`, and `review-debt` — when the previous review still holds undisposed objections, the new review emits one objection naming that review and the count; no gate, no block, the debt just re-accuses itself in every later review until the objections are disposed.

`eyes_worker.py --prompt-only --request <file> --response <file>` prints the exact prompt a call would send (the skill/eyes text, the request, the answer schema) and exits — for a session that dispatches its host's own subagent instead of this worker (a `native:` provider in chongdae). The subagent's answer is then written by the session; this worker never ran.

## Limits

- `--max-turns` bounds the Claude host only; `codex exec` has no turn limit to give, so a Codex eyes session ends when it ends.

- The engine never computes findings from another product's directory; it runs the reporters the lock declares and keeps what answers in the type. It reads run records only to pack them for the eyes.
- The engine reads records and git, never code for meaning. Meaning is read by late eyes — a fresh session with Read/Grep/Glob only, a fixed answer schema, and the rule that a finding without a quote from each side is dropped on consume. The reader is a model on the person's own host account.
- "Same kind of non-claim" is the first clause of the sentence, not a judgment.

## Versioning

Semver, and a version names one content: every change to the source — code, skill or command text, hooks, this README — bumps
the version in all three manifests (`plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`) and the
marketplace entries before it is used anywhere. Hosts copy a plugin at install and do not look again while the version stands,
so an unbumped edit is a copy nobody can tell from the old one. **patch**: behavior or wording, every interface unchanged.
**minor**: a new command, skill, field, hook or artifact key; what exists keeps working. **major**: an artifact type, lock or
record that other products read changes shape. hunsu's `check` fails a linked plugin whose source differs from the installed
copy under one version; `hunsu install --refresh <plugin>` recopies after the bump.

## Self-check

`python test_dwitbuk.py` — a temp project; every stop, rejection and kind of finding fires once, with recorded provider responses where a model would have answered. No model calls.
