## Q-match

One rule decides whether a path is a record path, in a new helper in `dwitbuk.py`:
`is_record(path, entries) -> bool`, where `entries` is an iterable of record-path entries such as `record_paths`
returns.

- The path is normalized first: backslashes become `/`, one leading `./` is removed, and a trailing `/` is ignored.
- An entry that ends in `/` names a directory: it matches the directory itself (`mangsang` or `mangsang/` for the
  entry `mangsang/`) and every path under it (`mangsang/relations/R-1.json`).
- An entry that does not end in `/` names that exact path: it matches the path equal to it, and paths under it if it
  is a directory (`entry + "/"` followed by anything).
- Nothing else matches. A path that only shares the entry's leading characters is not a record:
  `hunsu.py`, `hunsu_helper.py`, `hunsu-notes.md` for any `hunsu…` entry; `alpha.jsonl` or `alpha.json.py` for the
  entry `alpha.json`; `mangsang-extra/x.py` for `mangsang/`; `.alpha-extra/y.py` for `.alpha/`; `reviews2/a.json`
  for `reviews/`; `.chongdae-notes.md` for `.chongdae/`.
- An empty entry, or an empty path, matches nothing.
