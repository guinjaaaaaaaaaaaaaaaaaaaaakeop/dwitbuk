## Q-strict-keep

- mangsang's relations keep their late-review handling: `mangsang/` is a record for `verify_packet` and
  `documents_or_records` when the lock declares it, and stays in what late eyes read (`source_state`, the eyes
  request's diff and `new_files`, the stop hook's `touched`); a change under `mangsang/` after an eyes request still
  makes `eyes consume` refuse with "source changed".
- Directory entries behave as before. Real environment records stay excluded: `hunsu.json`, `hunsu.lock.json`,
  `hunsu.local.json`, `hunsu-judgments.json`, `hunsu-conflicts.md` as files; `.chongdae/`, `reviews/`, `.dwitbuk/`,
  `.claude/` and the lock's directory entries with what they hold.
- Same-prefix neighbours stay source at every site (`hunsu.py`, `alpha.jsonl` beside `alpha.json`, `x1.json` beside a
  declared `x[1].json`, `.alpha-extra/` beside `.alpha/`).
- `python3 test_dwitbuk.py` passes as a whole on Python 3.11 or later. No version bump; `README.md`, the manifests,
  `eyes_worker.py` and `hostcall.py` are not part of this build.
