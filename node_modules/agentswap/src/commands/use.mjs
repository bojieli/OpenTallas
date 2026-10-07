import fs from 'node:fs'
import {
  loadConfig, profilePath, profileExists, saveProfile,
  readTrustedStateV2, writeStateV2,
  withLock, writeJournal, readJournal, clearJournal, journalPath, journalSourcePath,
  backupSettingsBytes, backupProfileBytes, validateProfileObject, writeAtomic,
} from '../store.mjs'
import { agentSettingsPath, agentConfigDir } from '../paths.mjs'
import { contentHash } from '../settings.mjs'
import { reconcile } from '../reconcile.mjs'
import { launchEnv } from '../launch.mjs'
import { readLiveSettings } from '../live.mjs'

/**
 * Sticky switch to `name`. A profile file IS the complete settings snapshot; a
 * switch is a verbatim whole-file overwrite of the agent's settings.json.
 *
 * Provenance comes from `state.appliedHash`. We reconcile the ACTIVE profile's
 * state (did live drift? was the active profile edited?) before doing anything
 * destructive, then apply the target. Bare `agentswap` and `agentswap use <active>` route
 * through here too, so the entry points can't diverge.
 *
 * Returns { output, exitCode } plus, on success, launch context
 * { active, launchArgs, env } for the caller to spawn the agent.
 */
export async function use(name, opts = {}) {
  const settingsPath = agentSettingsPath()

  // The whole read → reconcile → decide → apply sequence runs under ONE lock
  // hold: a concurrent switch/save/web edit can no longer land between the
  // decision and the write.
  return await withLock(() => decideAndApply(name, opts, settingsPath))
}

async function decideAndApply(name, { json = false, discard = false, overwriteProfile = false } = {}, settingsPath) {
  await recoverJournal(settingsPath)

  // --- load the target profile (verbatim bytes + parsed object) ---
  // Exact name only: "WORK" must not open work.json and become the active name.
  if (!profileExists(name)) return fail(json, 'profile-not-found', `profile not found: ${name}`, 1, { name })
  let targetBytes
  try {
    targetBytes = fs.readFileSync(profilePath(name), 'utf8')
  } catch (e) {
    if (e.code === 'ENOENT') return fail(json, 'profile-not-found', `profile not found: ${name}`, 1, { name })
    throw e
  }
  let target
  try {
    target = JSON.parse(targetBytes)
  } catch (e) {
    return fail(json, 'invalid-profile', `profile "${name}" is not valid JSON: ${e.message}`, 1, { name })
  }
  const v = validateProfileObject(target)
  if (!v.ok) return fail(json, 'invalid-profile', `invalid profile "${name}": ${v.reason}`, 1, { name })
  const targetHash = contentHash(target)

  // --- read live settings.json (bytes for backup, hash for reconcile) ---
  const lr = readLiveSettings(settingsPath)
  if (!lr.ok) {
    return fail(json, 'settings-unreadable',
      `cannot parse ${settingsPath}: ${lr.detail}\nfix or remove it first — agentswap never overwrites a file it cannot read`,
      1, {})
  }
  const { live, liveBytes, liveHash } = lr

  // --- trusted baseline + active-profile hash for the guard ---
  const state = readTrustedStateV2()
  let baselineHash = state?.appliedHash ?? null
  let activeName = state?.activeProfile ?? null
  let activeHash = null
  if (activeName != null && baselineHash != null) {
    if (activeName === name) {
      activeHash = targetHash
    } else {
      const ap = tryReadProfile(activeName)
      if (ap == null) {
        baselineHash = null
        activeName = null
      } else {
        activeHash = contentHash(ap)
      }
    }
  } else {
    baselineHash = null
  }

  const decision = decide({
    name, activeName, targetHash, activeHash, liveHash, baselineHash, discard, overwriteProfile,
  })

  if (decision.action === 'block') {
    if (decision.kind === 'unrecorded') {
      return fail(json, 'unrecorded-settings',
        `current settings not recorded by any profile — they would be overwritten.\n` +
        `  agentswap add <name> --from-current   (record them first)\n` +
        `  agentswap use ${name} --discard        (discard live and switch)`,
        2, { hint: `agentswap add <name> --from-current, or agentswap use ${name} --discard` })
    }
    if (decision.kind === 'conflict') {
      return fail(json, 'conflict',
        `live settings and the active profile "${activeName}" both changed since last apply — refusing to switch.\n` +
        `  agentswap use ${name} --discard           (drop live changes, use target)\n` +
        `  agentswap use ${name} --overwrite-profile (save live into ${activeName} first, then switch)`,
        3, { hint: `agentswap use ${name} --discard | --overwrite-profile`, active: activeName })
    }
    return fail(json, 'unsaved',
      `live settings have unsaved changes not stored in "${activeName}" — switching would lose them.\n` +
      `  agentswap save                            (save them into ${activeName})\n` +
      `  agentswap use ${name} --discard           (discard them and switch)\n` +
      `  agentswap use ${name} --overwrite-profile (save into ${activeName}, then switch)`,
      3, { hint: `agentswap save | agentswap use ${name} --discard | --overwrite-profile`, active: activeName })
  }

  if (decision.action === 'skip') {
    if (decision.kind === 'rebaseline') {
      writeStateV2({ activeProfile: name, appliedHash: targetHash })
    }
    const note = decision.kind === 'unsaved-kept'
      ? ` (live has unsaved changes — run \`agentswap save\` to persist them into ${name})`
      : ''
    return ok(json, { from: name, to: name, backup: null, skipped: true },
      `already on ${name}${note}`, launchCtx(name, target))
  }

  // --- APPLY: verbatim whole-file overwrite, transactional ---
  // (already holding the shared lock — decideAndApply runs under withLock)
  //
  // Edge case: --overwrite-profile on the ACTIVE profile saves live into the
  // profile we are about to apply. Writing the pre-read targetBytes back would
  // resurrect the old profile content and leave both sides diverged — live is
  // already the desired content, so keep it and just re-baseline.
  const liveIsNowTheTarget = decision.saveLiveToActiveFirst && activeName === name
  let backup = null
  if (decision.saveLiveToActiveFirst && activeName) {
    const activeBytes = tryReadProfileBytes(activeName)
    if (activeBytes != null) backupProfileBytes(activeName, activeBytes)
    saveProfile(activeName, live)
  }
  const newHash = liveIsNowTheTarget ? contentHash(live) : targetHash
  if (!liveIsNowTheTarget) {
    if (liveBytes != null) backup = backupSettingsBytes(Buffer.from(liveBytes))
    writeJournal({ from: activeName ?? null, to: name, oldHash: liveHash, newHash })
    fs.mkdirSync(agentConfigDir(), { recursive: true })
    writeAtomic(settingsPath, targetBytes)
  } else {
    writeJournal({ from: activeName ?? null, to: name, oldHash: liveHash, newHash })
  }
  writeStateV2({ activeProfile: name, appliedHash: newHash })
  clearJournal()

  return ok(json, { from: activeName ?? null, to: name, backup: backup ?? null, skipped: false },
    `→ ${name}`, launchCtx(name, liveIsNowTheTarget ? live : target))
}

function decide({ name, activeName, targetHash, activeHash, liveHash, baselineHash, discard, overwriteProfile }) {
  if (baselineHash == null) {
    const r = reconcile({ liveHash, profileHash: targetHash, baselineHash: null })
    if (r.needsChoice && !discard) return { action: 'block', kind: 'unrecorded' }
    return { action: 'apply' }
  }

  const r = reconcile({ liveHash, profileHash: activeHash, baselineHash })
  const isActive = name === activeName

  if (r.state === 'conflict') {
    if (liveHash === null) {
      // Live is missing — there is nothing to keep or save. Re-materialize it
      // from the target instead of blocking on an artificial conflict, and
      // never saveLiveToActiveFirst: that would write null into the profile.
      return { action: 'apply' }
    }
    if (discard) return { action: 'apply' }
    if (overwriteProfile) return { action: 'apply', saveLiveToActiveFirst: true }
    return { action: 'block', kind: 'conflict' }
  }

  if (r.state === 'live-unsaved') {
    if (isActive) {
      // A MISSING live file has nothing worth keeping — re-apply the profile
      // instead of skipping (otherwise the restore commands stay broken).
      if (discard || liveHash === null) return { action: 'apply' }
      return { action: 'skip', kind: 'unsaved-kept' }
    }
    if (discard || liveHash === null) return { action: 'apply' }
    if (overwriteProfile) return { action: 'apply', saveLiveToActiveFirst: true }
    return { action: 'block', kind: 'unsaved' }
  }

  if (r.state === 'profile-edited') return { action: 'apply' }

  if (r.state === 'converged') {
    return isActive ? { action: 'skip', kind: 'rebaseline' } : { action: 'apply' }
  }
  return isActive ? { action: 'skip', kind: 'in-sync' } : { action: 'apply' }
}

async function recoverJournal(settingsPath) {
  if (!readJournal()) return
  await withLock(() => {
    const j = readJournal()
    if (!j) return
    const lr = readLiveSettings(settingsPath)
    if (!lr.ok) {
      // Live is unreadable AND a switch was mid-flight. Clearing the journal
      // here would destroy the only evidence of what happened — fail closed.
      const err = new Error(
        `agentswap: interrupted switch (${j.from ?? '?'} → ${j.to ?? '?'}) and live settings are unreadable: ${lr.detail}\n` +
        `inspect ${settingsPath}, then remove ${journalSourcePath() ?? journalPath()} to proceed`)
      err.code = 'EJOURNAL'
      throw err
    }
    const { liveHash } = lr
    if (liveHash != null && liveHash === j.newHash) {
      // Settings write landed, state commit didn't — finish the commit.
      writeStateV2({ activeProfile: j.to, appliedHash: j.newHash })
      clearJournal()
    } else if (liveHash === j.oldHash) {
      // Write never landed — nothing to finish; reconcile re-derives truth.
      clearJournal()
    } else {
      // Live matches NEITHER side — something else modified settings mid-crash.
      // Keep the journal and fail closed rather than guess.
      const err = new Error(
        `agentswap: interrupted switch (${j.from ?? '?'} → ${j.to ?? '?'}) left live settings in an unknown state.\n` +
        `inspect ${settingsPath}, then remove ${journalSourcePath() ?? journalPath()} to proceed`)
      err.code = 'EJOURNAL'
      throw err
    }
  })
}

/** Resolve per-profile launch context: cleaned launch env + launchArgs. */
function launchCtx(name, target) {
  const cfg = loadConfig()
  const meta = cfg.profiles?.[name] || {}
  const launchArgs = Array.isArray(meta.launchArgs) ? meta.launchArgs : (cfg.defaultLaunchArgs ?? [])
  const unsetEnv = Array.isArray(meta.unsetEnv) ? meta.unsetEnv : []
  const env = launchEnv(target.env, { unsetEnv })
  return { active: name, launchArgs, env }
}

function tryReadProfile(name) {
  if (!profileExists(name)) return null
  try { return JSON.parse(fs.readFileSync(profilePath(name), 'utf8')) } catch { return null }
}
function tryReadProfileBytes(name) {
  if (!profileExists(name)) return null
  try { return fs.readFileSync(profilePath(name), 'utf8') } catch { return null }
}

function ok(json, obj, humanMsg, extra) {
  const output = json ? JSON.stringify({ version: 2, ...obj }, null, 2) : humanMsg
  return { output, exitCode: 0, ...extra }
}
function fail(json, error, humanMsg, code, extra = {}) {
  const output = json ? JSON.stringify({ version: 2, error, ...extra }) : humanMsg
  return { output, exitCode: code }
}
