import fs from 'node:fs'
import {
  saveProfile, profilePath,
  readTrustedStateV2, writeStateV2,
  withLock, backupProfileBytes, loadProfileStrict,
} from '../store.mjs'
import { agentSettingsPath } from '../paths.mjs'
import { contentHash, deepEqual } from '../settings.mjs'
import { reconcile } from '../reconcile.mjs'
import { readLiveSettings } from '../live.mjs'

/**
 * `agentswap save`: store the current live settings verbatim back into the ACTIVE
 * profile, so a change the agent wrote (e.g. a model switch) or a hand edit
 * isn't silently lost on the next switch.
 *
 * Only safe when the reconciled state is `live-unsaved`. A double-change
 * `conflict` is refused unless `--overwrite-profile`.
 *
 * The read → reconcile → backup → write sequence runs under ONE lock hold, so
 * a concurrent profile edit can't land between the decision and the write.
 */
export async function save({ json = false, overwriteProfile = false } = {}) {
  return await withLock(() => doSave({ json, overwriteProfile }))
}

async function doSave({ json, overwriteProfile }) {
  const state = readTrustedStateV2()
  const activeName = state?.activeProfile ?? null
  if (!activeName) {
    return fail(json, 'no-active', 'no active profile — switch with `agentswap <name>` first', 1)
  }

  let active
  try {
    active = loadProfileStrict(activeName)
  } catch (e) {
    return fail(json, 'active-missing', `active profile "${activeName}" is unreadable: ${e.message}`, 1, { active: activeName })
  }
  if (active == null) {
    return fail(json, 'active-missing', `active profile "${activeName}" is missing — state is unknown`, 1, { active: activeName })
  }

  const lr = readLiveSettings(agentSettingsPath())
  if (!lr.ok) {
    return fail(json, 'settings-unreadable', `cannot parse ${agentSettingsPath()}: ${lr.detail}`, 1)
  }
  const { live, liveHash } = lr

  if (liveHash === null) {
    // Live file is absent/blank. There is nothing to save, and claiming
    // in-sync would disagree with `current` (which reports live-unsaved for a
    // missing file). Re-applying the profile is the honest restore path.
    return fail(json, 'live-missing',
      `live settings file is absent or blank — nothing to save.\n  agentswap use ${activeName}   (re-apply the profile to disk)`,
      1, { active: activeName })
  }

  if (deepEqual(live, active)) {
    writeStateV2({ activeProfile: activeName, appliedHash: contentHash(active) })
    return ok(json, { saved: null, skipped: true, backup: null }, `already in sync — nothing to save (${activeName})`)
  }

  const baselineHash = state?.appliedHash ?? null
  const r = reconcile({ liveHash, profileHash: contentHash(active), baselineHash })

  const persist = () => {
    const activeBytes = tryReadProfileBytes(activeName)
    const backup = activeBytes != null ? backupProfileBytes(activeName, activeBytes) : null
    saveProfile(activeName, live)
    writeStateV2({ activeProfile: activeName, appliedHash: contentHash(live) })
    return backup
  }

  switch (r.state) {
    case 'live-unsaved': {
      const backup = persist()
      return ok(json, { saved: activeName, skipped: false, backup }, `saved live settings → ${activeName}`)
    }
    case 'conflict': {
      if (!overwriteProfile) {
        return fail(json, 'conflict',
          `live settings and profile "${activeName}" both changed since last apply — refusing to overwrite the profile.\n` +
          `  agentswap save --overwrite-profile   (force live → ${activeName})\n` +
          `  agentswap use ${activeName} --discard  (drop live, keep the profile edits)`,
          3, { active: activeName })
      }
      const backup = persist()
      return ok(json, { saved: activeName, skipped: false, backup }, `saved live settings → ${activeName} (overwrote profile edits)`)
    }
    case 'profile-edited':
      return ok(json, { saved: null, skipped: true, reason: 'profile-edited', backup: null },
        `nothing to save — "${activeName}" was edited but live is unchanged; run \`agentswap use ${activeName}\` to apply it`)
    default: {
      if (!overwriteProfile) {
        return fail(json, 'unknown-baseline',
          `no trusted baseline for "${activeName}" and live differs from it — cannot tell which side changed.\n` +
          `  agentswap save --overwrite-profile   (force live → ${activeName})\n` +
          `  agentswap use ${activeName} --discard  (reset live to the profile)`,
          3, { active: activeName })
      }
      const backup = persist()
      return ok(json, { saved: activeName, skipped: false, backup }, `saved live settings → ${activeName}`)
    }
  }
}

function tryReadProfileBytes(name) {
  try { return fs.readFileSync(profilePath(name), 'utf8') } catch { return null }
}

function ok(json, obj, humanMsg) {
  return { output: json ? JSON.stringify({ version: 2, ...obj }, null, 2) : humanMsg, exitCode: 0 }
}
function fail(json, error, humanMsg, code, extra = {}) {
  return { output: json ? JSON.stringify({ version: 2, error, ...extra }, null, 2) : humanMsg, exitCode: code }
}
