import fs from 'node:fs'
import {
  listProfileNames, loadProfileStrict, validateProfileObject,
  loadConfig, saveConfig, saveProfile, withLock, caseVariantOf,
} from '../store.mjs'
import { isValidProfileName } from '../reserved.mjs'
import { syncUnitHash, canonicalSyncMeta } from '../sync.mjs'

/**
 * Hidden remote-side handler (`agentswap __sync`). Always returns a JSON
 * envelope — the SSH transport parses stdout, so mixed human text would be
 * indistinguishable from a broken remote.
 *
 * @param {string|null} sub
 * @param {string|null} [name]
 * @returns {Promise<{ output: string, exitCode: number }>}
 */
export async function syncAgent(sub, name = null) {
  if (sub === 'list') return listHashes()
  if (sub === 'read') return readOne(name)
  if (sub === 'write') return writeOne(name)
  return fail('unknown-sub', `unknown __sync subcommand: ${sub}`)
}

/**
 * Keep only the sync-safe meta fields. `remotes` membership is filtered
 * through the same name chokepoint as profiles so a hand-edited payload
 * cannot inject a path-traversal token into config.json.
 *
 * @param {unknown} meta
 * @returns {{ notes: string, launchArgs: string[]|null, unsetEnv: string[], remotes: string[] }}
 */
export function sanitizeMeta(meta) {
  const m = canonicalSyncMeta(meta)
  m.remotes = m.remotes.filter(isValidProfileName)
  return m
}

/** Meta currently stored for a profile (defaults when absent). */
function storedMeta(name) {
  return sanitizeMeta(loadConfig().profiles?.[name])
}

function listHashes() {
  const profiles = {}
  const errors = []
  for (const name of listProfileNames()) {
    try {
      const profile = loadProfileStrict(name)
      // The sync unit is profile + meta: a meta-only change must move the hash.
      profiles[name] = syncUnitHash(profile, storedMeta(name))
    } catch (e) {
      errors.push({ name, detail: e.message })
    }
  }
  return ok({ profiles, errors })
}

function readOne(name) {
  if (!name) return fail('usage', 'usage: __sync read <name>')
  let profile
  try {
    profile = loadProfileStrict(name)
  } catch (e) {
    return fail('profile-unreadable', e.message)
  }
  if (profile == null) return fail('not-found', `profile not found: ${name}`)
  const meta = storedMeta(name)
  return ok({ profile, meta, hash: syncUnitHash(profile, meta) })
}

async function writeOne(name) {
  let raw
  try {
    raw = fs.readFileSync(0, 'utf8')
  } catch (e) {
    return fail('invalid-json', e.message)
  }
  let body
  try {
    body = JSON.parse(raw)
  } catch (e) {
    return fail('invalid-json', e.message)
  }
  const v = validateProfileObject(body?.profile)
  if (!v.ok) return fail('invalid-profile', v.reason)
  const meta = sanitizeMeta(body.meta)

  return await withLock(() => {
    // A pushed "Work" must not land beside this machine's "work": one file on
    // macOS/Windows, and an unportable pair everywhere else. Refused even on
    // the force path — force overrides a conflict, not a collision.
    const other = listProfileNames().includes(name) ? null : caseVariantOf(name)
    if (other) return fail('name-collision', `profile "${other}" already has this name ignoring case on this machine`)
    // CAS over the SAME sync unit the write overwrites (profile + meta):
    // expectedHash present (including null = "must be absent") is the
    // compare-and-swap path; the key's absence is the force/overwrite path —
    // hasOwnProperty, not a null check, so a create (`expectedHash: null`)
    // is not mistaken for a force.
    const has = Object.prototype.hasOwnProperty.call(body, 'expectedHash')
    if (has) {
      const current = loadProfileStrict(name)
      const currentHash = current === null ? null : syncUnitHash(current, storedMeta(name))
      if (currentHash !== body.expectedHash) {
        return fail('conflict', `remote profile "${name}" changed since the last sync`)
      }
    }
    saveProfile(name, body.profile)
    const config = loadConfig()
    config.profiles[name] = meta
    saveConfig(config)
    return ok({ hash: syncUnitHash(body.profile, meta) })
  })
}

function ok(obj) {
  return { output: JSON.stringify({ version: 2, ...obj }, null, 2), exitCode: 0 }
}

function fail(error, detail) {
  return { output: JSON.stringify({ version: 2, error, detail }, null, 2), exitCode: 1 }
}
