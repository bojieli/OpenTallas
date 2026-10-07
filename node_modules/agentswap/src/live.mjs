import fs from 'node:fs'
import { contentHash } from './settings.mjs'

/**
 * Read the agent's live settings.json — the single source of truth for the
 * live snapshot every reconcile entry point uses.
 *
 *   - missing/blank file → { ok, live: {}, liveBytes: null, liveHash: null }
 *     (a null hash means "no live state"; a first switch is still allowed)
 *   - a parsed object, INCLUDING {}, gets a real contentHash — so a freshly
 *     applied EMPTY profile reports in-sync instead of a false live-unsaved
 *   - unparseable / non-object → { ok: false, detail } (fail-closed: agentswap
 *     never overwrites a live file it cannot read)
 */
export function readLiveSettings(settingsPath) {
  let bytes = null
  try {
    bytes = fs.readFileSync(settingsPath, 'utf8')
  } catch (e) {
    if (e.code === 'ENOENT') return { ok: true, live: {}, liveBytes: null, liveHash: null }
    return { ok: false, detail: e.message }
  }
  if (bytes.trim() === '') return { ok: true, live: {}, liveBytes: null, liveHash: null }
  let live
  try { live = JSON.parse(bytes) } catch (e) { return { ok: false, detail: e.message } }
  if (live === null || typeof live !== 'object' || Array.isArray(live)) {
    return { ok: false, detail: 'settings.json is not a JSON object' }
  }
  return { ok: true, live, liveBytes: bytes, liveHash: contentHash(live) }
}
