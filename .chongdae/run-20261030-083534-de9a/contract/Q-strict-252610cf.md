## Q-strict

Clarification from the owner and the coordination review: every current manifest's `records` (and so the lock's
`record-paths`) is unambiguous. An entry that ends in `/` names a directory. An entry without a trailing `/` names an
exact FILE path.

`is_record(path, entries)` decides by that declaration alone:

- The path is normalized: backslashes become `/`, one leading `./` is removed. A path that ends in `/` names a
  directory.
- A directory entry `D/` matches `D`, `D/`, and every path under `D/` — as before.
- A file entry `F` matches the path `F` and nothing else: not `F/`, and nothing under `F/`.
- No stat and no other look at the disk: if a declared file has been replaced by a directory, that directory and every
  file in it are source (`hunsu.json/child.py` with the bare entry `hunsu.json`; `custom-record.json/child.py` with a
  lock declaring the bare `custom-record.json`).
- Unchanged: a path that only shares an entry's leading characters never matches; wildcard characters in an entry are
  literal (`x[1].json` matches `x[1].json`, never `x1.json`); an empty entry or path matches nothing.

Superseded in the earlier contract's Q-match, for entries without a trailing `/` only: "and paths under it if it is a
directory (`entry + "/"` followed by anything)", and "a trailing `/` is ignored". The earlier tests that assert those
sentences (`alpha.json/inner.txt` and `alpha.json/` under the bare `alpha.json`; `mangsang/relations/R-1.json` under the
bare `mangsang`) are amended to this section; the earlier task records and answers stay as they were.
