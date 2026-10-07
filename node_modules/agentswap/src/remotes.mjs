import { loadConfig, saveConfig, withLock } from './store.mjs'
import { isValidProfileName } from './reserved.mjs'
import { probeRemote } from './ssh.mjs'
import { readSyncState, writeSyncState } from './sync.mjs'

/** Default remote agentswap binary; override with `--bin` when it is not on PATH. */
export const DEFAULT_BIN = 'agentswap'

/** @returns {Record<string, { host: string, bin: string }>} */
export function listRemotes() {
  return loadConfig().remotes ?? {}
}

/**
 * @param {string} name
 * @returns {{ host: string, bin: string }|null}
 */
export function getRemote(name) {
  return listRemotes()[name] ?? null
}

/**
 * Validate a remote name + target. Same name rule as profiles (the registry
 * is a JSON object keyed by name, not a path, but sharing the chokepoint
 * keeps `remote add` and `add` erroring the same way on `../x`).
 *
 * @param {string} name
 * @param {{ host: string, bin?: string }} spec
 * @returns {string|null} error string, or null if valid
 */
export function validateRemote(name, { host, bin = DEFAULT_BIN }) {
  if (!isValidProfileName(name)) {
    return `invalid remote name: ${JSON.stringify(name)} (letters, digits, _ and -; must start with a letter or digit)`
  }
  if (typeof host !== 'string' || host.length === 0 || /\s/.test(host)) {
    return `invalid host: ${JSON.stringify(host)} (non-empty SSH alias, no whitespace)`
  }
  if (typeof bin !== 'string' || bin.length === 0) {
    return `invalid bin: must be a non-empty command`
  }
  return null
}

/**
 * Register a remote after a version probe. The probe is outside the lock
 * (it is a network round-trip); the existence check is repeated inside so
 * two concurrent adds of the same name cannot both persist.
 *
 * @param {string} name
 * @param {{ host: string, bin?: string, json?: boolean }} [opts]
 * @returns {Promise<{ output: string, exitCode: number }>}
 */
export async function addRemote(name, { host, bin = DEFAULT_BIN, json = false } = {}) {
  const invalid = validateRemote(name, { host, bin })
  if (invalid) return fail(json, 'invalid-remote', invalid)
  if (getRemote(name)) return fail(json, 'exists', `remote already exists: ${name}`, 'run `agentswap remote ls` to see registered remotes')

  try {
    await probeRemote({ host, bin })
  } catch (e) {
    const detail = `${e.message}\nis agentswap installed on the remote and on its PATH? use --bin to give a full path.`
    return fail(json, 'probe-failed', detail)
  }

  const existed = await withLock(() => {
    const config = loadConfig()
    if (config.remotes[name]) return true
    config.remotes[name] = { host, bin }
    saveConfig(config)
    return false
  })
  if (existed) return fail(json, 'exists', `remote already exists: ${name}`)

  if (json) {
    return { output: JSON.stringify({ version: 2, added: name, remote: { host, bin } }, null, 2), exitCode: 0 }
  }
  return { output: `added remote "${name}" → ${host} (bin: ${bin})`, exitCode: 0 }
}

/**
 * Drop a remote from the registry, strip it from every profile's membership
 * array, and forget its sync.json subtree. Membership is machine-local
 * bookkeeping; leaving a dangling name would make later push/sync target a
 * remote that no longer exists.
 *
 * @param {string} name
 * @param {{ json?: boolean }} [opts]
 * @returns {Promise<{ output: string, exitCode: number }>}
 */
export async function removeRemote(name, { json = false } = {}) {
  if (!getRemote(name)) return fail(json, 'not-found', `remote not found: ${name}`, 'run `agentswap remote ls` to see registered remotes')

  await withLock(() => {
    // Baselines first: a crash between the two writes leaves "registered but no
    // baseline" (fail-closed on the next sync) — never "registry gone but a
    // stale baseline survives", which a same-named new remote would adopt as
    // its common ancestor and pull instead of conflict.
    const state = readSyncState()
    delete state.remotes[name]
    writeSyncState(state)
    const config = loadConfig()
    delete config.remotes[name]
    for (const meta of Object.values(config.profiles ?? {})) {
      if (Array.isArray(meta?.remotes)) meta.remotes = meta.remotes.filter(r => r !== name)
    }
    saveConfig(config)
  })

  if (json) return { output: JSON.stringify({ version: 2, removed: name }, null, 2), exitCode: 0 }
  return { output: `removed remote "${name}"`, exitCode: 0 }
}

function fail(json, error, detail, hint = null) {
  return {
    output: json
      ? JSON.stringify({ version: 2, error, detail, ...(hint ? { hint } : {}) }, null, 2)
      : detail,
    exitCode: 1,
  }
}
