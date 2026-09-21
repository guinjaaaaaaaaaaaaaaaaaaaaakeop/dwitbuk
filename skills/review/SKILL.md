---
name: review
description: Use at the start of a session, after a run completes, before a merge, or when the person asks what happened. Runs dwitbuk's review, relays the findings to the person for disposition, and follows up on findings nobody disposed of.
---

The engine is `dwitbuk.py` at this plugin's root: `python3 <plugin root>/dwitbuk.py <command> --target <project>` (`python` on hosts that have no `python3`).

1. `review` (a first review covers everything since the commit that locked the environment; later ones, since the previous review's head; `--since REV` overrides). Read the findings by kind: `outside-run` (work no run claims), `unattributed`, `delegated` (what no human decided, with the stated reason), `non-claim` (what runs declined to verify), `left-open` (a task abandoned or rejected and never retried), `undisposed` (earlier findings still open).
2. Show the person the findings that need them — delegated, outside-run and left-open first. For each they answer, `dispose <review>/<n> --as accepted|dismissed --why "<their words>" --by <name>`. If no person reads a finding and you dispose it yourself, say so: `--as ... --delegated "<why it was handed off>"` — recorded as a delegation, like a gate. An accepted finding that needs work becomes a plan item or a run; dwitbuk does not do the work.
3. `follow` at the next session start: what is still open. Commit `reviews/<id>.json` — it is a record like a run.
4. Before a merge or when a run's report deserves a second reader: `eyes request --out DIR --since <commit>`, `python3 <plugin root>/eyes_worker.py --request DIR/eyes-request.json --response DIR/eyes-response.json`, `eyes consume --dir DIR --by <who>`. Contradictions land in the latest review for disposition like any finding.

dwitbuk finds; it never edits the project.
