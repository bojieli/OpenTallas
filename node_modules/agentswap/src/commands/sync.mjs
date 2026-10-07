import {
  listProfileNames, loadProfileStrict, saveProfile, loadConfig, saveConfig, withLock, caseVariantOf,
} from '../store.mjs'
import { getRemote, listRemotes } from '../remotes.mjs'
import { runRemoteJson } from '../ssh.mjs'
import {
  readSyncState, writeSyncState, syncBaseline, recordSyncBaseline,
  syncReconcile, syncUnitHash, canonicalSyncMeta,
} from '../sync.mjs'

/**
 * push / pull / sync — multi-machine profile sync over SSH.
 *
 * Direction is decided per (profile, remote) by the three-way machine in
 * src/sync.mjs (local hash / remote hash / last-synced baseline). The remote
 * write is compare-and-swap: it carries the hash we last observed, so a remote
 * change between the list and the write surfaces as a conflict instead of a
 * silent clobber. Local bookkeeping (membership, baseline) runs under the
 * local withLock; remote writes run under the remote's own withLock.
 *
 * Deletions do not propagate: a profile missing on one side re-adopts from
 * the other, so `rm` is local-only and a sync re-pulls a surviving remote copy.
 */

const STATUS_LABELS = {
  pushed: 'PUSHED',
  pulled: 'PULLED',
  'in-sync': 'IN-SYNC',
  conflict: 'CONFLICT',
  'name-collision': 'NAME-CASE',
  'local-missing': 'LOCAL-MISSING',
  'remote-missing': 'REMOTE-MISSING',
  'local-unreadable': 'UNREADABLE',
  'remote-unreadable': 'UNREADABLE',
}

/** Statuses that count as success for the exit code. */
const OK_STATUSES = new Set(['pushed', 'pulled', 'in-sync'])

function fail(json, error, detail, hint = null) {
  return {
    output: json
      ? JSON.stringify({ version: 2, error, detail, ...(hint ? { hint } : {}) }, null, 2)
      : `agentswap: ${detail}`,
    exitCode: 1,
  }
}

/** Per-profile meta as synced (rides with the profile file; remote sanitizes). */
function profileMeta(config, name) {
  const m = config.profiles?.[name]
  return m && typeof m === 'object' && !Array.isArray(m) ? m : {}
}

/** Resolve the remote list for a push/pull: explicit args win, else membership. */
function resolveTargets(name, remoteNames, config) {
  const names = remoteNames.length ? remoteNames : (profileMeta(config, name).remotes ?? [])
  if (!names.length) {
    return { error: `profile "${name}" has no remotes — name one explicitly: agentswap push ${name} <remote>` }
  }
  const missing = [...new Set(names)].filter(r => !getRemote(r))
  if (missing.length) return { error: `unknown remote(s): ${missing.join(', ')}` }
  return { targets: [...new Set(names)] }
}

/**
 * Local bookkeeping after a successful remote write: persist the shipped meta
 * (membership included) and record the baseline. Re-checks under the lock that
 * the remote still exists — a `remote rm` landing between the remote write and
 * this commit must not resurrect a dangling membership/baseline.
 * An in-sync adoption calls with meta=null (membership union only).
 */
async function adoptLocally(remoteName, name, hash, meta = null) {
  await withLock(() => {
    const cfg = loadConfig()
    if (!cfg.remotes?.[remoteName]) return
    const existing = profileMeta(cfg, name)
    const shipped = meta ? canonicalSyncMeta(meta) : null
    const remotes = new Set([
      ...(Array.isArray(existing.remotes) ? existing.remotes : []),
      ...(shipped ? shipped.remotes : [remoteName]),
    ])
    cfg.profiles[name] = { ...existing, ...(shipped ?? {}), remotes: [...remotes].sort() }
    saveConfig(cfg)
    const state = readSyncState()
    recordSyncBaseline(state, remoteName, name, hash)
    writeSyncState(state)
  })
}

/**
 * Push one profile to one remote.
 * @param remoteHash hash last observed from this remote's `list`; when omitted
 *   and not forcing, a `list` is fetched first.
 * @param members every remote this invocation targets. The shipped meta
 *   carries all of them in its membership, so one multi-target push writes the
 *   SAME unit everywhere — adopting targets one push at a time would leave each
 *   remote holding a different membership, i.e. a different hash.
 */
async function pushOne(remoteName, name, { force = false, remoteHash = undefined, members = [remoteName] } = {}) {
  const remote = getRemote(remoteName)
  const profile = loadProfileStrict(name)
  if (profile === null) return { name, remote: remoteName, status: 'local-missing' }
  const meta = canonicalSyncMeta(profileMeta(loadConfig(), name))
  meta.remotes = [...new Set([...meta.remotes, ...members])].sort()
  const hash = syncUnitHash(profile, meta)

  if (remoteHash === undefined && !force) {
    const list = await runRemoteJson(remote, 'list')
    remoteHash = list.profiles?.[name] ?? null
  }
  if (!force) {
    const baseline = syncBaseline(readSyncState(), remoteName, name)
    const { state } = syncReconcile({ localHash: hash, remoteHash, baselineHash: baseline })
    if (state === 'in-sync') {
      await adoptLocally(remoteName, name, hash, meta)
      return { name, remote: remoteName, status: 'in-sync' }
    }
    if (state !== 'push') return { name, remote: remoteName, status: 'conflict' }
  }

  const body = { profile, meta }
  if (!force) body.expectedHash = remoteHash ?? null
  try {
    await runRemoteJson(remote, 'write', name, JSON.stringify(body))
  } catch (e) {
    if (e.code === 'EREMOTE' && (e.remoteError === 'conflict' || e.remoteError === 'name-collision')) {
      return { name, remote: remoteName, status: e.remoteError }
    }
    throw e
  }
  await adoptLocally(remoteName, name, hash, meta)
  return { name, remote: remoteName, status: 'pushed' }
}

/**
 * Pull one profile from one remote. The fetch is lock-free; the decide+write
 * is locked. @param snapshot a payload already fetched (the multi-remote
 * agreement pre-check) — reusing it closes the window where the remote could
 * move between the agreement check and the pull.
 */
async function pullOne(remoteName, name, { force = false, snapshot = null } = {}) {
  const remote = getRemote(remoteName)
  let data = snapshot
  if (!data) {
    try {
      data = await runRemoteJson(remote, 'read', name)
    } catch (e) {
      if (e.code === 'EREMOTE' && e.remoteError === 'not-found') {
        return { name, remote: remoteName, status: 'remote-missing' }
      }
      throw e
    }
  }
  const meta = canonicalSyncMeta(data.meta)
  const hash = syncUnitHash(data.profile, meta)

  const status = await withLock(() => {
    const local = loadProfileStrict(name)
    const localHash = local === null ? null : syncUnitHash(local, profileMeta(loadConfig(), name))
    const state = readSyncState()
    const baseline = syncBaseline(state, remoteName, name)
    const { state: decision } = syncReconcile({ localHash, remoteHash: hash, baselineHash: baseline })
    if (decision === 'in-sync') {
      // Always advance the baseline: equal content IS the new common ancestor,
      // even when an old baseline was stale (crash after the remote write, or
      // both sides converged independently).
      recordSyncBaseline(state, remoteName, name, hash)
      writeSyncState(state)
      return 'in-sync'
    }
    if (decision !== 'pull' && !force) return 'conflict'
    // A remote "Work" must not land beside a local "work": one file on
    // macOS/Windows (and an unportable pair everywhere else).
    if (local === null && caseVariantOf(name)) return 'name-collision'
    saveProfile(name, data.profile)
    const cfg = loadConfig()
    cfg.profiles[name] = { notes: '', launchArgs: null, unsetEnv: [], ...meta }
    saveConfig(cfg)
    recordSyncBaseline(state, remoteName, name, hash)
    writeSyncState(state)
    return 'pulled'
  })
  return { name, remote: remoteName, status }
}

function renderResults(kind, results, { json }) {
  const blocked = results.filter(r => !OK_STATUSES.has(r.status))
  if (json) {
    return {
      output: JSON.stringify({ version: 2, kind, results }, null, 2),
      exitCode: blocked.length ? 1 : 0,
    }
  }
  const lines = results.length ? [`${kind}:`] : [`${kind}: nothing to do`]
  for (const r of results) {
    const tag = STATUS_LABELS[r.status] ?? r.status
    const det = r.detail ? ` — ${r.detail}` : ''
    lines.push(`  ${tag.padEnd(12)} ${r.name} → ${r.remote}${det}`)
  }
  if (blocked.length) lines.push('some targets were not synced — see the entries above')
  return { output: lines.join('\n'), exitCode: blocked.length ? 1 : 0 }
}

/** `agentswap push <name> [remote...] [--force]` */
export async function pushProfile(name, remoteNames = [], { json = false, force = false } = {}) {
  if (!name) return fail(json, 'usage', 'usage: agentswap push <name> [remote...] [--force]', 'run `agentswap help push --json` for the full schema')
  let local
  try {
    local = loadProfileStrict(name)
  } catch (e) {
    return fail(json, 'profile-unreadable', e.message)
  }
  if (local === null) return fail(json, 'not-found', `profile not found: ${name}`, 'run `agentswap list` to see profiles')
  const resolved = resolveTargets(name, remoteNames, loadConfig())
  if (resolved.error) return fail(json, 'bad-target', resolved.error, 'run `agentswap remote ls` to see registered remotes')

  const results = []
  for (const remoteName of resolved.targets) {
    results.push(await pushOne(remoteName, name, { force, members: resolved.targets }))
  }
  return renderResults('push', results, { json })
}

/** `agentswap pull <name> [remote...] [--force]` */
export async function pullProfile(name, remoteNames = [], { json = false, force = false } = {}) {
  if (!name) return fail(json, 'usage', 'usage: agentswap pull <name> [remote...] [--force]', 'run `agentswap help pull --json` for the full schema')
  const resolved = resolveTargets(name, remoteNames, loadConfig())
  if (resolved.error) return fail(json, 'bad-target', resolved.error, 'run `agentswap remote ls` to see registered remotes')

  // Multi-remote pull: all targets must agree. Silently adopting A then B would
  // record baselines that a later sync pushes back to A — propagation by
  // accident. The fetched payloads are reused for the actual pulls so the
  // remote cannot move between the agreement check and the write.
  const snapshots = {}
  if (resolved.targets.length > 1) {
    const hashes = {}
    for (const remoteName of resolved.targets) {
      try {
        snapshots[remoteName] = await runRemoteJson(getRemote(remoteName), 'read', name)
      } catch (e) {
        if (e.code === 'EREMOTE' && e.remoteError === 'not-found') {
          return fail(json, 'remote-missing', `profile "${name}" not found on remote "${remoteName}"`, 'run `agentswap remote ls` to see registered remotes')
        }
        throw e
      }
      hashes[remoteName] = syncUnitHash(snapshots[remoteName].profile, snapshots[remoteName].meta)
    }
    if (new Set(Object.values(hashes)).size > 1) {
      const detail = `remotes disagree for "${name}": ${Object.entries(hashes)
        .map(([r, h]) => `${r}=${h.slice(0, 12)}`).join(', ')} — pull from one explicitly`
      return fail(json, 'remotes-disagree', detail, `agentswap pull ${name} <remote>`)
    }
  }

  const results = []
  for (const remoteName of resolved.targets) {
    results.push(await pullOne(remoteName, name, { force, snapshot: snapshots[remoteName] ?? null }))
  }
  return renderResults('pull', results, { json })
}

/** `agentswap sync [remote...] [--force-push] [--force-pull]` */
export async function syncAll(remoteNames = [], { json = false, forcePush = false, forcePull = false } = {}) {
  const entries = remoteNames.length
    ? remoteNames.map(n => [n, getRemote(n)])
    : Object.entries(listRemotes())
  const missing = entries.filter(([, r]) => !r).map(([n]) => n)
  if (missing.length) return fail(json, 'unknown-remote', `unknown remote(s): ${missing.join(', ')}`, 'run `agentswap remote ls` to see registered remotes')
  if (!entries.length) return fail(json, 'no-remotes', 'no remotes configured — add one with: agentswap remote add <name> --host <ssh-host>', 'agentswap remote add <name> --host <ssh-host>')

  // Fetch every remote's list FIRST. A profile present on ≥2 remotes with
  // different hashes is a conflict on ALL of them: sync must not converge the
  // remotes through this machine (pull A then push B is propagation, not sync).
  // The exception is a difference no remote made: when the profile exists here
  // and every copy still equals the baseline this machine recorded for that
  // remote, nothing gets pulled — the copies differ only by this machine's own
  // earlier pushes (e.g. membership grew), and each remote just catches up.
  const remoteLists = {}
  for (const [remoteName, remote] of entries) {
    try {
      remoteLists[remoteName] = await runRemoteJson(remote, 'list')
    } catch (e) {
      return fail(json, 'remote-unreachable', e.message)
    }
  }
  const remoteHashes = new Map() // profile → Map(remote → hash)
  for (const [remoteName] of entries) {
    for (const [name, hash] of Object.entries(remoteLists[remoteName].profiles ?? {})) {
      if (!remoteHashes.has(name)) remoteHashes.set(name, new Map())
      remoteHashes.get(name).set(remoteName, hash)
    }
  }
  const baselines = readSyncState()
  const localNames = new Set(listProfileNames())
  const disagreements = new Set()
  for (const [name, byRemote] of remoteHashes) {
    if (byRemote.size < 2 || new Set(byRemote.values()).size === 1) continue
    const onlyOurPushes = localNames.has(name)
      && [...byRemote].every(([remoteName, hash]) => syncBaseline(baselines, remoteName, name) === hash)
    if (!onlyOurPushes) disagreements.add(name)
  }

  const results = []
  for (const [remoteName] of entries) {
    const remoteList = remoteLists[remoteName]
    const config = loadConfig()
    const state = readSyncState()
    // Scope: local members of this remote ∪ remote-known profiles ∪ baselined profiles.
    const names = new Set([
      ...Object.keys(config.profiles ?? {}).filter(p =>
        Array.isArray(config.profiles[p].remotes) && config.profiles[p].remotes.includes(remoteName)),
      ...Object.keys(remoteList.profiles ?? {}),
      ...Object.keys(state.remotes[remoteName]?.profiles ?? {}),
    ])
    for (const name of [...names].sort()) {
      if (disagreements.has(name)) {
        results.push({ name, remote: remoteName, status: 'conflict', detail: 'remotes disagree' })
        continue
      }
      let localHash
      try {
        const local = loadProfileStrict(name)
        localHash = local === null ? null : syncUnitHash(local, profileMeta(config, name))
      } catch (e) {
        results.push({ name, remote: remoteName, status: 'local-unreadable', detail: e.message })
        continue
      }
      const remoteHash = remoteList.profiles?.[name] ?? null
      const baseline = syncBaseline(state, remoteName, name)
      const { state: decision } = syncReconcile({ localHash, remoteHash, baselineHash: baseline })
      if (decision === 'absent') continue
      if (decision === 'in-sync') {
        // Equal content is the new common ancestor — always advance the baseline.
        if (baseline !== localHash) await adoptLocally(remoteName, name, localHash)
        results.push({ name, remote: remoteName, status: 'in-sync' })
        continue
      }
      if (decision === 'push') {
        results.push(await pushOne(remoteName, name, { force: forcePush, remoteHash }))
        continue
      }
      if (decision === 'pull') {
        results.push(await pullOne(remoteName, name, { force: forcePull }))
        continue
      }
      // conflict — an explicit force direction resolves it.
      if (forcePush) { results.push(await pushOne(remoteName, name, { force: true, remoteHash })); continue }
      if (forcePull) { results.push(await pullOne(remoteName, name, { force: true })); continue }
      results.push({ name, remote: remoteName, status: 'conflict' })
    }
    // Corrupt remote profiles are reported, not swallowed.
    for (const e of remoteList.errors ?? []) {
      results.push({ name: e.name, remote: remoteName, status: 'remote-unreadable', detail: e.detail })
    }
  }
  return renderResults('sync', results, { json })
}
