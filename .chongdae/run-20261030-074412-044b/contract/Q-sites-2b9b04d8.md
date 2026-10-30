## Q-sites

Every place in `dwitbuk.py` and `hooks/stop_eyes.py` that decides "is this path a record" uses `is_record` (Q-match)
with the same entries it uses today; no record decision is left to `startswith` or to a glob.

1. `documents_or_records(paths, target)`: a path is a record only by Q-match against `record_paths(target)`; documents
   are still decided by their suffix as today. With a lock declaring `mangsang/`: `hunsu.lock.json`, `mangsang`,
   `mangsang/relations/R-1.json` are records; `hunsu.py`, `hunsu_helper.py`, `mangsang-extra/x.py` are not, so a list
   holding any of those (and no document suffix for it) is not all documents or records. `hunsu-notes.md` is still a
   document by its suffix.
2. `verify_packet(request)`: `touched` drops exactly the paths that are records by Q-match. `hunsu.py`,
   `hunsu_helper.py`, `hunsu-notes.md`, a same-prefix neighbour of a lock-declared file (`alpha.jsonl` beside declared
   `alpha.json`) and a sibling of a declared directory (`.alpha-extra/y.py` beside `.alpha/`) stay in `touched`, and
   their change is in the packet's `diff` (as a diff from the task's start, or as a new file's text, as today); the
   declared file `alpha.json`, a true descendant `.alpha/x.json`, `.chongdae/...` and `hunsu.json` are dropped. The
   request's `excluded.record-paths` list still drops chongdae's own runs (`.chongdae/` and what is under it) and keeps
   everything else, decided by the same rule.
3. `source_state(...)` (the late-eyes source fingerprint): a file is skipped as a record only by Q-match against the
   record paths other than `mangsang/`. Changing `hunsu.py`, `hunsu_helper.py` or `hunsu-notes.md` changes the
   fingerprint (an eyes answer bound before the change is refused at consume as "source changed"); changing
   `hunsu.json`, `hunsu.lock.json` or a file under `reviews/` alone does not. A non-git project's walk prunes a
   directory only when it is a record by Q-match.
4. `eyes request` (late eyes): the diff leaves out exactly the record paths other than `mangsang/`, plus the packet
   directory, using literal exclude pathspecs (`:(exclude,literal)ENTRY`) so an entry is never read as a glob or a
   prefix. `diff_leaves_out` keeps its form (each entry without its trailing `/`; the packet directory when it is
   inside the target) and holds hunsu's exact files instead of `hunsu*`. Untracked files enter `new_files` unless they
   are records by Q-match against those same entries or lie in the packet directory: an untracked `hunsu.py`,
   `hunsu_helper.py` or `hunsu-notes.md` is in `new_files`, and a committed-then-changed `hunsu.py` is in `diff`;
   an untracked `hunsu.json` is in neither.
5. `hooks/stop_eyes.py`: a dirty path is left out of the session's `touched` only when it is a record by Q-match
   against the record paths other than `mangsang/` (the `.local.json` rule stays as it is). A dirty `hunsu.py`,
   `hunsu_helper.py` or `hunsu-notes.md` reaches the eyes' `touched`; `diff_leaves_out` lists the exact entries.
