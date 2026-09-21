---
description: Record a human's disposition of a finding
argument-hint: <review>/<n> --as accepted|dismissed (--why WHY [--by NAME] | --delegated WHY) [--quote QUOTE]
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/dwitbuk.py" dispose $ARGUMENTS --target .`

Show the output above to the user as is. Do not interpret or act on it unless asked.
