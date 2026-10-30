## Q-conflict

Latest owner direction (via the coordination, after Q-git-config was written): every parser regression this run
introduced is closed before 2.0, including the narrow review's finding 4 — an unresolved merge conflict's `diff --cc`
section must not silently disappear. This section supersedes Q-git-config's documented limit for finding 4 only;
Q-git-config's other text stands. Reproduced on 97928f0 in `.maint-evidence/run3/conflict-repro-97928f0.txt`: with
`UU c.py` and a modified `d.py`, `eyes request` without a base exits 0 and its diff holds only `d.py`; git lists `c.py`
twice as a candidate.

1. The supported conflict format is handled: when the eyes request's diff is taken from the index to the work tree (no
   `--since` and no prior review), an unresolved path's `diff --cc` section is that path's own section. It is kept when
   the path is kept — exactly once, wherever batch boundaries fall and though git lists the path once per stage — and it
   is left out when the path is a declared record, like any other section.
2. No section of git's output is dropped silently: a section the filter cannot attribute to a candidate path makes the
   eyes request (and `verify_packet`'s `excluded_diff`) fail with a clear error before any packet is written — not an
   empty or partial diff.
3. With a base (`--since`, or a prior review's base) the conflicted path's text is what git gives against that base,
   as now. Q-exact-sections and Q-git-config hold as written.

Q-conflict item 2, clarified before any build (the tests cc-tests wrote first appended the foreign block after the last
section, where it joins that section's text): "a section the filter cannot attribute" means text git prints outside any
section header the filter reads — before the first `diff --git` or `diff --cc` header of a call's output, or under a
header starting `diff ` of another kind or one whose path cannot be read. That is what `diff.submodule=log` printed for
a gitlink first in a batch. A section with a readable header whose path is not a kept candidate (a file reached under a
name that changed between file and directory) is still left out, as Q-exact-sections says. Text inside a readable
section is not validated line by line.
