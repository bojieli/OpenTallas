/** Reserved subcommand names — cannot be used as profile names. */
export const RESERVED = new Set([
  'use', 'run', 'save', 'list', 'ls', 'current', 'show', 'add', 'edit', 'rm', 'remove',
  'diff', 'doctor', 'import', 'skill', 'help', 'version', 'backup', 'restore', 'web',
  'remote', 'push', 'pull', 'sync', '__sync',
])

export function isReserved(name) {
  return RESERVED.has(String(name).toLowerCase())
}

// Profile names are filenames (profiles/<name>.json) AND live in the top-level
// command namespace (`agentswap <name>`): alnum start, then alnum/_/-, no leading dash.
// Validated at the path-construction chokepoint so no entry point can traverse
// outside the profiles directory.
export const NAME_RE = /^[a-z0-9][a-z0-9_-]*$/i

export function isValidProfileName(name) {
  return typeof name === 'string' && name.length > 0 && name.length <= 64 && NAME_RE.test(name)
}
