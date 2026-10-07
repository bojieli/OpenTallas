# AgentSwap

**Agent Config Switch** — multi-platform config switcher & launcher for coding agents.

Manage multiple agent configurations (different providers, models, relays, hooks, permissions) as **profiles**. Switch between them instantly, launch several configs side by side in different panes, and edit everything through a local web UI.

- **macOS, Linux, Windows** — one Node.js codebase, no native deps
- **Two launch modes** — sticky (machine default) or per-launch (parallel-safe)
- **Safe by default** — whole-file profiles, drift detection, conflict guards, secret masking, 0600 files
- **Local web UI** — `agentswap web` for visual profile editing
- **Multi-machine sync** — push/pull/sync profiles over SSH; no daemon, no server
- **Agent-friendly** — `--json` contracts everywhere, plus a skill that teaches agents to use AgentSwap and open herdr panes with a specific profile

## Install

Requires Node.js ≥ 20. The CLI command is `agentswap` (short alias `aswap`).

```bash
# from a clone of this repo
npm install -g .

# or run directly without installing
node bin/agentswap.mjs <command>
```

The agent CLI must be on your PATH for launch commands.

## Quick start

```bash
# Snapshot your current settings into a profile
agentswap add work --from-current

# Create from this platform’s template and edit it ($EDITOR)
agentswap add personal

# Switch (overwrites the agent's settings.json) and launch
agentswap work

# List / inspect
agentswap list
agentswap show personal          # secrets masked
agentswap diff work personal

# Launch a one-off config without touching global state (great for panes)
agentswap run personal

# Visual management
agentswap web
```

## Concepts

**A profile is a complete `settings.json` snapshot.** The whole file — env, model, hooks, permissions, statusLine, anything. Switching is a verbatim whole-file overwrite: no field merging, no managed keys, no partial updates. This means AgentSwap never needs to understand the settings format, and new agent settings keys work automatically.

Trade-off: shared config is **not** auto-propagated across profiles. Each profile carries its own full settings. `agentswap save` writes live changes back into the active profile so nothing is silently lost.

**Two modes:**

| | Sticky (`agentswap <name>` / `agentswap use`) | Per-launch (`agentswap run <name>`) |
|---|---|---|
| Effect | Overwrites the agent's `settings.json` | Writes a private 0600 temp file, passed via `--settings` |
| Scope | Machine default — affects new sessions | One process only |
| Parallel-safe | No | Yes |
| Best for | Interactive terminals | herdr panes, scripts, multi-agent work |

`run` precedence note: `--settings` is the agent's CLI layer, which **beats** project/local settings; sticky mode sits at the user layer, so repo settings override it. `agentswap run x` ≠ `agentswap use x` followed by launching the agent.

**Drift detection.** AgentSwap records a content-hash baseline of what it last applied. On every switch/save it compares three hashes — live settings, active profile, baseline — to tell which side changed:

- live changed, profile didn't → `agentswap save` stores live into the profile
- profile changed, live didn't → next switch just applies it
- **both changed → conflict**: switch and save refuse until you pick a side (`--discard` drops live, `--overwrite-profile` keeps live)

**Launch env hygiene.** Both modes strip the inherited auth/routing env namespace (provider tokens, base URLs, and agent-specific auth keys) before injecting the profile's own `env`, so a stale token from a parent shell can't shadow the profile's provider. Profile `env` values of `null` explicitly delete a key.

## Commands

```
agentswap <name> [args…]              switch + launch (args pass through to the agent)
agentswap [args…]                     relaunch with the active profile
agentswap <name> --discard            drop unsaved live changes and switch
agentswap <name> --overwrite-profile  save live into the active profile, then switch

agentswap use <name> [--json]         sticky switch without launching
agentswap save [--json]               save live settings → active profile
agentswap run <name> [--json-cmd] [--save-on-exit] [-- args…]
agentswap current [--json]            active profile + drift status
agentswap list [--json]
agentswap show <name> [--reveal] [--json]
agentswap diff <a> [b] [--json]       two profiles, or profile vs live
agentswap add <name> [--from-current] [--platform <platform>]
agentswap edit <name>                 open in $EDITOR
agentswap rm <name> [--force]
agentswap import <file> [--apply]     import profiles from a JSON export (dry-run default)
agentswap backup list [--json]
agentswap restore <file> [--yes]      restore a backup (dry-run default)
agentswap web [--port N] [--no-open]  local web UI
agentswap skill install [--force]     install the agent skill
agentswap doctor [--json]             environment diagnostics
agentswap version

agentswap remote add <name> --host <ssh-host> [--bin <path>]
agentswap remote ls
agentswap remote rm <name>
agentswap push <name> [remote...] [--force]
agentswap pull <name> [remote...] [--force]
agentswap sync [remote...] [--force-push] [--force-pull]
```

All `--json` outputs share a stable `{ "version": 2, ... }` contract. `agentswap help --json` is the machine-readable command reference.

## Multi-machine sync

Profiles can move between machines over SSH. There is no daemon and no listening port: the other machine needs `agentswap` installed and key-based SSH (`ssh <host>` must not prompt). Each profile opts into remotes; `push` / `pull` / `sync` then decide direction with a three-way hash (local / remote / last-synced baseline). Both sides changed, or there is no baseline yet, is a **conflict** — the same fail-closed rule as a local switch. Deleting a profile is local-only; a copy that still exists on the other side comes back on the next sync.

```bash
agentswap remote add vps --host vps     # probes `agentswap version` over SSH
agentswap push work vps                 # send a profile; records membership
# …edit `work` on the VPS, `agentswap save`…
agentswap sync                          # VPS moved, we didn't → pull
```

`--force` / `--force-push` / `--force-pull` pick a side. Design, membership, and what is *not* synced (active profile, backups, `sync.json`): [docs/sync.md](docs/sync.md).

## Web UI

```bash
agentswap web            # picks a free port, opens your browser
agentswap web --port 47831 --no-open
```

- Sidebar with all profiles, active marker, and live drift status (every
  reconcile state gets its own label, not just "unsaved")
- **Daily editor is an env table** — arbitrary key/value rows (values masked by
  default with an explicit show control). Deleting a key is not the same as
  setting it to `""`. Non-string / `null` env values lock to Advanced JSON
- **Advanced edit** keeps the previous seven section tabs (model, behavior,
  permissions, hooks, plugins, launch, raw JSON) behind an explicit mode
  switch — one JSON truth, not a second config store
- **Platform templates** (macOS / Linux / Windows) live in the rail: edit each
  template's full settings JSON. New profiles pick a platform and seed from
  that template (`{ env: {} }` by default); editing a template only affects
  *later* creates. Optionally still create from the current live settings
  (never mixed with `platform` in the same request)
- Env-only saves preserve unedited launch metadata (`notes` / `launchArgs` /
  `unsetEnv`) so a spaced launch arg is not re-split by a pure env edit
- **Model** (Advanced): base URL, credential (token or API key), model, per-role
  model mapping, fallback models
- **Behavior**: ~50 form controls over the settings keys people actually tune —
  thinking effort and budget, theme and renderer, status line, capability
  switches, update channel and privacy flags, git attribution. Booleans are
  tri-state (*default / on / off*): a profile is a whole-file snapshot, so
  "leave this key out" is a distinct choice from "set it to false"
- **Permissions**: allow / ask / deny rule lists, extra working directories,
  the starting permission mode, and the sandbox switches
- **Hooks**: one card per hook — pick the event, the matcher, the command —
  instead of hand-nesting `event → matcher group → handler[]`. Plus a **hook
  library**: eleven bundled presets (destructive-command guard, secret-file
  guard, format-on-edit, trace log, turn-end chime, repo-state injection, …),
  each carrying a separate command per platform, so a profile bound for a
  Windows box gets the Windows variant. "Save to library" files a hook you
  wrote onto the shelf (`AGENTSWAP_HOME/hooks.json`) for the next profile
- **Plugins**: enabled plugins, extra marketplaces, MCP server approval
- Raw settings JSON editor with validation — its own Advanced tab, since it
  shows the credential in clear text
- The structured tabs are a lossless *projection* of the JSON, never a filter:
  a key no control owns rides through untouched, and a value a control cannot
  represent locks its row (*edit in JSON*) rather than being rewritten. A live
  15-key, 18-hook `settings.json` round-trips byte for byte
- Create profiles in place, from a platform template or the current live settings
- Remotes section: register and unregister remotes, browse their profiles,
  edit them over the same SSH sync protocol
- Saves are compare-and-swap everywhere — an edit that raced a CLI write (or
  a concurrent remote edit) is a conflict prompt, not a silent overwrite;
  template saves refuse force-overwrite on conflict (reload required)
- Unsaved edits are guarded: typing during a save stays dirty, and a navigation
  or template reload that fails hands the draft back unsaved-and-protected (it
  can't be saved while it is being replaced). Navigating away or closing the tab asks first;
  `Cmd/Ctrl+S` saves; dialogs close on `Esc` and confirm on `Enter`
- Binds to `127.0.0.1` only; every API call (reads included) requires a
  per-session token delivered via the `#fragment` of the startup URL, and the
  Host header must be loopback (CSRF / DNS-rebinding safe)

## Agent skill

`agentswap skill install` installs the bundled skill from `skills/agentswap/` into the agent's skills directory. The skill teaches agents to:

- discover and switch profiles via the `--json` contracts
- choose sticky vs `run` correctly
- open their own herdr panes running a specific profile (`herdr pane split` + `agentswap run`)
- respect the red lines (never reveal secrets, never sticky-switch for one-off tasks)

## Cross-platform

| | macOS | Linux | Windows |
|---|---|---|---|
| Config dir | `~/.config/agentswap` | `~/.config/agentswap` | `%APPDATA%\agentswap` |
| Editor | `$EDITOR` / `$VISUAL` | same | same, `notepad` fallback; `.cmd` editors like `code` work by name |
| Launch | direct spawn | direct spawn | `cmd.exe` shim wrapper for npm `.cmd` bins |

`$EDITOR` may carry arguments (`code --wait`); quote a path that contains spaces (`"C:\Program Files\…\code.cmd" --wait`).

Override AgentSwap's config dir with `AGENTSWAP_HOME` (handy for tests and isolated setups). The agent's own config directory is independent and follows the agent's usual override.

Profile names are file names, and the default macOS and Windows filesystems ignore case: `Work` and `work` would be one file there. So on every platform a name resolves exactly (`agentswap use WORK` does not open `work`), and a new name must be unique ignoring case — `add`, `import`, web renames and `sync`/`push` refuse to create `Work` beside `work` (sync reports `name-collision`). Profiles travel between machines, so a set that only works on Linux is refused there too; an existing Linux pair keeps working.

### Windows notes

- Tested design, not yet battle-tested on a real Windows box — please open an issue if something misbehaves.
- Atomic writes retry on `EPERM` (transient AV file locks).
- PowerShell: everything runs through `node`, so profile/args handling is identical; no shell-specific quoting in the CLI itself.
- Launching through an npm `.cmd` shim goes via `cmd.exe`, which expands `%VAR%` in arguments before the agent sees them — a cmd.exe layer behavior no launcher can disable. AgentSwap only ever passes through your own profile name, launchArgs, and command line.

## Layout

```
<AGENTSWAP_HOME>/
├── config.json          # defaults, remotes registry, per-profile meta (notes, launchArgs, unsetEnv, remotes)
├── state.json           # active profile + applied-hash baseline
├── sync.json            # last-synced hashes per remote (machine-local; never synced)
├── profiles/<name>.json # one complete settings snapshot each (0600)
├── run/                 # per-launch temp settings (GC'd by owner pid; *.kept.json never)
└── backups/
    ├── settings/        # live-settings backups (rotated)
    └── profiles/<name>/ # per-profile backups (rotated independently)
```

## Security

- Profile and settings files are written `0600`; dirs `0700`.
- `show` / `diff` / list mask secrets best-effort (key-name taint, env-wide masking, format heuristics). `--reveal` is opt-in.
- `run --json-cmd` emits env key **names** only — never values — and writes no temp file.
- The web UI binds to loopback and requires a per-session token for every API
  call; the token is delivered via the startup URL's `#fragment` and never
  appears in the page HTML or server logs.
- AgentSwap only ever **reads** the agent's credentials file (for diagnostics); it never writes or copies it.

## Development

```bash
node --test            # full suite (unit + CLI e2e in isolated temp dirs)
npm run check          # repo guardrails: zero deps, skill contract, doc routing, redlines
```

The codebase is dependency-free Node.js ESM. `src/` is the library + commands, `bin/agentswap.mjs` is the entry, `src/web/` is the local UI, `skills/agentswap/` is the bundled agent skill.

See [docs/architecture.md](docs/architecture.md) for the design, [docs/sync.md](docs/sync.md) for multi-machine sync, [docs/v1.md](docs/v1.md) for what v1 does and doesn't cover, and [docs/index.md](docs/index.md) for the doc routing table (which docs to update when a path changes).

## License

MIT
