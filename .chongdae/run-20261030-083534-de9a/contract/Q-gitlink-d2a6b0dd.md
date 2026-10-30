## Q-gitlink

Added on the coordination's bounded finding (the independent review's finding 5, reproduced on ca9c776 in
`.maint-evidence/run3/gitlink-repro-ca9c776.txt`); it supersedes the "not changed in this run" note above for finding 5
only. Findings 7 and 9 stay documented limits.

- `source_state`'s tracked traversal (`git ls-files` entries) marks an entry that git itself reports as a directory — a
  gitlink, index mode `160000` — with a trailing `/` before it is tested as a record, the same marker the status loop
  already gives untracked and ignored directories. The type comes from git's own report of the entry, not from
  `is_record` looking at the disk; `is_record` and every other site are unchanged.
- So a tracked nested repository (gitlink) at a bare exact-file declaration such as `custom-record.json` is source:
  editing a file inside it changes the fingerprint (an eyes answer bound before is refused with "source changed"), as
  it does for a gitlink at an undeclared path such as `lib`.
- A gitlink under a true directory declaration (an entry ending in `/`, such as `custom-dir/`) stays excluded; a
  regular tracked file at a bare declaration (`custom-record.json` as a file) stays excluded; mangsang's `mangsang/`
  still counts for freshness.
- No other behaviour changes; `python3 test_dwitbuk.py` passes as a whole on Python 3.11 or later.
