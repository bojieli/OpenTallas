/**
 * Command registry — the single source of truth for the command surface.
 * Human HELP text, `help --json` schemas, and usage-error strings all generate
 * from these entries, so the three can never drift. When you add a command,
 * register it here AND in src/reserved.mjs.
 *
 * Launch modes (`agentswap <name>`, bare relaunch) are not subcommands — they
 * live in MODES and render in the Human section of HELP.
 */

const arg = (name, description, required = false) => ({ name, required, description })
const opt = (flags, description, extra = {}) => ({ flags, description, ...extra })

export const GROUPS = [
  ['launch', 'Human'],
  ['core', 'Agent / script'],
  ['sync', 'Multi-machine sync'],
]

export const MODES = [
  { usage: 'agentswap <name> [args…]', description: 'switch to <name> (whole-file overwrite) and launch the agent' },
  { usage: 'agentswap [args…]', description: 'relaunch with the current active profile (no switch)' },
  { usage: 'agentswap <name> -- args…', description: '`--` separates pass-through args explicitly' },
  { usage: 'agentswap <name> --discard | --overwrite-profile', description: 'resolve unsaved-change / conflict guards' },
]

export const COMMANDS = [
  {
    name: 'use', group: 'core',
    description: 'sticky switch to a profile (whole-file overwrite), no launch',
    usage: 'agentswap use <name> [--json] [--discard] [--overwrite-profile]',
    arguments: [arg('name', 'profile to switch to', true)],
    options: [
      opt('--json', 'machine-readable output'),
      opt('--discard', 'discard unsaved live changes when switching'),
      opt('--overwrite-profile', 'overwrite the profile with live settings on conflict'),
    ],
    examples: ['agentswap use work', 'agentswap use work --json'],
  },
  {
    name: 'save', group: 'core',
    description: 'save live settings into the active profile',
    usage: 'agentswap save [--json] [--overwrite-profile]',
    arguments: [],
    options: [
      opt('--json', 'machine-readable output'),
      opt('--overwrite-profile', 'overwrite the profile even when it was edited since last apply'),
    ],
    examples: ['agentswap save', 'agentswap save --json'],
  },
  {
    name: 'run', group: 'core',
    description: 'per-launch override via a private temp settings file, parallel-safe',
    usage: 'agentswap run <name> [--json-cmd] [--save-on-exit] [-- args…]',
    arguments: [arg('name', 'profile to launch with', true)],
    options: [
      opt('--json-cmd', 'emit the launch plan (command, args, env key names) instead of launching'),
      opt('--save-on-exit', 'save live settings back into the profile when the agent exits'),
      opt('--', 'pass remaining args through to the agent'),
    ],
    examples: ['agentswap run work', 'agentswap run work --json-cmd', 'agentswap run work -- --resume'],
  },
  {
    name: 'current', group: 'core',
    description: 'show the active profile and unsaved-changes status',
    usage: 'agentswap current [--json]',
    arguments: [],
    options: [opt('--json', 'machine-readable output')],
    examples: ['agentswap current', 'agentswap current --json'],
  },
  {
    name: 'list', group: 'core',
    description: 'list profiles',
    usage: 'agentswap list [--json]',
    arguments: [],
    options: [opt('--json', 'machine-readable output')],
    examples: ['agentswap list', 'agentswap list --json'],
  },
  {
    name: 'show', group: 'core',
    description: 'print a profile (secrets masked unless --reveal)',
    usage: 'agentswap show <name> [--reveal] [--json]',
    arguments: [arg('name', 'profile to print', true)],
    options: [
      opt('--reveal', 'show secret values instead of masking them'),
      opt('--json', 'machine-readable output'),
    ],
    examples: ['agentswap show work', 'agentswap show work --reveal'],
  },
  {
    name: 'diff', group: 'core',
    description: 'deep JSON diff of two profiles, or a profile vs live settings',
    usage: 'agentswap diff <a> [b] [--json]',
    arguments: [arg('a', 'first profile (or vs live when b omitted)', true), arg('b', 'second profile')],
    options: [opt('--json', 'machine-readable output')],
    examples: ['agentswap diff work personal', 'agentswap diff work'],
  },
  {
    name: 'add', group: 'core',
    description: 'create a new profile (template, or snapshot of live settings)',
    usage: 'agentswap add <name> [--from-current] [--platform <platform>]',
    arguments: [arg('name', 'new profile name', true)],
    options: [
      opt('--from-current', 'snapshot the current live settings.json instead of a template'),
      opt('--platform <platform>', 'create from a specific platform template (darwin|linux|win32)'),
    ],
    examples: ['agentswap add personal', 'agentswap add work --from-current', 'agentswap add ci --platform linux'],
  },
  {
    name: 'edit', group: 'core',
    description: 'open a profile in $EDITOR',
    usage: 'agentswap edit <name>',
    arguments: [arg('name', 'profile to edit', true)],
    options: [],
    examples: ['agentswap edit work'],
  },
  {
    name: 'rm', group: 'core',
    description: 'delete a profile (refuses the active one without --force)',
    usage: 'agentswap rm <name> [--force]',
    arguments: [arg('name', 'profile to delete', true)],
    options: [opt('--force', 'delete even when the profile is active')],
    examples: ['agentswap rm personal', 'agentswap rm work --force'],
  },
  {
    name: 'backup', group: 'core',
    description: 'list the rotated settings/profile backup pools',
    usage: 'agentswap backup list [--json]',
    arguments: [],
    options: [opt('--json', 'machine-readable output')],
    examples: ['agentswap backup list'],
  },
  {
    name: 'restore', group: 'core',
    description: 'restore a settings.json backup (dry-run without --yes)',
    usage: 'agentswap restore <file> [--yes]',
    arguments: [arg('file', 'backup file to restore', true)],
    options: [opt('--yes', 'actually write the restore')],
    examples: ['agentswap restore backups/settings/…json', 'agentswap restore <file> --yes'],
  },
  {
    name: 'import', group: 'core',
    description: 'import profiles from a JSON export (dry-run without --apply)',
    usage: 'agentswap import <file> [--apply]',
    arguments: [arg('file', 'JSON export to import', true)],
    options: [opt('--apply', 'write the new profiles (existing ones are never overwritten)')],
    examples: ['agentswap import profiles.json', 'agentswap import profiles.json --apply'],
  },
  {
    name: 'web', group: 'core',
    description: 'local web management UI (loopback only, per-session token)',
    usage: 'agentswap web [--port N] [--no-open]',
    arguments: [],
    options: [
      opt('--port <N>', 'listen on this port'),
      opt('--no-open', 'do not open the browser'),
    ],
    examples: ['agentswap web', 'agentswap web --port 7878 --no-open'],
  },
  {
    name: 'skill', group: 'core',
    description: 'install the bundled agent skill',
    usage: 'agentswap skill install [--force]',
    arguments: [],
    options: [opt('--force', 'overwrite an existing installation')],
    examples: ['agentswap skill install'],
  },
  {
    name: 'doctor', group: 'core',
    description: 'environment diagnostics',
    usage: 'agentswap doctor [--json]',
    arguments: [],
    options: [opt('--json', 'machine-readable output')],
    examples: ['agentswap doctor'],
  },
  {
    name: 'version', group: 'core',
    description: 'print the agentswap version',
    usage: 'agentswap version',
    arguments: [],
    options: [],
    examples: ['agentswap version'],
  },
  {
    name: 'remote', group: 'sync',
    description: 'manage remote sync targets (add / ls / rm)',
    usage: 'agentswap remote <add|ls|rm> [args…]',
    arguments: [
      arg('sub', 'add | ls | rm', true),
      arg('name', 'remote name (add/rm)'),
    ],
    options: [
      opt('--host <ssh-host>', 'SSH alias or user@host (add)'),
      opt('--bin <path>', 'path to agentswap on the remote (add; default: agentswap)'),
      opt('--json', 'machine-readable output'),
    ],
    examples: ['agentswap remote add vps --host myvps', 'agentswap remote ls', 'agentswap remote rm vps'],
  },
  {
    name: 'push', group: 'sync',
    description: 'push a profile to its remotes (or the named ones)',
    usage: 'agentswap push <name> [remote...] [--force] [--json]',
    arguments: [
      arg('name', 'profile to push', true),
      arg('remote…', 'remotes to push to (default: the profile\'s membership)'),
    ],
    options: [
      opt('--force', 'overwrite remote changes (skip the conflict guard)'),
      opt('--json', 'machine-readable output'),
    ],
    examples: ['agentswap push work', 'agentswap push work vps --force'],
  },
  {
    name: 'pull', group: 'sync',
    description: 'pull a profile from its remotes (or the named one)',
    usage: 'agentswap pull <name> [remote...] [--force] [--json]',
    arguments: [
      arg('name', 'profile to pull', true),
      arg('remote…', 'remotes to pull from (default: the profile\'s membership; they must agree)'),
    ],
    options: [
      opt('--force', 'overwrite local changes (skip the conflict guard)'),
      opt('--json', 'machine-readable output'),
    ],
    examples: ['agentswap pull work', 'agentswap pull work vps'],
  },
  {
    name: 'sync', group: 'sync',
    description: 'reconcile every profile with every remote (or the named ones)',
    usage: 'agentswap sync [remote...] [--force-push] [--force-pull] [--json]',
    arguments: [arg('remote…', 'remotes to sync (default: all)')],
    options: [
      opt('--force-push', 'resolve conflicts by taking local'),
      opt('--force-pull', 'resolve conflicts by taking remote'),
      opt('--json', 'machine-readable output'),
    ],
    examples: ['agentswap sync', 'agentswap sync vps', 'agentswap sync --force-pull'],
  },
]

export function getCommand(name) {
  return COMMANDS.find(c => c.name === name) ?? null
}

/** Render the human HELP text from the registry. */
export function renderHelp() {
  const lines = ['agentswap — agent-config-switch (profile = complete settings snapshot)', '']
  for (const [group, title] of GROUPS) {
    lines.push(`${title}:`)
    const entries = group === 'launch'
      ? MODES
      : COMMANDS.filter(c => c.group === group)
    const width = Math.max(...entries.map(e => e.usage.length))
    for (const e of entries) {
      lines.push(`  ${e.usage.padEnd(width)}   ${e.description}`)
    }
    lines.push('')
  }
  return lines.join('\n')
}
