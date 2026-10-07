---
name: agentswap
description: Switch and launch coding-agent configs (providers/models/settings) via the `agentswap` CLI, and launch config-specific panes in herdr. Use when the user wants to switch profiles, launch the agent with a specific config, list/compare configs, or open a herdr pane running a specific profile. Trigger on: "切到 xx 配置", "用 xx 配置跑", "有哪些配置", "换个 provider", "开个 pane 跑 xx", "agentswap", or any request to change/launch a coding-agent configuration.
---

# agentswap — Agent Config Switch

`agentswap` manages multiple coding-agent configs (different providers/models/settings) as **profiles**. A profile **is a complete `settings.json` snapshot** — the whole file, editable and `cp`-able. Switching is a **verbatim whole-file overwrite**: no diffs, no merge, no managed keys. agentswap never parses the settings' internals, so the agent can add/rename any key and agentswap is unaffected.

Consequence: shared config is **not** auto-synced — each profile carries its own full settings. `agentswap save` exists so a change made live is never silently lost on the next switch.

**Two modes:**
- **Sticky** (`agentswap use <name>` or `agentswap <name>`): overwrites the agent's `settings.json` and launches the agent. Persists until the next switch. Best for interactive terminal use.
- **Per-launch** (`agentswap run <name>`): writes the profile to a private temp file and launches via `--settings` without touching any persistent state. Parallel-safe — use for herdr panes, scripts, or running multiple configs at once.

## Machine-readable help

The CLI is self-describing. Run `agentswap help --json` for the full command list, and `agentswap help <cmd> --json` for one command's schema (usage, arguments, options, examples). `agentswap <cmd> --help --json` works too. This skill's command list is **guidance, not the contract** — when flags or subcommands disagree, trust `help --json`.

JSON errors are `{ "version": 2, "error": "…", "detail": "…", "hint": "…" }` (`hint` optional). Follow `hint` when present (it is the next command to run).

---

## When to use this skill

- User wants a different provider/model ("切到 work 配置", "用 personal 跑")
- User asks what configs exist ("有哪些配置")
- User wants to launch the agent with a specific config for a task
- User wants a new herdr pane (or worker) running a specific profile

---

## Query profiles (read-only, safe)

`agentswap list --json` / `agentswap current --json` for names and drift; `show` / `diff` to inspect (secrets masked). **Do not** read files under the agentswap config dir — go through the CLI. Flags and schemas: `agentswap help --json`.

---

## Launch the agent

### Interactive / sticky (default for human terminals)
```bash
agentswap <name>               # overwrite settings.json + launch
agentswap                       # relaunch with the current active profile
agentswap <name> -- --resume    # args after -- pass through
```

### Parallel / scripted / herdr panes (no global state change)
```bash
agentswap run <name>
agentswap run <name> -- --resume   # pass-through args
```

`agentswap run <name> --json-cmd` returns the launch plan (`command`, `args`, `envKeys`) for a worker to execute — **env key names only, never values, and no temp file is written**.

### `run` ≠ sticky precedence (state this if it matters)

`--settings` is the agent's **CLI layer** (higher priority than user/project/local): under `agentswap run` the profile **beats** a repo's project/local settings; under sticky `agentswap use` the profile sits at the **user** layer, so repo local/project **override** it. So `agentswap run x` ≠ `agentswap use x` followed by launching the agent.

### Which mode for which job (decide before launching)

| Goal | Use | Why |
|---|---|---|
| Give **one pane / one worker** a specific config | **`agentswap run <name>`** | Private per-launch temp file + injected env for that process only. Does not touch the global settings. Other panes/workers are unaffected; multiple configs run in parallel safely. |
| Change the machine's **default** config (all new terminals) | `agentswap <name>` / `agentswap use` | Overwrites the global settings file. Affects every agent that reads it, including sessions already open. |

**For herdr / any multi-worker or "just this task" scenario, default to `agentswap run`.** Sticky is for "make this my default from now on" — it mutates shared global state and can disrupt other running sessions.

**Isolation boundary (be honest about the limit):** `agentswap run` isolates **settings + auth/routing env** (token, base_url, model, permissions, hooks) per process — perfect for running different **providers/relays** in parallel. It does **not** isolate the shared OAuth login (`.credentials.json`) or installed plugins. Multiple relay-**token** configs in parallel = fully isolated; multiple distinct **OAuth identities** in parallel = not achievable via agentswap (would need separate `CLAUDE_CONFIG_DIR` per worker).

---

## Open a herdr pane with a specific profile

When the user asks for a new pane/worker running a profile (or you need one yourself), use `agentswap run` — never sticky — inside a new herdr pane:

```bash
# 1. split a sibling pane (right for wide panes, down for narrow/tall), keep focus
herdr pane split --current --direction right --cwd "$PWD" --no-focus
#    → read the new pane id from .result.pane.pane_id in the JSON

# 2. launch the profile in it (foreground agent process, not a detached command)
herdr pane run <pane-id> "agentswap run <name>"
```

For a **named agent pane** (herdr tracks its lifecycle: idle/working/blocked), start the agent through herdr instead of a raw command:

```bash
herdr agent start <unique-name> --kind claude --pane <pane-id> -- --dangerously-skip-permissions
# then drive it:
herdr agent prompt <unique-name> "your task" --wait --timeout 120000
```

Rules:
- Verify you are inside herdr first: `test "${HERDR_ENV:-}" = 1`. If not, say so and stop.
- Use `--no-focus` for background panes unless the user asked to switch context.
- Use the returned pane ID / agent name — never derive IDs from the sidebar.
- One profile per pane; don't run two `agentswap run` sessions in one pane.
- If the pane should also do repo work, pass `--cwd` explicitly (default is the caller's cwd).

---

## `agentswap save` (baseline provenance)

After settings are edited live (the agent's model switch "save as default", or a hand edit), `agentswap save` writes the live settings back into the **active** profile so the next switch doesn't lose them. agentswap keeps a **baseline hash** of what it last applied to tell which side changed:

- live changed, profile didn't → `save` stores live into the profile
- profile changed, live didn't → nothing to save; the next switch just applies it
- **both** changed → **conflict**: `save` and switch **refuse** until you pick a side (`agentswap save --overwrite-profile` forces live; `agentswap use <name> --discard` drops live)

Don't auto-save `run` sessions — a "save as default" inside a run writes the user-layer file and can show up as spurious `agentswap current` drift.

---

## Manage profiles (ask the user first)

Creating, editing, deleting, importing, and the web UI all mutate stored profiles — ask first. Command schemas: `agentswap help --json`.

### Create from a platform template

`agentswap add <name>` copies the template for the machine running AgentSwap,
then opens the new profile in the editor. Use `--platform darwin|linux|win32`
when preparing a profile for another platform; Linux processes in WSL use
`linux`. For scripts, `agentswap add <name> --platform linux --json` creates the
profile without opening an editor. `--from-current` instead snapshots the live
settings and cannot be combined with `--platform`.

The local web UI manages the three templates and opens profiles in an env
editor by default. Templates are complete settings snapshots copied only at
creation: editing a template never changes existing profiles. Templates stay
local; syncing a profile still transfers its complete settings and metadata.
Use advanced JSON when a setting is outside env or cannot be represented by
the env editor. Never assume a platform template translates machine paths.

### Red lines
- Never `agentswap show --reveal` unless the user explicitly asks to see secret values. `show`/`diff` mask by default.
- Never hand-edit a profile's tokens/secrets on your own initiative — ask the user.
- `agentswap <name>` / `agentswap use` **overwrites** the live settings file. For one-off or parallel launches, use `agentswap run` instead.
- Never close herdr panes/workspaces you didn't create.

---

## If `agentswap` is not installed

`command -v agentswap` fails → tell the user, then install from the repo's instructions (see README). After install, `agentswap skill install` places this skill in the agent's skills directory.

---

## JSON (version 2)

Command schemas live in `agentswap help --json`, not in this skill. Successful `--json` objects always carry `"version": 2`.

Errors (usage and thrown) when `--json` is set:

```json
{ "version": 2, "error": "usage", "detail": "…", "hint": "run `agentswap help use --json` for the full schema" }
```

Follow `hint` when present.

`agentswap current --json` — `status` ∈ `in-sync | live-unsaved | profile-edited | conflict | unknown | none`; `unsaved` is `true|false|null` (`null` when undeterminable, with a nonzero exit).

`agentswap run <name> --json-cmd` returns the launch plan (`command`, `args`, `envKeys`) — **env key names only, never values, and no temp file is written**.
