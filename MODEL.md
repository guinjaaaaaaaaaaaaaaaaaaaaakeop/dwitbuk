# dwitbuk's model

This repository keeps a [mangsang](https://github.com/guinjaaaaaaaaaaaaaaaaaaaaakeop/mangsang) model of eight core
contracts of the engine, and nothing more. The records are in `mangsang/`. This page says what they claim and what they
do not. [check_mangsang.py](check_mangsang.py) fails when the model is missing or loses any of it. None of this is part
of the installed plugin in `plugin/`.

## Covered contracts

Each contract is a concept whose one-sentence meaning is in `mangsang/concepts/`. The summaries below are not the
meanings; `mangsang concept show NAME` prints a meaning with everything that stands on it.

| concept | in short | code | manual (`plugin/README.md`) | tests (`test_dwitbuk.py`) |
|---|---|---|---|---|
| `quote-grounded-finding` | `eyes consume` keeps, and the verify path counts, an eyes finding only when its record and tree quote fields are filled (an anomaly: the tree quote alone); whether a quote is true is not checked here | `plugin/dwitbuk.py:grounded`, `plugin/eyes_worker.py:main` | `/dwitbuk:eyes` | `test_one_grounding_rule_for_eyes_findings_an_anomaly_stands_on_the_tree`, `test_eyes_packet_carries_diff_records_plan_and_open_findings_and_consume_keeps_only_quoted_contradictions` |
| `bound-late-answer` | a late-eyes answer is taken only while bound to its request, target and unchanged source | `plugin/dwitbuk.py:bind_eyes`, `plugin/dwitbuk.py:check_eyes`, `plugin/eyes_worker.py:main`, `plugin/hooks/stop_eyes.py:main` | `/dwitbuk:eyes`, Stop hook | `test_late_eyes_refuses_wrong_target_unbound_replaced_and_stale_answers`, `test_late_eyes_sees_nested_source_and_worker_refuses_changes_during_call`, `test_stop_hook_validates_before_displaying_even_without_a_review` |
| `one-answer-per-charge` | a charge stays owed until one disposition answers it, carried once until then | `plugin/dwitbuk.py:identity`, `charge`, `answered`, `carry`, `cmd_dispose` | Files in your project, `/dwitbuk:dispose` | `test_one_charge_is_disposed_once_across_consecutive_reviews`, `test_a_carried_charge_stands_once_and_one_disposal_answers_it_once` |
| `serialized-review-mutation` | one review mutation at a time per checkout; a competing one exits 4 before reading or writing any review record; records replaced atomically | `plugin/dwitbuk.py:ReviewLock`, `serialized`, `save` | `/dwitbuk:eyes` | `test_concurrent_consumers_refuse_busy_then_retain_both_findings_on_retry` |
| `fail-closed-layer` | every finding is an objection unless one of four rules names it an observation: an explicit layer, a fact kind, a declared setting's note, a by-nature no-check line | `plugin/dwitbuk.py:layer`, `collect`, `cmd_dispose` | Kinds of finding | `test_layers_are_fail_closed_and_a_reporter_may_mark_its_own_kind_informational`, `test_a_layer_a_reporter_gave_that_is_no_layer_is_a_charge_and_never_left_to_the_by_nature_rule`, `test_a_run_seen_again_is_answered_and_what_no_check_can_decide_is_said_not_charged`, `test_no_check_by_nature_stays_but_never_lifts_a_constituents_explicit_objection` |
| `verifier-sees-touched` | the verify packet names every touched path but `.chongdae/` and `.claude/`, each with its diff under the size cut, lists in `not_in_diff` what that diff does not hold whole, and an accept names those the eyes did not open | `plugin/dwitbuk.py:verify_packet`, `plugin/eyes_worker.py:unread_touched`, `main` | as chongdae's `verifier` | `test_D1_verify_packet_keeps_touched_record_paths_with_their_diff_and_drops_only_chongdae_and_claude`, `test_D1_verify_packet_names_in_not_in_diff_what_its_diff_does_not_hold_whole`, `test_D2_unread_touched_names_the_not_in_diff_files_the_eyes_did_not_open`, `test_D2_an_accept_that_left_a_big_touched_file_unread_says_so_and_a_reject_is_untouched` |
| `closed-review-kept` | consume never rewrites a review a completed run recorded at close; it appends to the bound review (or its eyes review) only while that is the latest and open, else writes a new review naming it that carries the open set | `plugin/dwitbuk.py:closed_reviews`, `cmd_eyes`, `bind_eyes` | `/dwitbuk:eyes` | `test_D4_consume_on_a_packet_bound_to_a_closed_review_writes_a_new_eyes_review_and_leaves_the_closed_one_as_it_was`, `test_E1_a_packet_bound_to_no_review_gets_a_new_eyes_review_and_leaves_the_ordinary_review_as_it_was` |
| `selected-host-plugin-root` | one vendored resolver gives `{plugin:NAME}` the copy for the host the process runs on: a link, else the declared marketplace installed on that host; never another host's or marketplace's copy; a version note becomes a `plugin-version` objection; otherwise no root and a reason | `plugin/pluginroot.py:resolve`, `_resolve`, `load`, `catalog_source`, `plugin/dwitbuk.py:plugin_root`, `resolve_argv`, `collect` | Plugin roots | `test_D5_environ_defaults_to_os_environ`, `test_D5_codex_only_install_resolves_on_codex_and_not_on_claude_code`, `test_D5_the_same_name_in_two_marketplaces`, `test_D5_dwitbuk_plugin_root_is_resolves_root_and_stops_with_its_reason`, `test_E2_a_malformed_or_non_object_installed_plugins_json_gives_no_root_and_the_reason_names_it` |

Every concept is realized in all three media (manual, code, tests), and every relation quotes its anchor. The core
symbols `grounded`, `check_eyes`, `cmd_dispose`, `ReviewLock`, `layer`, `verify_packet`, `closed_reviews` and
`plugin/pluginroot.py:resolve` are each documented by a manual section.

A test `verifies` a symbol only where it calls that symbol, or its bare command dispatch, and asserts on what it returns
or writes. A test that reaches a symbol only through another one is a `realizes` of the concept, not a `verifies`.
Under that rule:
- `grounded`, `cmd_dispose` (through `dispose`) and `plugin/hooks/stop_eyes.py:main` are verified by the tests named in
  the table.
- `cmd_eyes` (through `eyes consume`) is verified by `test_late_eyes_refuses_wrong_target_unbound_replaced_and_stale_answers`
  and `test_concurrent_consumers_refuse_busy_then_retain_both_findings_on_retry`. Its fingerprint reads `check_eyes`, so
  an edit to `check_eyes` makes both stale.
- `ReviewLock` is verified by `test_package_a_copy_of_the_payload_alone_runs_review_dispose_eyes_and_hooks_outside_the_checkout`.
  It holds `dwitbuk.ReviewLock` in a second process and asserts that a competing `dispose` exits 4 and writes nothing.
- `cmd_review` (through `review`) is verified by
  `test_layers_are_fail_closed_and_a_reporter_may_mark_its_own_kind_informational`. It asserts the layers the review
  writes: an unknown kind is an objection, `delegated` is an observation, and a reporter's explicit layer is kept. Its
  fingerprint reads `layer`, so an edit to `layer` makes it stale.
- `verify_packet` is verified by both `test_D1_*` tests, which call it and assert on its `touched`, `diff` and `not_in_diff`;
  `plugin/eyes_worker.py:unread_touched` by `test_D2_unread_touched_names_the_not_in_diff_files_the_eyes_did_not_open`, and
  `plugin/eyes_worker.py:main` by `test_D2_an_accept_that_left_a_big_touched_file_unread_says_so_and_a_reject_is_untouched`.
- `cmd_eyes` is also verified by `test_D4_consume_on_a_packet_bound_to_a_closed_review_writes_a_new_eyes_review_and_leaves_the_closed_one_as_it_was`
  (through `eyes consume`); `closed_reviews`, which it calls, has no direct test and is held by realizes.
- `plugin/pluginroot.py:resolve` is verified by `test_D5_environ_defaults_to_os_environ`, which calls it directly; the other
  D5 and E2 tests call it through the `Hosts` helper, so they are its `realizes`. `plugin_root` is verified by
  `test_D5_dwitbuk_plugin_root_is_resolves_root_and_stops_with_its_reason`.
- `check_eyes`, `layer` and `carry` have no test that proves them directly, so their test coverage is held by `realizes`
  (and, for `check_eyes` and `layer`, by the `cmd_eyes` and `cmd_review` verifies above). The tests that call
  `dwitbuk.layer` call it only on findings `review` wrote with a layer already, so the call returns the stored layer and
  could not fail on `layer`'s own rules. An edit to `carry` makes only its `realizes` stale: the concept owes a re-read,
  and no test is asked.

Each concept has one domain question (`mangsang/cq/`) answered by its meaning. The invariants are:
- `registered-payload` and `registered-source`: every tracked file under `plugin/` and every root path starting `test`
  is watched unless an `except` entry names it, and `AGENTS.md` and `MODEL.md` are watched. See Registered and excepted.
- `projection`: each concept is realized in all three media; its code media are `plugin/dwitbuk.py`, `plugin/eyes_worker.py`,
  `plugin/hooks/stop_eyes.py` and `plugin/pluginroot.py`.
- `resolved`: no relation stands on a dead anchor.
- coverage: `verified-*` asks for a direct `verifies` on `grounded`, `cmd_eyes`, `cmd_dispose`, `ReviewLock`,
  `cmd_review`, `verify_packet`, `cmd_eyes` again (`verified-closed-reviews`) and `plugin/pluginroot.py:resolve`. `verified-check-eyes` was revised from `check_eyes` to `cmd_eyes`, and `verified-layer` from `layer` to
  `cmd_review`; each keeps its earlier declaration in its history. `documented-*` asks for a manual section on each
  core symbol.
- `required-model` (kind `required`, mangsang 2.2.0 or later): the eight concepts, their eight questions, the twenty
  invariants above and each concept's core projection (`plugin/dwitbuk.py:grounded realizes concept:quote-grounded-finding`, …,
  `plugin/pluginroot.py:resolve realizes concept:selected-host-plugin-root`) must stand: none missing, retired, drifted,
  owing a re-read or broken. It is the engine's form of the required lists in `check_mangsang.py`.

The retired records keep their reasons as written. The reason on `mangsang/retired/R-dfc55f40.json` names
`test_a_layer_a_reporter_gave_that_is_no_layer_is_a_charge_and_never_left_to_the_by_nature_rule` as `layer`'s direct
`verifies`. That relation, R-899ccedc, was retired after it as an overclaim, and the later retirement supersedes the
sentence: no test proves `layer` directly.

## Registered and excepted

The two `registered` invariants decide which tracked files the net must see. The engine's `check` fails when a tracked
file under an invariant's paths is neither registered nor matched by one of its `except` entries. A new file there must
be classified before the model holds again. Register and relate it when it carries a covered contract. Otherwise name it
in an `except`, with its reason in the table below and in `check_mangsang.py`. Never register a file only to quiet the
check. `check_mangsang.py` fails when an invariant stops asking about a path below, or excepts anything the table does
not list.

| invariant | path | what it covers |
|---|---|---|
| `registered-payload` | `plugin/` | the installed payload and every subdirectory |
| `registered-source` | `test` | every tracked root path starting `test`: the suites `test_*.py`, and a `tests/` directory if one is added |
| `registered-source` | `AGENTS.md`, `MODEL.md` | the source maintenance documents |

| except | invariant | reason |
|---|---|---|
| `plugin/hostcall.py` | payload | the vendored host-call adapter shared with the other plugins; it starts a host and returns its answer and judges nothing, so it is in none of the five contracts |
| `plugin/hooks/session_start.py` | payload | prints the count of undisposed objections at session start; it never writes and decides none of the five contracts |
| `plugin/hooks/hooks.json`, `plugin/hooks/codex.json` | payload | host hook manifests: they wire the two hooks to their events and hold no logic |
| `plugin/plugin.json`, `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json` | payload | plugin manifests: packaging and the version |
| `plugin/LICENSE` | payload | the license |
| `plugin/commands/dispose.md`, `plugin/commands/eyes.md`, `plugin/commands/follow.md`, `plugin/commands/review.md` | payload | the host's per-action CLI adapters: markdown that runs the CLI and holds no engine code |
| `plugin/skills/review/SKILL.md` | payload | the shared review procedure: prose for the session, not engine code |
| `test_check_mangsang.py` | source | the guard's own regression suite: it proves `check_mangsang.py` on disposable copies and tests none of the five contracts |

Every entry names one file; no entry is a glob. The engine matches an entry with `fnmatch`, where `*` also matches
`/`, so a glob could leave out files its reason never covered. A new file under `plugin/commands/` or `plugin/skills/`
fails `check` like any other: a new adapter, a new procedure or code.

## Engine-enforced facts and policy

The engine enforces the five contracts above, and the related tests prove them. What follows is policy: recorded, never
verified by dwitbuk.

- Whether a disposition's reason answers its finding. The disposal keeps `finding_text` beside `why` so a reader can
  weigh them; nothing judges it.
- Who may dispose. `--by` names a person on the caller's word, while `--delegated` says no person read the finding.
- When a review runs. The lock's `reviewer` role and the review skill say so; dwitbuk does not.
- Whether an accepted finding needs work. That becomes a plan item or a run elsewhere.

The model's meanings, questions, invariants and relations are agent judgments. They were signed `--delegated` under the
owner's model-application task — the three concepts of 2.2.0, their questions, the coverage and required invariants and
the revised `bound-late-answer` under the owner's Stage C request of 2026-11-06 — read against the files named above, and
no person approved their wording. Re-read relations are signed as the agent's own re-read.

## Not claimed

- **The rest of `plugin/dwitbuk.py`:**
  - reporter collection (only the layer `collect` gives a finding, and the `plugin-version` objection it records, are in
    scope; how `{plugin:NAME}` resolves is `selected-host-plugin-root`);
  - non-claim grouping beyond the layer it gives a grouped non-claim, and `unchanged` counting;
  - the stop hook's own display filter, used when no review exists: it checks neither a finding's kind nor its `where`,
    so `quote-grounded-finding` claims only consume and the verify path;
  - the verify packet beyond which touched paths reach it and what its diff leaves out (`verifier-sees-touched`): its
    instructions, `excluded`, and its weighing of quote spans (`weigh`, `unfounded`);
  - whether an eyes quote occurs verbatim in the record or the tree: `grounded` checks only that the quote fields are
    filled, and consume checks nothing more of a quote;
  - diff bounding and batching, record paths, the internals of `source_state`, and `follow`'s output.
- **The rest of the payload:** `plugin/hostcall.py`, `plugin/hooks/session_start.py`, `plugin/commands/`,
  `plugin/skills/`, the manifests and `plugin/LICENSE`. `registered-payload` excepts each, with the reasons under
  Registered and excepted.
- **The rest of `test_dwitbuk.py`.** Only the tests named above are related. The model claims nothing about the suite
  as a whole; `python3 test_dwitbuk.py` does that.
- **Root files other than the `test` paths, `AGENTS.md` and `MODEL.md`:** the entry points `dwitbuk.py` and
  `eyes_worker.py` (AGENTS.md keeps engine code out of them), `check_mangsang.py`, `README.md`, the hunsu files, and the
  catalogs in hidden directories. No `registered` invariant asks about them, so a new root file that is not a `test`
  path does not fail `check`. The engine's unseen advice leaves the root's own files out too.
- **Hosts and packaging:** the Codex adapter, packaging and versions; which installed copy each host actually loads is
  the host's, read from its registry files as `selected-host-plugin-root` says, never observed in a live host session.

Some anchors' fingerprints read many helpers in their file: `collect`, `plugin/eyes_worker.py:main` and
`plugin/hooks/stop_eyes.py:main`. An edit to reporter resolution or to the worker's host call makes those relations
stale. That is expected: read them, then reconfirm or update.

## Maintaining it

- Before editing a registered file, run `mangsang lookup PATH`. The relations it lists are part of the same change.
- The session that owns or orchestrates the change keeps the net coherent within it. A bounded worker reports the
  anchors and relations it affects, and writes or signs model records only when its task contract says so. See
  [AGENTS.md](AGENTS.md), Keeping the model.
- After a change, run `python3 check_mangsang.py --engine <the installed mangsang.py>`.
  - A stale relation: read `impact --show`, then reconfirm it, or change the section or test it stands on.
  - A meaning that no longer holds: `concept revise` it, or mark it with `concept drift` until it is revised.
  - A `registered` failure or an unseen line: a new file nobody classified. Register and relate it, or except it with a
    reason (`cq revise` the invariant, then update the tables above and `SCOPE` in `check_mangsang.py`). It is never
    an expected line to leave standing.
  - Never reconfirm unread.
- Adding a contract to the scope takes all of these: the concept first, then its projections and a question, then this
  page, the `required-model` invariant's lists, and the declarations in `check_mangsang.py`: `CONCEPTS`, `QUESTIONS`,
  `CORE`, `VERIFIED`, `SLUGS` (which builds `COVERAGE`), `INVARIANTS` and `MEDIA`. The guard requires `required-model`
  itself; its lists name the eight concepts, eight questions, twenty other invariants and eight core projections.
- `python3 test_check_mangsang.py --engine <the installed mangsang.py>` proves the checker on disposable copies. It
  never changes the live tree.

## The check

`check_mangsang.py --engine PATH [--target DIR] [--json]` reads the records and never writes them. Exit codes:
- **1:** the engine's `check --require-model`, `cq` or `impact` fails, or a project declaration differs from the records.
  The engine's `check --require-model` rejects an absent or empty model; `required-model` decides whether required
  concepts, questions, invariants and core projections remain. The declared projection, coverage and registered
  invariants decide missing projections, `verifies`/`documents`, and unregistered tracked files.
  The guard requires an active `required-model` of kind `required` and checks that its lists still name every declared
  concept, question, other invariant and core projection. It keeps each domain question's concept binding, each
  invariant's kind, each `COVERAGE` predicate and anchor, exact `MEDIA` for `projected`, and the registered `SCOPE`
  paths and allowed excepts. It also requires this page to name every declared concept/path/except, evidence on every
  relation, and the engine's reads to leave the model records unchanged.
- **2:** the engine is missing or is not a mangsang engine.
- **0:** otherwise.
