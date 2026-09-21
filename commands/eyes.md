---
description: Late eyes — pack the diff, run records, plan and open findings for a bounded read-only session (request), or take its quoted contradictions into the latest review (consume)
argument-hint: request --out DIR [--since COMMIT] | consume --dir DIR --by WHO
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/dwitbuk.py" eyes $ARGUMENTS --target .`

Show the output above to the user as is. After `request`, run `python "${CLAUDE_PLUGIN_ROOT}/eyes_worker.py" --request DIR/eyes-request.json --response DIR/eyes-response.json` and then `consume`. Do not interpret or act on findings unless asked.
