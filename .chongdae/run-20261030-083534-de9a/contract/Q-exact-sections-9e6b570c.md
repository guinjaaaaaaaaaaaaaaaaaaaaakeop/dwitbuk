## Q-exact-sections

Added on the bounded non-author review of ca9c776 and 5078ffb (`.maint-evidence/run3/review/fix-review-report.md`,
findings 1–4) and a session probe on 5078ffb (`.maint-evidence/run3/record-leak-repro-5078ffb.txt`): when a name changes
between a file and a directory, git lists both `N` and `N/child`, and the literal pathspec `:(literal)N` still reaches
`N/child`. That put a declared bare record `foo/rec.json` into the late-eyes diff (source `foo` replaced by a directory),
put a replaced file's source children into `excluded_diff` when the replacement is staged, and repeated `foo/a.py` when a
batch boundary fell between `foo` and `foo/a.py`.

1. The diff composed from candidate paths (the eyes request's `diff` and `verify_packet`'s `excluded_diff`) holds, for
   each kept candidate, that path's own section and nothing else: no section of a path the candidate judgement did not
   keep, and each kept path's section exactly once, wherever batch boundaries fall. With a source file `foo` replaced by
   a directory holding the declared bare record `foo/rec.json`, the eyes request's diff holds `foo`'s deletion and
   nothing of `foo/rec.json`; with HEAD's file `custom-record.json` replaced in the work tree by a directory whose
   `child.py` is staged, `excluded_diff` for the bare entry holds the file's deletion and nothing of `child.py`.
2. Without such a file/directory change the text is what it was: one unbatched call over the kept paths.
3. Tests also pin two rules that already hold: a single path longer than `PATHSPEC_BATCH_BYTES` is diffed (alone) rather
   than refused, dropped or raised on (item 6 of Q-review-fixes); and a gitlink inside a nested repository that the
   traversal walks into is marked like one at the top level (Q-gitlink).

Findings 7 and 9 of the first review stay documented limits.
