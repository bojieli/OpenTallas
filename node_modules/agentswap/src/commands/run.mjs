import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import {
  loadConfig, profilePath, profileExists, saveProfile,
  withLock, backupProfileBytes, gcRunFilesByOwner, validateProfileObject, KEPT_RUN_SUFFIX,
} from '../store.mjs'
import { runDir } from '../paths.mjs'
import { contentHash } from '../settings.mjs'
import { reconcile } from '../reconcile.mjs'
import { launchAgent, runArgs, launchEnv } from '../launch.mjs'

/**
 * Run mode (per-launch override). No global mutation, parallel-safe. The
 * profile's complete settings go verbatim into a private temp file passed via
 * `--settings` (CLI layer, higher priority than user/project/local — this is
 * explicitly an override mode, not sticky equivalence).
 */
export async function run(name, { extraArgs = [], jsonCmd = false, saveOnExit = false, binName = 'claude' } = {}) {
  if (!profileExists(name)) return { output: `profile not found: ${name}`, exitCode: 1 }
  let profileBytes
  try {
    profileBytes = fs.readFileSync(profilePath(name), 'utf8')
  } catch (e) {
    if (e.code === 'ENOENT') return { output: `profile not found: ${name}`, exitCode: 1 }
    throw e
  }
  let profile
  try {
    profile = JSON.parse(profileBytes)
  } catch (e) {
    return { output: `profile "${name}" is not valid JSON: ${e.message}`, exitCode: 1 }
  }
  const v = validateProfileObject(profile)
  if (!v.ok) {
    return { output: `invalid profile "${name}": ${v.reason}`, exitCode: 1 }
  }

  const cfg = loadConfig()
  const meta = cfg.profiles?.[name] || {}
  const launchArgs = Array.isArray(meta.launchArgs) ? meta.launchArgs : (cfg.defaultLaunchArgs ?? [])
  const unsetEnv = Array.isArray(meta.unsetEnv) ? meta.unsetEnv : []
  const envKeys = Object.keys(profile.env || {})

  // --json-cmd: DO NOT materialize a secret temp file. Emit a stable command +
  // args template + env key NAMES only (never values).
  if (jsonCmd) {
    return {
      output: JSON.stringify({
        version: 2,
        command: `agentswap run ${name}`,
        args: runArgs('<per-run temp settings file>', launchArgs, extraArgs),
        envKeys,
      }, null, 2),
      exitCode: 0,
    }
  }

  // --- materialize the private temp settings file (0600, crypto nonce) ---
  gcRunFilesByOwner()
  fs.mkdirSync(runDir(), { recursive: true })
  const nonce = crypto.randomBytes(6).toString('hex')
  const tmp = path.join(runDir(), `${name}-${process.pid}-${nonce}.json`)
  fs.writeFileSync(tmp, profileBytes, { mode: 0o600 })
  const preHash = contentHash(profile)

  const env = launchEnv(profile.env, { unsetEnv })
  const args = runArgs(tmp, launchArgs, extraArgs)
  const code = await launchAgent({ args, env, binName })

  // --- on exit: detect agent-written changes to the temp file ---
  // Only the temp-file read is swallowed (file may be gone). Persistence
  // errors must propagate: --save-on-exit failing means the user's change was
  // NOT saved, so the change is backed up and run exits non-zero.
  let persistFailed = false
  let afterBytes = null
  let afterReadFailed = false
  try {
    afterBytes = fs.readFileSync(tmp, 'utf8')
  } catch {
    afterBytes = null
    afterReadFailed = true
  }
  if (afterReadFailed) {
    // The temp file is gone/unreadable after exit. Without --save-on-exit the
    // session was ephemeral anyway; with it, the user expected a save we cannot
    // perform — fail loudly instead of returning the child's zero.
    if (saveOnExit) {
      // Rename it out of the owner-pid GC: this process exits next, and the
      // next run's GC would otherwise delete what may be the only copy.
      const kept = tmp.slice(0, -'.json'.length) + KEPT_RUN_SUFFIX
      let keptOk = true
      try { fs.renameSync(tmp, kept) } catch { keptOk = false }
      console.error(keptOk
        ? `error: --save-on-exit could not read the session settings after exit; NOT saved — kept for inspection: ${kept}`
        : `error: --save-on-exit could not read the session settings after exit; NOT saved — copy it out before the next run cleans it up: ${tmp}`)
      persistFailed = true
    }
  } else {
    let after = null
    let parseOk = false
    try { after = JSON.parse(afterBytes); parseOk = true } catch { parseOk = false }

    if (!parseOk) {
      // Unparseable post-exit content. If it differs from what we wrote, the
      // agent changed it into something we can't persist — back it up.
      if (afterBytes !== profileBytes) {
        const backup = backupProfileBytes(name, Buffer.from(afterBytes))
        console.error(`warn: this run session wrote unparseable settings; NOT saved. Backup: ${backup}`)
        if (saveOnExit) persistFailed = true
      }
    } else {
      const cv = validateProfileObject(after)
      const changed = contentHash(after) !== preHash
      if (changed && !cv.ok) {
        // JSON but not an object root (null/array/scalar) — never persist an
        // invalid profile; back the raw bytes up so nothing is silently lost.
        const backup = backupProfileBytes(name, Buffer.from(afterBytes))
        console.error(`warn: this run session wrote invalid settings (${cv.reason}); NOT saved. Backup: ${backup}`)
        if (saveOnExit) persistFailed = true
      } else if (changed) {
        if (saveOnExit) {
          let outcome
          try {
            outcome = await persistRunChanges(name, after, preHash)
          } catch (e) {
            // Loud failure: keep the change recoverable instead of letting the
            // temp-file GC silently destroy it.
            const backup = backupProfileBytes(name, Buffer.from(afterBytes))
            console.error(`error: failed to persist run-session changes: ${e.message}\nbackup of the change: ${backup}`)
            throw e
          }
          if (outcome === 'conflict') persistFailed = true // warned + backed up inside
        } else {
          console.error(`warn: this run session modified its settings; the change is ephemeral and was discarded (use --save-on-exit to persist it into "${name}")`)
        }
      }
    }
  }
  // Cleanup. Never delete a file we failed to read under --save-on-exit: it may
  // still hold the agent's changes (e.g. chmod 000) and be the only copy.
  if (!(afterReadFailed && saveOnExit)) {
    try { fs.rmSync(tmp, { force: true }) } catch {}
  }

  return { output: '', exitCode: code !== 0 ? code : (persistFailed ? 1 : 0) }
}

/**
 * --save-on-exit: route the run's in-session change through the conflict
 * machine against the profile itself. A concurrent DIFFERENT edit is a
 * conflict and is refused (the change is backed up so it isn't lost); a
 * concurrent edit to the SAME content has already persisted the change and is
 * a noop success. The profile read, reconcile and write happen under ONE lock
 * hold. Returns 'saved' | 'noop' | 'conflict'.
 */
async function persistRunChanges(name, after, preHash) {
  let outcome = 'noop'
  await withLock(() => {
    let curBytes = null
    try { curBytes = fs.readFileSync(profilePath(name), 'utf8') } catch {}
    let curHash = null
    if (curBytes != null) { try { curHash = contentHash(JSON.parse(curBytes)) } catch {} }

    const r = reconcile({ liveHash: contentHash(after), profileHash: curHash, baselineHash: preHash })
    if (r.state === 'live-unsaved' || r.state === 'no-baseline') {
      if (curBytes != null) backupProfileBytes(name, curBytes)
      saveProfile(name, after)
      console.error(`saved run-session changes → profile "${name}"`)
      outcome = 'saved'
    } else if (r.state === 'converged' || r.state === 'in-sync') {
      // profile already matches the change — nothing to do.
      outcome = 'noop'
    } else {
      const backup = backupProfileBytes(name, Buffer.from(JSON.stringify(after, null, 2) + '\n'))
      console.error(`warn: "${name}" was edited while this run was active — run changes NOT saved (conflict). Backup: ${backup}`)
      outcome = 'conflict'
    }
  })
  return outcome
}
