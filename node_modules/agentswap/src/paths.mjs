import os from 'node:os'
import path from 'node:path'

/**
 * Path resolution for agentswap. All platform differences live here.
 */

/**
 * The agent's config dir (`CLAUDE_CONFIG_DIR` overrides, like the agent
 * itself). Resolved to an absolute path: state and the journal are bound to
 * a fingerprint of this path, and a relative value would give two different
 * directories (same value, different cwd) one fingerprint.
 */
export function agentConfigDir() {
  const dir = process.env.CLAUDE_CONFIG_DIR
  return dir ? path.resolve(dir) : path.join(os.homedir(), '.claude')
}

/** Path to the agent's settings.json (the file agentswap mutates in sticky mode). */
export function agentSettingsPath() {
  return path.join(agentConfigDir(), 'settings.json')
}

/** Path to the agent's credentials (OAuth). Read-only reference, never mutated. */
export function agentCredentialsPath() {
  return path.join(agentConfigDir(), '.credentials.json')
}

/** Root of agentswap's own state directory. Override with AGENTSWAP_HOME (used by tests). */
export function appHome() {
  if (process.env.AGENTSWAP_HOME) return path.resolve(process.env.AGENTSWAP_HOME)
  if (process.platform === 'win32' && process.env.APPDATA) {
    return path.join(process.env.APPDATA, 'agentswap')
  }
  return path.join(os.homedir(), '.config', 'agentswap')
}

export const profilesDir = () => path.join(appHome(), 'profiles')
export const runDir = () => path.join(appHome(), 'run')
export const backupsDir = () => path.join(appHome(), 'backups')
export const configPath = () => path.join(appHome(), 'config.json')
export const statePath = () => path.join(appHome(), 'state.json')
export const syncStatePath = () => path.join(appHome(), 'sync.json')
/** The user's own hook presets, saved from the web UI's hook library. */
export const hookLibraryPath = () => path.join(appHome(), 'hooks.json')
export const templatesPath = () => path.join(appHome(), 'templates.json')

/**
 * Attempts for a filesystem op whose EPERM may be TRANSIENT: on win32, AV
 * scanners and indexers hold files open for milliseconds. Elsewhere EPERM is
 * a real permission error, so a single attempt.
 */
export const EPERM_ATTEMPTS = process.platform === 'win32' ? 4 : 1

export const KNOWN_PLATFORMS = ['darwin', 'linux', 'win32']

/** Validate whether a string is one of the supported template platforms. */
export function isValidPlatform(platform) {
  return typeof platform === 'string' && KNOWN_PLATFORMS.includes(platform)
}

/** Normalize platform for template lookup, or return null if invalid. */
export function normalizePlatform(platform) {
  if (typeof platform !== 'string') return null
  const p = platform.trim().toLowerCase()
  return KNOWN_PLATFORMS.includes(p) ? p : null
}

