## Q-bounded

Latest root direction, after raw-build finished (its record keeps all three attempts: the first's dispute that the raw
fix needs the shared `git()` helper, the second's decision to read every batch before ordering and cutting, the third
keeping that code). It supersedes two settlements written above — they stay as history, not as the contract:

- the paragraph "Q-raw-text, settled on raw-build's dispute …", which authorized changing the generic `git()` helper.
  That change exceeded the intended patch-only newline preservation; the first attempt's dispute had it right, the
  nitpick kept its wrapper unchanged, and the provider then changed the global helper as that paragraph allowed;
- Q-raw-text item 3 and the paragraph "Q-raw-text item 3, settled after raw-build's second attempt …", which made the
  request read every batch.

1. Scope of the raw read. The generic `git(target, *args)` helper has its previous semantics again (text with universal
   newlines, as at 39e2a7b). The untranslated patch text that `path_diff` parses comes from a narrowly named patch
   helper in dwitbuk.py, `git_patch(target, *args)`, used only by `path_diff`'s content diff calls: git's stdout decoded
   as UTF-8 (errors replaced) without newline translation, `None` on a non-zero exit. Tests that observe or inject those
   content calls do so at that seam or at subprocess invocation.
2. Bounded work. Once the composed text has passed its limit (80000 characters for the eyes diff, 40000 for
   `excluded_diff`), no later `git diff` batch is invoked; the text is cut at the limit and the truncation is declared
   (`diff_truncated` for the eyes request). Patches of batches not yet needed are never kept.
3. Order. Within a batch, git's own order is kept. Across batch boundaries the combined (`diff --cc`) sections of UU
   conflicts may follow the order of the batches instead of one call's global order (combined sections first). That
   is the documented limit: it loses nothing, and when the text is not cut every kept section is present exactly once
   with all its source content.
4. Unchanged and still required: a DU/UD conflict's `* Unmerged path PATH` line is that path's own section in every
   position; a lone `\r` neither starts nor ends a section; unexpected output fails explicitly before any packet is
   written; exact attribution, no declared record's section, no repeated section; the canonical flags of Q-git-config.
