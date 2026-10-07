import {
  deleteProfile, profileExists, loadConfig, saveConfig,
  readTrustedStateV2, writeStateV2, withLock,
} from '../store.mjs'

/**
 * Remove a profile: delete the profile file AND its config.profiles metadata.
 * If it was active, clear active + appliedHash (first-switch protection
 * re-engages on the next switch). The active check runs INSIDE the lock so a
 * concurrent switch can't race the decision.
 */
export async function rm(name, { force = false, json = false } = {}) {
  const result = await withLock(() => {
    // under the lock: a concurrent delete must win (→ not found), not be
    // reported as this call's success
    // exact name: on macOS/Windows "rm WORK" must not delete work.json (and
    // slip past the active-profile guard, which compares exact names)
    if (!profileExists(name)) return { notFound: true }
    const wasActive = readTrustedStateV2()?.activeProfile === name
    if (wasActive && !force) return { refuse: true, wasActive }
    deleteProfile(name)
    const cfg = loadConfig()
    if (cfg.profiles && cfg.profiles[name]) {
      delete cfg.profiles[name]
      saveConfig(cfg)
    }
    if (wasActive) {
      writeStateV2({ activeProfile: null, appliedHash: null })
    }
    return { refuse: false, wasActive }
  })

  if (result.notFound) {
    if (json) return { output: JSON.stringify({ version: 2, error: 'not-found', detail: `profile not found: ${name}` }), exitCode: 1 }
    return { output: `profile not found: ${name}`, exitCode: 1 }
  }
  if (result.refuse) {
    return { output: `cannot remove active profile '${name}' — switch away first or use --force`, exitCode: 1 }
  }
  const { wasActive } = result
  if (json) return { output: JSON.stringify({ version: 2, removed: name, clearedActive: wasActive }), exitCode: 0 }
  return { output: `removed: ${name}${wasActive ? ' (was active — no active profile now)' : ''}`, exitCode: 0 }
}
