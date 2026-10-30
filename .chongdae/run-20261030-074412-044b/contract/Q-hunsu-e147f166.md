## Q-hunsu

`record_paths(target)` no longer returns the bare `hunsu`. In its place it returns hunsu's environment files by exact
name — `hunsu.json`, `hunsu.lock.json`, `hunsu.local.json`, `hunsu-judgments.json`, `hunsu-conflicts.md` — whether or
not the project has a lock. Everything else it returned stays: the lock's declared `record-paths` entries (or, without
a lock, `.mangsang/` and `.dwitbuk/`), and always `.chongdae/`, `reviews/`, `.dwitbuk/`, `.claude/`. The result is still
a sorted tuple of unique strings. Without a lock it is exactly
`(".chongdae/", ".claude/", ".dwitbuk/", ".mangsang/", "hunsu-conflicts.md", "hunsu-judgments.json", "hunsu.json",
"hunsu.local.json", "hunsu.lock.json", "reviews/")`.
