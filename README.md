# dwitbuk — source repository

Placed eyes and a ledger of findings. **What the plugin does — its commands, roles, hooks, the files it writes in a
project, the kinds of finding and its limits — is in [plugin/README.md](plugin/README.md)**, the README an installation
carries. This page is for working on the source.

## Install

Using dwitbuk needs no clone. Requires Python 3.11 or later:

```
claude plugin marketplace add guinjaaaaaaaaaaaaaaaaaaaaakeop/dwitbuk
claude plugin install dwitbuk@dwitbuk
```

Codex: `codex plugin marketplace add guinjaaaaaaaaaaaaaaaaaaaaakeop/dwitbuk`, `codex plugin add dwitbuk@dwitbuk`.

Both catalogs at this repository's root name `./plugin` as the plugin's source
([.claude-plugin/marketplace.json](.claude-plugin/marketplace.json),
[.agents/plugins/marketplace.json](.agents/plugins/marketplace.json)), so a host installs that directory and only it.

## Clone and develop

Before changing the source, prepare the development environment as [AGENTS.md](AGENTS.md#preparing-the-environment)
says: read `hunsu.json` with this machine's `hunsu.local.json`, then use the pinned hunsu release's own `install` and
`check`. Using dwitbuk in another project needs only the Install above, never this repository's hunsu files.

| path | installed | what |
|---|---|---|
| [plugin/](plugin/) | yes, all of it | the payload: `dwitbuk.py` (engine and CLI), `eyes_worker.py` (the eyes' host session), `hostcall.py` (the family's vendored host call), `hooks/`, `commands/`, `skills/review/SKILL.md`, the manifests `plugin.json`, `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`, `README.md` and `LICENSE` |
| `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json` | no | the Claude and Codex catalogs; hosts read them to find `./plugin` |
| [dwitbuk.py](dwitbuk.py), [eyes_worker.py](eyes_worker.py) | no | entry points for a checkout, no engine code (below) |
| [test_dwitbuk.py](test_dwitbuk.py) | no | the self-check |
| [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md) | no | maintainer guidance |
| `hunsu.json`, `hunsu.lock.json`, `hunsu-judgments.json` | no | this repository's own agent environment: it is developed with the released family, not with this checkout |
| `.chongdae/`, `reviews/`, `.dwitbuk/` | no | this repository's own run and review records and machine-local state |
| [LICENSE](LICENSE) | no | the repository's license; `plugin/LICENSE` is the same text, shipped |

The runtime has one source, `plugin/`. It imports nothing above that directory and no other plugin's checkout, and it
holds no symlink. Run it from a checkout as an installation runs it:

```sh
python3 plugin/dwitbuk.py follow --target /path/to/project
python3 plugin/eyes_worker.py --help
```

`python3 dwitbuk.py …` and `python3 eyes_worker.py …` at the root still work. Before 2.1.0 the root was the plugin, and
resolvers released before this layout (chongdae 2.0.0's `{plugin:NAME}`) take a `hunsu.local.json` link to a checkout as
the plugin's root. Each runs `plugin/<the same name>` as `__main__`, with `plugin/` first on `sys.path` and the root
taken off it. Imported with a checkout root on `sys.path`, each puts the payload's module in its place in `sys.modules`,
so every importer shares one engine instance. They are not installed, and code belongs in `plugin/`, never in them.
`hostcall.py` is a module, not a command, and lives only in `plugin/`. A check that compares the family's vendored
copies reads it there.

To try the working source in a project, add this checkout as a local marketplace (`claude plugin marketplace add
<checkout>`) and use `hunsu dev dwitbuk --market <its name>`, or link the plugin to this checkout in `hunsu.local.json`.
The host runs a directory marketplace's plugin in place from the catalog's source, and from 2.1.0 dwitbuk resolves
both the same way, to `plugin/`.
Git ignores Python bytecode, and the self-check writes none into `plugin/`.

## Maintainer guidance and hosts

[AGENTS.md](AGENTS.md) holds this repository's maintenance guidance. It is not part of the plugin and is not
automatically injected into a project that installs it. Codex discovers repository guidance along its project path
([Codex guidance loading](https://learn.chatgpt.com/docs/agent-configuration/agents-md)). Claude Code's direct
`AGENTS.md` support depends on version and settings; [CLAUDE.md](CLAUDE.md) contains only `@AGENTS.md` as a
compatibility import, so the maintainer rules still have one source
([Claude memory and imports](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools)).
The installed procedure is [plugin/skills/review/SKILL.md](plugin/skills/review/SKILL.md), shared by both hosts; host
integration and the CLI are described in [plugin/README.md](plugin/README.md#shared-guidance-and-hosts).

## Versioning

Semver, and a version names one content: every change to the payload — code, skill or command text, hooks, its README —
bumps the version in all three manifests (`plugin/plugin.json`, `plugin/.claude-plugin/plugin.json`,
`plugin/.codex-plugin/plugin.json`) and the marketplace entries before it is used anywhere. Hosts copy a plugin at
install and do not look again while the version stands, so an unbumped edit is a copy nobody can tell from the old one.
**patch**: behavior or wording, every interface unchanged. **minor**: a new command, skill, field, hook or artifact key;
what exists keeps working. **major**: an artifact type, lock or record that other products read changes shape, or a
supported Python or host version is dropped (an `engines` floor rises, as `python` from 3.9 to 3.11 did in 2.0.0).
hunsu's `check` fails a linked plugin whose source differs from the installed copy under one version; for a locally
linked plugin, `hunsu install --refresh <plugin>` re-snapshots after the bump.

2.1.0 is a minor release. The payload moved to `plugin/`, the catalogs' source became `./plugin`, `plugin/README.md` is
shipped, and a link or in-place directory marketplace now resolves through its catalog. Nothing an installation runs was
removed or renamed: commands, hooks, the skill, roles, reads, artifacts and the Python floor are unchanged, and the root
entry points keep checkout paths working.

### Release and adoption

Documentation and shared instruction edits also need a patch bump when interfaces stay unchanged. Changes only to
development files outside `plugin/` (tests, this README, `AGENTS.md`) do not change what is installed.
Keep the version equal in `plugin/plugin.json`, `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`,
and the root `.claude-plugin/marketplace.json` (both `metadata.version` and this product's `plugins[].version`).
`.agents/plugins/marketplace.json` has no version field; verify its product name and source path (`./plugin`),
but do not invent a version field there.

Before publication, run the relevant checks in **Self-check** for behavior changes; for documentation-only
changes, verify links, command examples, imports and manifest consistency, plus `git diff --check`.
Publish the checked commit using this repository's existing release convention. Publication does not update
consumer installations: update the plugin through the host's supported workflow, reconcile the consuming
project's declared environment and lock if managed, and start a new host session to apply the installation.
Report publication, project adoption and live-host verification separately. Refreshing a locally linked
plugin is not an update procedure for every remote installation.

## Self-check

`python3 test_dwitbuk.py` from this directory: a temp project in which every stop, rejection and kind of finding fires
once, with recorded provider responses where a model would have answered. No model calls. The tests exercise
`plugin/`. The package checks:

- `plugin/` holds the whole runtime and nothing else: no tests, hunsu environment, run, review or model records,
  bytecode or symlinks.
- Every path a manifest, hook, command or catalog names is inside it, and its README links nowhere above it.
- A copy of `plugin/` alone, outside the checkout with no import path into it, runs the actual CLI through a small
  review, dispose and late-eyes workflow, with a fake `claude` on `PATH` as the host. It also runs the hooks.
- The root entry points delegate to the payload with one module instance.
