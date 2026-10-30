## Q-review-fixes

Added after the independent review of aad18a6 (`.maint-evidence/run2/review/final-review-report.md`); the sections above
stand. Its findings 1, 2, 4 and 6 are regressions or disagreements of this run's own change, finding 3 a test gap:

1. Renames. The eyes request's candidate listing and its diff do not pair renames (`--no-renames`): each side of a
   rename is its own candidate, judged by `is_record` on its own. A source file moved into a record path shows its
   deletion (`git mv src.py reviews/src.py`: `src.py` is in the diff, `reviews/src.py` is not); a rename between two
   source paths shows the old path's deletion and the new path as a new file; a record moved to a source path shows the
   new file and not the record's deletion. This holds with `--since`, from the latest review's base, and for a target
   inside a larger repository.
2. Argument limits. The kept literal pathspecs are given to git in batches: each git call's pathspec arguments together
   stay within `dwitbuk.PATHSPEC_BATCH_BYTES` (a module-level int, default well under the platform's argument limit; a
   test may lower it), and the diffs are concatenated in the order git listed the paths, the same text one call would
   give. The request may stop calling git once the diff has passed its 80000-character cut; `diff_truncated` stays true
   then. A change set whose names alone exceed the argument limit no longer fails.
3. `excluded_diff` in `verify_packet` holds exactly what each excluded entry names under Q-strict: a bare entry only that
   file — never files under a directory that took its name (those are source, and are in `diff` when touched) — and an
   entry ending in `/` that directory's files.
4. An untracked entry git lists as a directory (`name/`, an untracked nested repository, including one at a declared
   file's name) is not read as a file: it is not in `new_files`, and the eyes request completes.
5. Tests for Q-hostcall decide "the rest of the parent's environment": the child's environment equals the parent's with
   exactly the six identity/metadata keys removed and `AGENT_HOST`/`AGENT_WORKER` set (plus
   `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` for claude), for keys the earlier tests did not list (`HOME`, `LANG`, an
   `XDG_*`, an `SSH_*`, a `CLAUDE_CODE_*`, an arbitrary marker).

6. Settled after fx-build's first attempt chose to raise `ValueError` for a path longer than the limit (rejected): the
   limit bounds how many paths share one git call; a single literal pathspec longer than `PATHSPEC_BATCH_BYTES` is given
   to git alone in its own call. No path is refused, dropped or raised on.
7. `excluded_diff` is composed the way the eyes request's diff is: for each excluded entry, the candidate paths
   `git diff --no-renames --name-only` reports against `HEAD` for it, judged with `is_record` against that one entry, and
   only those diffed as literal pathspecs in batches — not by an include/exclude pathspec pair, since pathspec magic is
   not how this project decides file versus directory.

Not changed in this run, reported instead: a gitlink (submodule) at a declared file's path is still tested as a file by
`source_state` (finding 5); the stop hook's packet drops `mangsang/` through `verify_packet` (finding 7, older than this
run); the pre-existing `-z` / staged-change gaps of finding 9.
