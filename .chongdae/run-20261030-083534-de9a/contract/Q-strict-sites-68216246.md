## Q-strict-sites

Every place that decides "is this path a record" follows Q-strict, and they agree with each other. In particular, with
the bare `hunsu.json` (always a record path) and a lock declaring the bare `custom-record.json`, after each of those
files was replaced by a directory holding a tracked `child.py`:

1. `documents_or_records`: `hunsu.json/child.py` and `custom-record.json/child.py` are not records.
2. `verify_packet`: they stay in `touched`, and their change (from the task's start, or as a new file) is in `diff`.
   Each touched path and each `excluded` path is given to git as a literal pathspec (`:(literal)PATH`), so a name with
   wildcard characters selects only itself.
3. `source_state`: changing `hunsu.json/child.py` or `custom-record.json/child.py` changes the fingerprint (an eyes
   answer bound before the change is refused at consume with "source changed"). A directory the function examines — in
   its walk of a project without git, and an untracked or ignored directory entry from `git status` — is tested as a
   directory (with its trailing `/`), so a file entry never prunes it.
4. `eyes request` (late eyes): `left_out` keeps each entry as declared — directories with their trailing `/` — and the
   packet directory, when it is inside the target, is added as a directory (`<relative path>/`). `diff_leaves_out` lists
   them in that form. The diff is composed from the candidate file paths git reports as changed against the same base
   (`git diff --name-only`), each judged with `is_record` against `left_out`; only the kept paths are diffed, as literal
   pathspecs. When no candidate remains the diff is empty — never an unrestricted `git diff`. Pathspec magic alone is
   not a correct exclusion: `:(exclude,literal)hunsu.json` and `:(exclude,glob)hunsu.json` both hide every file under a
   directory named `hunsu.json`. A changed tracked `hunsu.json/child.py` or `custom-record.json/child.py` is in the
   packet's `diff`, shown by a test on real git output, and an untracked file inside such a directory is in
   `new_files`.
5. `hooks/stop_eyes.py`: a dirty `hunsu.json/child.py` or `custom-record.json/child.py` reaches the session's `touched`
   and its change reaches the packet's `diff`; `diff_leaves_out` lists the entries as declared (directories with `/`).
