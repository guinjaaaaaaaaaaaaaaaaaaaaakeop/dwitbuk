## Q-raw-text

Added on the bounded exact-source review of the final parser at dc726d5 (`.maint-evidence/run4/review/parser-review-report.md`,
findings 1–3; 1 and 2 reproduced in `.maint-evidence/run4/du-cr-repro-dc726d5.txt`). Both are parser regressions this run
introduced, so under the owner's direction they close before 2.0. Q-exact-sections, Q-git-config and Q-conflict stand.

1. Modify/delete conflicts. Without a base, git prints an unresolved path whose conflict is modify/delete (DU, UD) as the
   one line `* Unmerged path PATH` (the name not quoted) instead of a `diff --cc` section. That line is that path's own
   section: kept once when the path is kept, left out when it is a declared record — never failing the request, never
   attached to another path's section, whatever the file order or batch boundaries. With a base, as now.
2. Raw text. The diff text `path_diff` parses is git's output as git wrote it: no newline translation, so a lone `\r`
   in a file's content stays inside that file's section and can neither start a section nor end one. A file with
   CR-only line endings whose content holds a line beginning `diff ` keeps its whole section, and the request succeeds.
3. Order. The composed text keeps the order one git call gives over the kept paths: the combined (`diff --cc`) sections
   first, then the others in git's order — also when batch boundaries fall between them.
