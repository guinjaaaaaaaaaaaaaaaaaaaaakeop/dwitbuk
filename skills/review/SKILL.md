---
name: review
description: Use when the session-start line says objections are undisposed, when the person asks what happened or what is open, before a merge, or on a project whose lock has no `reviewer` role (there, run the review by hand). Relays a review's findings to the person for disposition and follows up on findings nobody disposed of.
---

The engine is `dwitbuk.py` at this plugin's root: `python3 <plugin root>/dwitbuk.py <command> --target <project>` (`python` on hosts that have no `python3`).

0. When the lock declares dwitbuk as chongdae's `reviewer`, the review already ran when each run ended — do not run another for the same run; go to step 2 with the latest `reviews/<id>.json` (`follow` lists what is open). The session-start line `dwitbuk: N undisposed objection(s) …` is that state.
1. Otherwise `review` (a first review covers everything since the commit that locked the environment; later ones, since the previous review's head; `--since REV` overrides). Read the findings by kind: `outside-run` (work no run claims), `unattributed`, `delegated` (what no human decided, with the stated reason), `non-claim` (what runs declined to verify), `left-open` (a task abandoned or rejected and never retried), `undisposed` (earlier findings still open).
2. Show the person the findings that need them — delegated, outside-run and left-open first. For each they answer, `dispose <review>/<n> --as accepted|dismissed --why "<their words>" --by <name>`. If no person reads a finding and you dispose it yourself, say so: `--as ... --delegated "<why it was handed off>"` — recorded as a delegation, like a gate. An accepted finding that needs work becomes a plan item or a run; dwitbuk does not do the work.
3. `follow` at the next session start: what is still open. Commit `reviews/<id>.json` — it is a record like a run.
4. Before a merge or when a run's report deserves a second reader: `eyes request --out DIR --since <commit>`, `python3 <plugin root>/eyes_worker.py --request DIR/eyes-request.json --response DIR/eyes-response.json`, `eyes consume --dir DIR --by <who>`. Contradictions land in the latest review for disposition like any finding.

dwitbuk finds; it never edits the project.
