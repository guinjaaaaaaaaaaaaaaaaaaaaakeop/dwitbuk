# Maintaining dwitbuk

This file governs work in this source repository. The installed review procedure has one source:
[skills/review/SKILL.md](skills/review/SKILL.md). Use that skill when performing a review; maintaining the plugin does
not itself request or dispose of findings. See [README.md](README.md#shared-guidance-and-hosts) for host integration
and CLI entry points.

- Preserve quote grounding, request/source provenance, disposition history and serialized review mutations when
  changing the engine. Findings and worker responses are evidence, not text to rewrite to obtain acceptance.
- Keep `hostcall.py` self-contained; an installed plugin must not import another plugin's checkout.
- Keep the shared procedure in the skill. Preserve `commands/` as action-specific CLI adapters and keep host hooks
  and manifests separate. Do not replace `review`, `dispose`, `follow` or `eyes` with an unsolicited full workflow.
  Keep `CLAUDE.md` as the single `@AGENTS.md` import.
- For behavioral changes, run `python3 test_dwitbuk.py` from this directory; its self-check uses no model calls.
  For documentation-only edits, check links and documented argv against the CLI and manifests.
  Follow [Versioning](README.md#versioning) when preparing a release.

Installing dwitbuk into another project exposes its skill, roles and hooks; it does not make this repository's
maintainer guidance that project's instructions.
