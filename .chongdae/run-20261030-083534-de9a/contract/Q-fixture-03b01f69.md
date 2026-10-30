## Q-fixture

Owner direction on an observed integration defect of the test fixture (not of the product): run from a worker session
(`AGENT_WORKER=1` in the parent environment, as every hired worker of this run had), the unchanged
`test_session_start_hook_says_what_the_placed_reviews_still_need_and_nothing_else` fails with `JSONDecodeError` —
reported by rs-tests, cc-tests and others, and reproduced in `.maint-evidence/run4/fixture-before-{normal,worker}.txt`
(normal parent: pass; worker parent: fail). Its hook calls inherit the parent's `AGENT_WORKER`, so the calls that stand
for a normal session are silenced by the production guard.

1. The calls of that test that stand for a normal session start the hook with `AGENT_WORKER` removed from the child's
   environment; the calls that test worker suppression still pass `AGENT_WORKER=1` explicitly and still expect silence.
2. The production guard (`hooks/session_start.py`, `hooks/stop_eyes.py`: silent when `AGENT_WORKER` is set) is not
   changed, and no test changes the live process's environment globally.
3. The test passes run from a normal parent and from a worker parent.
