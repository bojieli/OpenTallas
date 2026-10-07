/**
 * Multi-machine sync: the three-way reconcile over local / remote / baseline
 * hashes, plus the machine-local sync-state store (sync.json).
 *
 * This mirrors src/reconcile.mjs: the baseline is the common ancestor — the
 * hash of the profile content as it was at the last successful sync — which
 * makes "which side moved" decidable. sync.json is provenance like state.json:
 * machine-local, never synced itself, and fail-closed (a missing baseline is a
 * conflict, never a silent overwrite).
 */
import { syncStatePath } from './paths.mjs'
import { readJsonSafe, writeJson, ensureAcsHome } from './store.mjs'
import { contentHash } from './settings.mjs'

/**
 * Pure sync state machine over three content hashes.
 *
 * @param {{ localHash: string|null, remoteHash: string|null, baselineHash: string|null }} hashes
 * @returns {{ state: 'absent'|'in-sync'|'push'|'pull'|'conflict' }}
 *
 * Deletions do not propagate: a profile missing on one side re-adopts from the
 * other (local-only → push, remote-only → pull). Both sides moved, or no
 * common ancestor with divergent content → conflict, resolved only by an
 * explicit --force.
 */
export function syncReconcile({ localHash = null, remoteHash = null, baselineHash = null } = {}) {
  const local = localHash ?? null
  const remote = remoteHash ?? null
  const baseline = baselineHash ?? null

  if (local === null && remote === null) return { state: 'absent' }
  if (local === null) return { state: 'pull' }
  if (remote === null) return { state: 'push' }
  if (local === remote) return { state: 'in-sync' }
  if (baseline === null) return { state: 'conflict' }
  if (local === baseline) return { state: 'pull' }
  if (remote === baseline) return { state: 'push' }
  return { state: 'conflict' }
}

// ---- sync.json (machine-local provenance) ------------------------------------

const emptyState = () => ({ version: 1, remotes: {} })

/** Read sync state; absent / corrupt / wrong version → empty (no baseline = fail-closed). */
export function readSyncState() {
  const s = readJsonSafe(syncStatePath())
  if (!s || typeof s !== 'object' || Array.isArray(s) || s.version !== 1) return emptyState()
  const remotes = s.remotes && typeof s.remotes === 'object' && !Array.isArray(s.remotes) ? s.remotes : {}
  return { version: 1, remotes }
}

export function writeSyncState(state) {
  ensureAcsHome()
  writeJson(syncStatePath(), { version: 1, remotes: state?.remotes ?? {} })
}

/** Baseline hash last synced for (remote, profile), or null. */
export function syncBaseline(state, remote, profile) {
  return state.remotes?.[remote]?.profiles?.[profile]?.hash ?? null
}

/** Record a sync baseline. Mutates `state`; the caller persists under withLock. */
export function recordSyncBaseline(state, remote, profile, hash) {
  if (!state.remotes[remote] || typeof state.remotes[remote] !== 'object') {
    state.remotes[remote] = { profiles: {} }
  }
  state.remotes[remote].profiles[profile] = { hash, ts: new Date().toISOString() }
  return state
}

/** Drop a remote's whole subtree (remote rm). Mutates and returns `state`. */
export function forgetRemote(state, remote) {
  delete state.remotes[remote]
  return state
}

// ---- sync unit hash -----------------------------------------------------------

/**
 * Normalize synced meta for hashing. `remotes` is set semantics (sorted,
 * deduped) so membership order can't perturb the hash; launchArgs is sequence
 * semantics (order kept); non-string elements are dropped on both sides so a
 * hand-edited config can't desynchronize the two hash computations.
 */
export function canonicalSyncMeta(meta) {
  const m = meta && typeof meta === 'object' && !Array.isArray(meta) ? meta : {}
  return {
    notes: typeof m.notes === 'string' ? m.notes : '',
    launchArgs: Array.isArray(m.launchArgs) ? m.launchArgs.filter(x => typeof x === 'string') : null,
    unsetEnv: Array.isArray(m.unsetEnv) ? [...m.unsetEnv.filter(x => typeof x === 'string')].sort() : [],
    remotes: Array.isArray(m.remotes)
      ? [...new Set(m.remotes.filter(x => typeof x === 'string'))].sort()
      : [],
  }
}

/**
 * The sync unit is the profile file PLUS its synced meta — the hash must cover
 * everything a remote write overwrites, or a meta-only change (notes,
 * membership) is invisible to the reconcile and the CAS.
 */
export function syncUnitHash(profile, meta) {
  return contentHash({ p: profile, m: canonicalSyncMeta(meta) })
}
