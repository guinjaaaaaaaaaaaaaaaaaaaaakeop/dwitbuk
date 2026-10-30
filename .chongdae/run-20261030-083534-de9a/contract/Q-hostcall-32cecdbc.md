## Q-hostcall

- `hostcall.py` becomes byte-identical to hacheong's reviewed `hostcall.py` at commit `7aa70c6` (SHA-256
  `fa06077c00e1aa8514be54689567bad7abcb5c5f21794e1b5f551ebb1e07873b`). Nothing else changes in it, and it imports no
  other plugin.
- Through dwitbuk's own adapter entry points — `eyes_worker.claude(packet, schema, args)` and
  `eyes_worker.codex(packet, schema, args)` — with `subprocess.run` replaced by a recorder (no host process starts), the
  environment given to the child:
  - names the worker's own host whatever the parent's `AGENT_HOST` says: `AGENT_HOST=claude-code` for the claude
    adapter, `AGENT_HOST=codex` for the codex adapter; and `AGENT_WORKER=1`;
  - carries none of the parent's session identity or project metadata: no `CODEX_THREAD_ID`, `CLAUDE_CODE_SESSION_ID`,
    `CHONGDAE_SESSION`, `AI_AGENT`, `CLAUDE_PROJECT_DIR`, `CODEX_VERSION`;
  - keeps the rest of the parent's environment — configuration, authentication and markers such as `CLAUDE_CONFIG_DIR`,
    `CODEX_HOME`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `CLAUDECODE`, `PATH` — and the claude call still sets
    `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`;
  - the codex call passes `AGENT_CODEX_SANDBOX`, when the parent sets it, as its `-s` sandbox, and `read-only`
    otherwise.
- The parent's `os.environ` is the same after each call as before it.
- `python3 test_dwitbuk.py` passes as a whole on Python 3.11 or later.
