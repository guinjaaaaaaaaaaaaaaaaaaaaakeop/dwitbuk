## Q-keep

- mangsang's model records keep their special handling: `mangsang/` is a record for `verify_packet` and
  `documents_or_records` when the lock declares it (as today), and stays in what late eyes read — `source_state`, the
  eyes request's diff and `new_files`, and the stop hook — so a change under `mangsang/` after an eyes request still
  makes `eyes consume` refuse the answer as "source changed".
- Late-review freshness is otherwise unchanged: run records under `.chongdae/` still count when `records=True`, a
  commit of `reviews/` alone still does not stale an answer, and the packet directory is still excluded.
- String prefixes that are not about record paths stay as they are: the packet directory's containment check, the
  `git rev-parse --show-prefix` stripping, `run-` directory names, `eyes*-response.json` names, the `(provider) `
  and `settings.` text forms, the `.local.json` stop-hook rule, and `../` relative-path checks.
- `hostcall.py`, `eyes_worker.py`, the manifests and `README.md` are not part of this change; no version bump.
- `python3 test_dwitbuk.py` passes as a whole, on Python 3.11 or later.
