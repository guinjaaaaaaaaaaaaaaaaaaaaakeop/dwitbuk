## Q-git-config

Added on the narrow non-author review of d1e8c32 (`.maint-evidence/run3/review-xs/xs-review-report.md`, findings 1–3
and 5; finding 1 reproduced in `.maint-evidence/run3/color-repro-d1e8c32.txt`): the section filter reads git's diff text,
so that text must not depend on the user's git configuration.

1. The git diff calls whose output `path_diff` parses ask for plain, repository-relative, per-file text whatever the
   user's configuration says: no colour, no relative headers, a gitlink shown in its short form, no external diff driver,
   and the `a/` `b/` prefixes already pinned. With a global git configuration setting `color.ui=always`,
   `diff.relative=true`, `diff.submodule=log`, `diff.noprefix=true` and `diff.mnemonicPrefix=true`, the eyes request's
   diff (top-level target and a target inside a larger repository) and `verify_packet`'s `excluded_diff` are the same
   text as with an empty global configuration.
2. The tests' unbatched comparison asks git for the same pinned form, so the suite does not depend on a maintainer's
   global git configuration for these comparisons.

Documented limits, not changed in this run: an unresolved merge conflict's `diff --cc` section is not kept when the eyes
request has no base (finding 4); `diff.orderFile` ordering across batch boundaries is not checked; the first review's
findings 7 and 9; `verify_packet`'s per-touched-file diff still gives git one literal pathspec per touched path, which
reaches files under a touched name that changed between file and directory.
