import {
  readTrustedStateV2, loadProfileStrict,
} from '../store.mjs'
import { agentSettingsPath } from '../paths.mjs'
import { contentHash } from '../settings.mjs'
import { reconcile } from '../reconcile.mjs'
import { readLiveSettings } from '../live.mjs'

/**
 * Report the active profile and whether live has unsaved changes. When the
 * answer is genuinely undeterminable, reports `status:"unknown"` / `unsaved:null`
 * and a nonzero exit — never a dishonest `unsaved:false`.
 */
export function current({ json = false } = {}) {
  const state = readTrustedStateV2()
  const activeName = state?.activeProfile ?? null

  if (!activeName) {
    return report(json, { active: null, status: 'none', unsaved: null }, 0,
      '(no active profile — switch with `agentswap <name>` or `agentswap use <name>`)')
  }

  let profile
  try {
    profile = loadProfileStrict(activeName)
  } catch {
    return report(json, { active: activeName, status: 'unknown', unsaved: null }, 1,
      `${activeName}  [unknown — profile "${activeName}" is unreadable]`)
  }
  if (profile == null) {
    return report(json, { active: activeName, status: 'unknown', unsaved: null }, 1,
      `${activeName}  [unknown — profile "${activeName}" is missing]`)
  }

  const lr = readLiveSettings(agentSettingsPath())
  if (!lr.ok) {
    return report(json, { active: activeName, status: 'unknown', unsaved: null }, 1,
      `${activeName}  [unknown — settings.json is unparseable]`)
  }

  const baselineHash = state?.appliedHash ?? null
  if (baselineHash == null) {
    return report(json, { active: activeName, status: 'unknown', unsaved: null }, 1,
      `${activeName}  [unknown — no baseline; run \`agentswap use ${activeName}\`]`)
  }

  const r = reconcile({ liveHash: lr.liveHash, profileHash: contentHash(profile), baselineHash })
  const { status, unsaved } = mapState(r.state)
  const tag = status === 'in-sync' ? '' : `  [${status}${unsaved ? ' — run \`agentswap save\`' : ''}]`
  return report(json, { active: activeName, status, unsaved }, 0, `${activeName}${tag}`)
}

function mapState(state) {
  switch (state) {
    case 'live-unsaved': return { status: 'live-unsaved', unsaved: true }
    case 'profile-edited': return { status: 'profile-edited', unsaved: false }
    case 'conflict': return { status: 'conflict', unsaved: true }
    case 'converged': return { status: 'in-sync', unsaved: false }
    default: return { status: 'in-sync', unsaved: false }
  }
}

function report(json, obj, exitCode, humanMsg) {
  return { output: json ? JSON.stringify({ version: 2, ...obj }, null, 2) : humanMsg, exitCode }
}
