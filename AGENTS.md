# Maintaining dwitbuk

This file governs work in this source repository. The installed plugin is [plugin/](plugin/); everything else here is
development material. The installed review procedure has one source:
[plugin/skills/review/SKILL.md](plugin/skills/review/SKILL.md). Use that skill when performing a review; maintaining
the plugin does not itself request or dispose of findings. See
[plugin/README.md](plugin/README.md#shared-guidance-and-hosts) for host integration and CLI entry points, and
[README.md](README.md#clone-and-develop) for the repository layout.

- Preserve quote grounding, request/source provenance, disposition history and serialized review mutations when
  changing the engine. Findings and worker responses are evidence, not text to rewrite to obtain acceptance.
- Keep runtime code only in `plugin/`: self-contained, no import from the checkout above it, no symlink. The root
  `dwitbuk.py` and `eyes_worker.py` stay entry points that run the payload's file and hold no engine code. Tests,
  hunsu files and run/review records never go into `plugin/`.
- Keep `plugin/hostcall.py` and `plugin/pluginroot.py` self-contained: the family vendors both byte-identical, and an
  installed plugin must not import another plugin's checkout.
- Keep the shared procedure in the skill. Preserve `plugin/commands/` as action-specific CLI adapters and keep host
  hooks and manifests separate. Do not replace `review`, `dispose`, `follow` or `eyes` with an unsolicited full workflow.
  Keep `CLAUDE.md` as the single `@AGENTS.md` import.
- User documentation is `plugin/README.md` and links nowhere above `plugin/`; developer documentation is the root
  `README.md`.
- For behavioral changes, run `python3 test_dwitbuk.py` from this directory; its self-check uses no model calls and
  includes the package checks. For documentation-only edits, check links and documented argv against the CLI and
  manifests. Follow [Versioning](README.md#versioning) when preparing a release.

## Preparing the environment

First establish whether the person wants to use dwitbuk or to change it.

- **Use it in another project:** install the published plugin from its marketplace
  ([plugin/README.md](plugin/README.md#install)); the host installs `plugin/` alone. Do not copy or apply this
  repository's `hunsu.json`, `hunsu.lock.json`, `hunsu-judgments.json` or records there: that project declares its own
  environment. Installing dwitbuk exposes its skill, roles and hooks; it does not make this file that project's
  instructions.
- **Change it:** prepare the development environment this repository declares.
  1. Read `hunsu.json` together with `hunsu.local.json` when it exists (this machine's links, `dev`, `hosts` and
     settings). The lock records an outcome; it is not the declaration.
  2. Use the hunsu release `hunsu.json` pins. When it is not installed here, install it from the marketplace
     `hunsu.json` names for it. Then run that hunsu's own steps: `python3 <hunsu root>/hunsu.py install --target .`
     makes this machine match `hunsu.json` and checks it; `hunsu.py check --target .` checks again. Where `check`
     stops at a decision, follow its `hunsu:compose` skill and ask the person. If the marketplace publishes another
     version than the pin, say so and reconcile it; never run a different version silently.
  3. Work on the host this session runs on, when it is usable, with the role providers `hunsu.json` explicitly
     requires. Where `hunsu.json` declares how work a member's sandbox cannot do is handled (`capabilities`, a role's
     `@cap` alternate), that declaration applies; it is not a silent swap. Do not start the other host only to cover
     it, and do not swap a role's host or model silently: any other missing required provider is a configuration
     mismatch to reconcile in the declared roles with the person.
  4. Keep personal paths, secrets and logins in machine-local files (`hunsu.local.json`, the hosts' local settings),
     never in committed ones. Add no setup script or host dependency mechanism of your own.

## Keeping the model

The mangsang model in `mangsang/` covers only the contracts and files [MODEL.md](MODEL.md) lists, not the whole source.
That bound is deliberate. Files outside it stay unregistered on purpose. In the payload and the root suites, each is
named in a `registered` invariant's `except` with its reason (MODEL.md), so `check` prints no unseen line. A
`registered` failure or an unseen line is a new file nobody classified: register and relate it when it carries a covered
contract, otherwise except it with a reason. Never leave one standing as expected. Widen the scope only by adding a
contract as MODEL.md says. Write the model's records only with the installed, locked mangsang engine, never with a
working checkout.

- Before changing a registered file, run `python3 <mangsang root>/mangsang.py lookup PATH --target .`. The relations
  it lists belong to the same change.
- The session that owns or orchestrates a change keeps the net coherent within it. It plans the relation update as its
  own task after the edit, and that task carries `python3 check_mangsang.py --engine <mangsang root>/mangsang.py` as
  its check. Covered work is complete when that check passes.
- A bounded worker (a builder, a test writer, a reviewer) reports the anchors and relations its change affects. It
  writes or signs model records only when its task contract says so. This guidance adds no write or signing authority
  to any worker; signatures follow mangsang's operate skill.
- `check_mangsang.py` checks that the model still holds its required concepts, questions, invariants and
  projections, then runs the engine's `check`, `cq` and `impact`. It fails when any of them fails or the model is
  absent.
- A stale relation is read (`impact --show`) and then reconfirmed or changed; never reconfirm one unread.
