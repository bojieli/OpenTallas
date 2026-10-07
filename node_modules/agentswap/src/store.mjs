import fs from 'node:fs'
import path from 'node:path'
import crypto, { createHash } from 'node:crypto'
import { AsyncLocalStorage } from 'node:async_hooks'
import {
  appHome, profilesDir, runDir, backupsDir,
  configPath, statePath, agentSettingsPath, agentConfigDir, EPERM_ATTEMPTS,
} from './paths.mjs'
import { isValidProfileName } from './reserved.mjs'



const DEFAULT_CONFIG = {
  version: 2,
  defaultLaunchArgs: ['--dangerously-skip-permissions'],
  backupsKeep: 20,
  // Per-profile metadata (NOT settings — the profile file is the settings
  // snapshot). Keyed by profile name: { notes, launchArgs, unsetEnv, remotes }.
  // `remotes` is the multi-remote sync membership (see docs/sync.md).
  profiles: {},
  // Remote sync targets: { name: { host, bin } }. Machine-local — never synced.
  remotes: {},
}

function ensureDir(dir, mode = 0o700) {
  fs.mkdirSync(dir, { recursive: true, mode })
}

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'))
  } catch (e) {
    if (e.code === 'ENOENT') return fallback
    throw e
  }
}

/** Never throws: absent OR corrupt → null. Used by fail-closed state readers. */
export function readJsonSafe(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'))
  } catch {
    return null
  }
}

/** Synchronous sleep (win32 EPERM retry backoff — AV file locks are transient). */
function sleepSync(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)
}

/** Atomic rename with win32 EPERM retry. Cleans up tmp on failure. */
function renameAtomic(tmp, file, beforeRename = null) {
  const attempts = EPERM_ATTEMPTS
  for (let i = 0; ; i++) {
    try {
      if (beforeRename) beforeRename()
      fs.renameSync(tmp, file)
      return
    } catch (e) {
      if (e.code === 'EPERM' && i < attempts - 1) {
        sleepSync(50 * (i + 1))
        continue
      }
      try { fs.rmSync(tmp, { force: true }) } catch {}
      throw e
    }
  }
}

/**
 * The file a write to `file` must replace. A rename onto a symlink replaces
 * the LINK, so a settings.json linked into a dotfiles repo would silently
 * turn into a detached regular file; write the file it points at instead
 * (for a dangling link, the path it names).
 */
function writeTarget(file) {
  let st
  try { st = fs.lstatSync(file) } catch { return file }
  if (!st.isSymbolicLink()) return file
  try { return fs.realpathSync(file) } catch {}
  return path.resolve(path.dirname(file), fs.readlinkSync(file))
}

/** Atomic file write (string|Buffer): pid-suffixed tmp + rename, win32 EPERM retry. */
export function writeAtomic(file, data, mode = 0o600) {
  const target = writeTarget(file)
  const tmp = `${target}.${process.pid}.tmp`
  fs.writeFileSync(tmp, data, { mode })
  // Fence at the COMMIT point, not before the tmp write: the lock could be
  // displaced while the tmp bytes land or during a win32 EPERM retry (up to
  // ~300ms of sleeps), and the rename must not go through in that case.
  renameAtomic(tmp, target, assertLockHeld)
}

/**
 * Write-time fencing. Every critical state write (config, state, profiles,
 * journal, live settings) goes through writeAtomic, which — when running
 * inside a withLock transaction — verifies the lock still names our token
 * BEFORE the write commits. A displaced holder (its lock moved by a thief in
 * the irreducible userspace window) thus stops writing at the next write
 * boundary: it cannot overwrite the new holder's writes after the new holder
 * reports success. The check→rename gap is a few microseconds; the
 * journal/reconcile pass converges anything torn. Writes outside a lock
 * context (bootstrap) are unchecked — there is nothing to displace.
 */
function assertLockHeld() {
  const token = lockStore.getStore()
  if (!token) return
  let holder
  try {
    holder = readLockHolder(lockPath())
  } catch {
    holder = null // unparseable — not ours → displaced
  }
  if (!holder || holder.pid !== process.pid || holder.token !== token) {
    const err = new Error('agentswap: the config lock was displaced during this operation; re-run the command')
    err.code = 'ELOCKDISPLACED'
    throw err
  }
}

export function writeJson(file, obj, mode = 0o600) {
  writeAtomic(file, JSON.stringify(obj, null, 2) + '\n', mode)
}

export function ensureAcsHome() {
  ensureDir(appHome())
  ensureDir(profilesDir())
  ensureDir(runDir())
  ensureDir(backupsDir())
}

export function loadConfig() {
  ensureAcsHome()
  const cfg = readJson(configPath(), null)
  // Missing config: return the in-memory default WITHOUT persisting it.
  // Persisting here is an unlocked write that could overwrite a config a
  // concurrent locked transaction just saved; the first real persist happens
  // under withLock via saveConfig. The nested values are FRESH copies: a
  // shallow spread would share DEFAULT_CONFIG.profiles / defaultLaunchArgs,
  // so a caller mutating the returned object would ghost its metadata into
  // every later load that misses the file.
  if (!cfg) return {
    ...DEFAULT_CONFIG,
    profiles: {},
    remotes: {},
    defaultLaunchArgs: [...DEFAULT_CONFIG.defaultLaunchArgs],
  }
  return {
    ...DEFAULT_CONFIG,
    ...cfg,
    profiles: cfg.profiles ?? {},
    remotes: cfg.remotes ?? {},
    defaultLaunchArgs: cfg.defaultLaunchArgs ?? [...DEFAULT_CONFIG.defaultLaunchArgs],
  }
}

export function saveConfig(cfg) {
  ensureAcsHome()
  writeJson(configPath(), cfg)
}

export function listProfileNames() {
  ensureAcsHome()
  try {
    return fs.readdirSync(profilesDir())
      .filter(f => f.endsWith('.json'))
      .map(f => f.slice(0, -5))
      .sort()
  } catch (e) {
    if (e.code === 'ENOENT') return []
    throw e
  }
}

/** Chokepoint for name → path: every profile file access goes through here. */
function assertValidProfileName(name) {
  if (!isValidProfileName(name)) {
    const err = new Error(`invalid profile name: ${JSON.stringify(name)} (letters, digits, _ and -; must start with a letter or digit)`)
    err.code = 'EBADPROFILENAME'
    throw err
  }
}

export function profilePath(name) {
  assertValidProfileName(name)
  return path.join(profilesDir(), `${name}.json`)
}

/**
 * Is `name` an existing profile, spelled exactly? Never "whatever file the
 * filesystem would open": where it ignores case (default macOS and Windows),
 * opening WORK.json reads work.json, and the caller would then act on — and
 * record — the wrong name.
 */
export function profileExists(name) {
  assertValidProfileName(name)
  return listProfileNames().includes(name)
}

/**
 * The existing profile spelled differently from `name` but equal to it
 * ignoring case, or null. On macOS/Windows the two are ONE file, and profiles
 * travel between machines, so a NEW name must stay unique ignoring case on
 * every platform (an existing exact name always resolves to itself).
 */
export function caseVariantOf(name) {
  const lower = name.toLowerCase()
  return listProfileNames().find(n => n !== name && n.toLowerCase() === lower) ?? null
}

export function saveProfile(name, profile) {
  ensureAcsHome()
  // Last line of defense for every writer (pull, import, remote write…):
  // creating "Work" beside "work" would overwrite it on macOS/Windows.
  if (!listProfileNames().includes(name)) {
    const other = caseVariantOf(name)
    if (other) {
      const err = new Error(`profile name "${name}" collides with existing "${other}" (names are case-insensitive on macOS/Windows)`)
      err.code = 'ENAMECASE'
      throw err
    }
  }
  writeJson(profilePath(name), profile)
}

/**
 * Register per-profile metadata in config.profiles so list/rm stay in sync.
 */
export function registerProfileMeta(name, { notes = '', launchArgs = null, unsetEnv = [] } = {}) {
  const cfg = loadConfig()
  if (!cfg.profiles || typeof cfg.profiles !== 'object') cfg.profiles = {}
  if (!cfg.profiles[name]) {
    cfg.profiles[name] = { notes, launchArgs, unsetEnv }
    saveConfig(cfg)
  }
}




export function deleteProfile(name) {
  assertLockHeld()
  fs.rmSync(profilePath(name), { force: true })
}

/**
 * Strict profile load: null when absent; throws on corrupt JSON (EPROFILEPARSE)
 * or a non-object root (EINVALIDPROFILE); otherwise the plain settings object.
 */
export function loadProfileStrict(name) {
  if (!profileExists(name)) return null // exact names only (see profileExists)
  let raw
  try {
    raw = JSON.parse(fs.readFileSync(profilePath(name), 'utf8'))
  } catch (e) {
    if (e.code === 'ENOENT') return null
    if (e.code === 'EBADPROFILENAME') throw e
    const err = new Error(`agentswap: profile "${name}" is not valid JSON: ${e.message}`)
    err.code = 'EPROFILEPARSE'
    throw err
  }
  const v = validateProfileObject(raw)
  if (!v.ok) {
    const err = new Error(`agentswap: invalid profile "${name}": ${v.reason}`)
    err.code = 'EINVALIDPROFILE'
    throw err
  }
  return raw
}

/** A profile must be a plain JSON object. */
export function validateProfileObject(obj) {
  if (obj === null) return { ok: false, reason: 'profile is null (expected a JSON object)' }
  if (Array.isArray(obj)) return { ok: false, reason: 'profile is an array (expected a JSON object)' }
  if (typeof obj !== 'object') return { ok: false, reason: `profile is a ${typeof obj} (expected a JSON object)` }
  return { ok: true }
}

// ---- state (provenance) ------------------------------------------------------

/**
 * Short fingerprint of the resolved settings path. Binds state to a single
 * CLAUDE_CONFIG_DIR so two config dirs sharing one AGENTSWAP_HOME can't cross-wire
 * the single `active`/appliedHash.
 */
export function configDirFingerprint() {
  return createHash('sha256').update(agentSettingsPath()).digest('hex').slice(0, 12)
}

/** Read state, or null when absent / unparseable / not version 2 (fail-closed). */
export function readStateV2() {
  const s = readJsonSafe(statePath())
  if (!s || typeof s !== 'object' || Array.isArray(s) || s.version !== 2) return null
  return s
}

/**
 * Read state bound to THIS agent config dir. State carries a fingerprint of the
 * settings path it was written for; a mismatch OR ABSENCE (e.g. state written
 * by an older version, CLAUDE_CONFIG_DIR switched, or a hand-edited file) means
 * the active profile / baseline cannot be trusted for THIS live file, so every
 * entry point uses this — never readStateV2() directly for decisions.
 */
export function readTrustedStateV2() {
  const s = readStateV2()
  if (!s) return null
  if (s.configDirFingerprint !== configDirFingerprint()) return null
  return s
}

/** Write state, stamping version:2 and (unless supplied) the config-dir fingerprint. */
export function writeStateV2(state = {}) {
  ensureAcsHome()
  const out = {
    version: 2,
    activeProfile: state.activeProfile ?? null,
    appliedHash: state.appliedHash ?? null,
    configDirFingerprint: state.configDirFingerprint ?? configDirFingerprint(),
  }
  writeJson(statePath(), out)
  return out
}

// ---- cross-process lock ------------------------------------------------------
//
// The lock file holds `<pid>:<token>`. The token makes stale-lock stealing safe:
// a thief re-reads the file and only removes it when the owner is STILL the same
// dead pid+token it first saw, so it can't remove a fresh lock another process
// just created. The file is created via link(2) from a fully-written tmp file,
// so contenders never observe a half-written/empty lock.
//
// Reentrancy is tracked per ASYNC CONTEXT (AsyncLocalStorage), not with a
// module-level counter: two CONCURRENT same-process transactions (e.g. two web
// requests) must contend, while a withLock nested inside the holding context
// (use → recoverJournal) shares the hold.

const lockStore = new AsyncLocalStorage()

/**
 * Tokens held by LIVE withLock contexts in THIS process. A lock naming our
 * own pid is only reclaimable when its token is NOT in this set: then it is
 * an orphan (a release that failed, or a pid-reused predecessor) — never a
 * live peer context. Without this, a swallowed release failure on Windows
 * leaves an own-pid lock this process can never steal (own pid is always
 * alive), so a long-running web server would fail every write with ELOCKED.
 *
 * The token is published synchronously at acquisition (inside acquireLock,
 * before its async boundary yields): a same-tick contender must already see
 * it as live, or it would misread the fresh lock as an orphan and steal it.
 */
const liveTokens = new Set()

function isPidAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false
  try {
    process.kill(pid, 0)
    return true
  } catch (e) {
    return e.code === 'EPERM'
  }
}
export { isPidAlive }

/**
 * Parse the lock file. Returns { pid, token } for a valid `pid:token` lock,
 * or null when the file is absent. THROWS ELOCKFORMAT for a present-but-
 * unparseable lock: a contender must NOT steal what it can't parse — a lock
 * written by a different agentswap generation is left for its owner, not
 * corrupt-stolen. Callers that only need "is it ours?" catch it and treat it
 * as displaced; acquireLock lets it propagate (fail-closed).
 */
function readLockHolder(file) {
  let content
  try {
    content = fs.readFileSync(file, 'utf8').trim()
  } catch (e) {
    if (e.code === 'ENOENT') return null
    throw e
  }
  const m = /^(\d+):([0-9a-f]+)$/.exec(content)
  if (!m) {
    const err = new Error(`agentswap: the lock file is in an unknown format and was left untouched: ${file}`)
    err.code = 'ELOCKFORMAT'
    throw err
  }
  const pid = parseInt(m[1], 10)
  if (!Number.isInteger(pid) || pid <= 0) {
    const err = new Error(`agentswap: the lock file is in an unknown format and was left untouched: ${file}`)
    err.code = 'ELOCKFORMAT'
    throw err
  }
  return { pid, token: m[2] }
}

const lockPath = () => path.join(appHome(), 'lock')

function lockTmpName(file) {
  return `${file}.${process.pid}.${crypto.randomBytes(6).toString('hex')}.tmp`
}

/**
 * Atomically create the lock file via link(2) from a fully-written tmp.
 * Returns true on success, false on EEXIST. Contenders never observe an
 * empty or half-written lock (the path appears complete or not at all).
 */
function createLockAtomic(file, token) {
  const tmp = lockTmpName(file)
  try {
    fs.writeFileSync(tmp, `${process.pid}:${token}`, { mode: 0o600 })
    try {
      fs.linkSync(tmp, file)
      return true
    } catch (e) {
      if (e.code !== 'EEXIST') throw e
      return false
    }
  } finally {
    try { fs.rmSync(tmp, { force: true }) } catch {}
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Decide whether a thief may proceed with the rename-claim, given the holder
 * it first read and a fresh re-read immediately before the rename. The
 * re-read shrinks the ABA window: if a live owner cycled the lock between the
 * two reads, the thief backs off instead of moving a live lock.
 *
 * Own-pid locks need a token-liveness predicate: another context in THIS
 * process may legitimately hold the lock (a concurrent web request), while
 * an own-pid lock whose token no live context holds is an orphan a failed
 * release left behind. The default is conservative (assume live → never
 * steal); acquireLock passes the real liveTokens membership.
 *
 * Residual limitation (inherent to zero-dep userspace locks): between this
 * re-read and the rename — two adjacent sync syscalls — another PROCESS can
 * still acquire. The post-rename verify + link-restore (restoreClaimedLock)
 * then bound the damage: the thief never runs its critical section on a
 * displaced lock, and a third contender's lock is never clobbered. The worst
 * case is the displaced holder running unprotected for a few microseconds;
 * withLock's fencing check then fails THAT transaction (ELOCKDISPLACED) so
 * the caller re-runs, and the next reconcile/journal pass converges. An
 * OS-level lock (flock/LockFileEx) would close this fully but is not in
 * Node's stdlib.
 */
/**
 * Does a claimed grave still match the stale lock we read — same pid and
 * token? If a live owner cycled the lock between our re-read and the rename,
 * the grave names a different owner and must be restored, not deleted.
 */
export function claimMatchesHolder(claimed, first) {
  return claimed !== null && first !== null
    && claimed.pid === first.pid && claimed.token === first.token
}

export function stealClaimStillValid(first, fresh, isTokenLive = () => true) {
  const unchanged = first === null
    ? fresh === null
    : fresh !== null && fresh.pid === first.pid && fresh.token === first.token
  if (!unchanged) return false
  if (fresh === null) return true // still absent
  if (fresh.pid === process.pid) return !isTokenLive(fresh.token) // own-pid orphan?
  return !isPidAlive(fresh.pid) // still dead
}

/**
 * Write `content` at the (empty) lock path atomically — the restore fallback
 * when link(2) persistently fails. Never clobbers an existing lock (a
 * contender's). Returns true on write, false if the path was already taken.
 */
export function writeLockIfAbsent(file, content) {
  // Write the bytes fully to a tmp first, then link(2) into place. An
  // O_EXCL create-then-write leaves an EMPTY lock observable for the write
  // duration: a contender that reads it as corrupt steals it and writes its
  // own bytes over ours. link is atomic — the path appears complete or not
  // at all, so no empty lock is ever observable.
  const tmp = `${file}.write.${process.pid}.${crypto.randomBytes(6).toString('hex')}`
  try {
    fs.writeFileSync(tmp, content, { mode: 0o600 })
    fs.linkSync(tmp, file)
    return true
  } catch (e) {
    if (e.code === 'EEXIST') return false
    throw e
  } finally {
    try { fs.rmSync(tmp, { force: true }) } catch {}
  }
}

/**
 * Put back a claimed lock we must not keep (verification showed a live owner
 * cycled under us). Uses link(2), NOT rename: rename would silently REPLACE a
 * fresh lock a third contender created at the now-empty path in the meantime,
 * leaving two live owners convinced they hold the lock. link fails EEXIST
 * instead — the worst outcome is then an orphaned grave, never two owners.
 * Returns true if restored, false if the path was taken by someone else.
 *
 * Transient win32 EPERM (AV scans) is retried: leaving the path empty lets a
 * contender acquire while the displaced owner still runs. On persistent
 * failure the displaced owner's OWN lock content is written back at the path
 * (writeLockIfAbsent — never clobber a contender): contenders then wait out
 * the owner's pid instead of entering while it runs, and the owner's fencing
 * check sees its own token and finishes legitimately. If a contender already
 * holds the path, the write reports EEXIST: the grave is stale evidence and
 * is cleared, and we return false. On any other failure (the same dir
 * permissions that blocked the link) the grave stays as evidence and the
 * error surfaces — the path is NOT claimed protected.
 */
export function restoreClaimedLock(file, grave) {
  const attempts = EPERM_ATTEMPTS
  for (let i = 0; ; i++) {
    try {
      fs.linkSync(grave, file)
      try { fs.rmSync(grave, { force: true }) } catch {}
      return true
    } catch (e) {
      if (e.code === 'EEXIST') {
        // A contender legitimately holds the path — the grave is stale evidence.
        try { fs.rmSync(grave, { force: true }) } catch {}
        return false
      }
      if (e.code === 'EPERM' && i < attempts - 1) {
        sleepSync(50 * (i + 1))
        continue
      }
      let content
      try { content = fs.readFileSync(grave, 'utf8') } catch { throw e }
      if (writeLockIfAbsent(file, content)) {
        try { fs.rmSync(grave, { force: true }) } catch {}
        return true
      }
      // A contender legitimately holds the path — the grave is stale evidence.
      try { fs.rmSync(grave, { force: true }) } catch {}
      return false
    }
  }
}

async function acquireLock(file, { timeoutMs = 10_000, pollMs = 50 } = {}) {
  const deadline = Date.now() + timeoutMs
  const token = crypto.randomBytes(8).toString('hex')
  for (;;) {
    if (createLockAtomic(file, token)) {
      // Publish the token synchronously, BEFORE this async function yields:
      // a same-tick contender (Promise.all of N withLock calls) must already
      // see the token as live — adding it in the caller after
      // `await acquireLock()` would let every contender misread the fresh
      // lock as an own-pid orphan and steal it out from under the holder.
      liveTokens.add(token)
      return token
    }
    // Propagates ELOCKFORMAT: a lock we can't parse is left for its owner,
    // never corrupt-stolen (a different agentswap generation's lock).
    const holder = readLockHolder(file)
    const stale = holder === null
      || (holder.pid !== process.pid && !isPidAlive(holder.pid))
      || (holder.pid === process.pid && !liveTokens.has(holder.token))
    if (stale) {
      // Stale (absent-after-race, owned by a dead pid, or an own-pid orphan a
      // failed release left). Claim it ATOMICALLY via rename: only one thief
      // can win the claim, and the lock path itself is never unconditionally
      // removed — so a thief can't delete a live lock another contender just
      // created (the old read-then-rm window).
      const grave = `${file}.dead.${process.pid}.${crypto.randomBytes(6).toString('hex')}`
      // Re-read immediately before the rename (see stealClaimStillValid for
      // the residual window this does not close). A lock that became
      // unparseable under us changed owner — back off.
      let fresh
      try { fresh = readLockHolder(file) } catch { continue }
      if (!stealClaimStillValid(holder, fresh, (t) => liveTokens.has(t))) continue
      try {
        fs.renameSync(file, grave)
      } catch (e) {
        if (e.code !== 'ENOENT') throw e
        continue // someone else cycled it first — re-read
      }
      if (holder !== null) {
        // Verify the claimed file still names the dead owner we read. If not,
        // a live owner cycled the lock under us — restore it and back off.
        let claimed
        try { claimed = readLockHolder(grave) } catch { claimed = null }
        if (!claimMatchesHolder(claimed, holder)) {
          restoreClaimedLock(file, grave)
          continue
        }
      }
      try { fs.rmSync(grave, { force: true }) } catch {}
      continue // stale file exclusively removed; next iteration creates our lock
    }
    if (Date.now() >= deadline) {
      const err = new Error(`agentswap: config is locked by pid ${holder?.pid ?? 'unknown'} (${file})`)
      err.code = 'ELOCKED'
      throw err
    }
    // Async poll: a holder in ANOTHER async context of this process must be
    // able to progress on the event loop — a synchronous sleep here would
    // deadlock it until the timeout.
    await sleep(pollMs)
  }
}

export async function releaseLock(file, token) {
  let holder
  try {
    holder = readLockHolder(file)
  } catch {
    return // unparseable — not ours; leave it for its owner
  }
  if (!holder || holder.pid !== process.pid || holder.token !== token) return
  // Claim the path atomically with a rename, not a path-based rm: between the
  // read above and the removal (on win32 the EPERM retry loop sleeps up to
  // ~300ms) a thief can displace our lock and a contender can take the path —
  // a plain rm would then delete the CONTENDER's lock. The rename captures
  // whatever is at the path in a unique grave; the content check then proves
  // it is still ours before deleting it, and anything else is restored.
  const grave = `${file}.released.${process.pid}.${crypto.randomBytes(6).toString('hex')}`
  const attempts = EPERM_ATTEMPTS
  for (let i = 0; ; i++) {
    try {
      fs.renameSync(file, grave)
      break
    } catch (e) {
      if (e.code === 'ENOENT') return // already gone
      if (e.code === 'EPERM' && i < attempts - 1) {
        // Transient win32 EPERM (AV scans hold the file for milliseconds).
        await sleep(50 * (i + 1))
        continue
      }
      // Persistent failure: leave the lock in place. It names our pid, so a
      // contender waits us out; when this process exits the dead-pid lock is
      // stolen by the next contender.
      return
    }
  }
  const claimed = readLockHolder(grave)
  if (claimed && claimed.pid === process.pid && claimed.token === token) {
    try { fs.rmSync(grave, { force: true }) } catch {}
  } else {
    // Not ours — a live owner cycled the path under us. Put it back.
    restoreClaimedLock(file, grave)
  }
}

/**
 * Run `fn` while holding the single cross-process lock. All mutating commands
 * share it. `fn` may be sync or async; the lock is always released in `finally`.
 * Reentrancy is per async context: a withLock nested in the holding context
 * (use → recoverJournal) shares the hold; a concurrent same-process context
 * (another web request) contends like any other process.
 *
 * Fencing: after `fn` returns, the lock is re-read. If it no longer names our
 * token, it was displaced during the transaction (the irreducible userspace
 * window — see stealClaimStillValid): the transaction may have raced a peer,
 * so we fail it with ELOCKDISPLACED instead of reporting success. The caller
 * re-runs; journal recovery / reconcile converge the state.
 */
export async function withLock(fn, opts = {}) {
  ensureAcsHome()
  const file = lockPath()
  if (lockStore.getStore()) return await fn()
  // acquireLock publishes the token to liveTokens synchronously (see there).
  const token = await acquireLock(file, opts)
  try {
    // The ALS carries the token (not just a flag) so writeAtomic's write-time
    // fencing can verify the lock still names us before each write commits.
    const result = await lockStore.run(token, fn)
    let holder
    try { holder = readLockHolder(file) } catch { holder = null }
    if (!holder || holder.pid !== process.pid || holder.token !== token) {
      const err = new Error('agentswap: the config lock was displaced during this operation; re-run the command')
      err.code = 'ELOCKDISPLACED'
      throw err
    }
    return result
  } finally {
    await releaseLock(file, token)
    liveTokens.delete(token)
  }
}

// ---- transition journal ------------------------------------------------------
//
// The journal is PER CONFIG DIR (fingerprint-suffixed): a crash mid-switch in
// one CLAUDE_CONFIG_DIR must not block or mis-recover commands in another.
// The fingerprint binds the journal to the config dir it describes, so a
// journal from a different dir can never be auto-consumed here.

const journalPath = () => path.join(appHome(), `journal-${configDirFingerprint()}.json`)

export { journalPath }

/** Record an in-flight switch so a half-completed transition can be recovered. */
export function writeJournal({ from = null, to = null, oldHash = null, newHash = null } = {}) {
  ensureAcsHome()
  writeJson(journalPath(), {
    from, to, oldHash, newHash,
    pid: process.pid,
    ts: new Date().toISOString(),
  })
}

/**
 * The journal file a read would consume: the fingerprinted one for THIS
 * config dir, or null when absent. Recovery, error messages and cleanup touch
 * only this file.
 */
export function journalSourcePath() {
  try { if (fs.existsSync(journalPath())) return journalPath() } catch {}
  return null
}

export function readJournal() {
  const src = journalSourcePath()
  return src ? readJsonSafe(src) : null
}

export function clearJournal() {
  assertLockHeld()
  const src = journalSourcePath()
  if (src) { try { fs.rmSync(src, { force: true }) } catch {} }
}

// ---- split backups -------------------------------------------------------------

function backupNonce() {
  return crypto.randomBytes(6).toString('hex')
}

function backupStamp() {
  return new Date().toISOString().replace(/[:.]/g, '-')
}

const settingsBackupsDir = () => path.join(backupsDir(), 'settings')
const profileBackupsDir = (name) => {
  assertValidProfileName(name)
  return path.join(backupsDir(), 'profiles', name)
}

function writeBackup(dir, filename, bytes) {
  ensureDir(dir, 0o700)
  const dest = path.join(dir, filename)
  fs.writeFileSync(dest, bytes, { mode: 0o600 })
  return dest
}

function pruneDir(dir, keep) {
  try {
    const files = fs.readdirSync(dir).filter(f => f.endsWith('.json')).sort()
    while (files.length > keep) fs.rmSync(path.join(dir, files.shift()), { force: true })
  } catch {}
}

/** Back up already-read settings bytes into their own pool (0600), pruned to `keep`. */
export function backupSettingsBytes(bytes, { keep } = {}) {
  const k = keep ?? loadConfig().backupsKeep ?? 20
  const dir = settingsBackupsDir()
  const dest = writeBackup(dir, `settings-${backupStamp()}-${process.pid}-${backupNonce()}.json`, bytes)
  pruneDir(dir, k)
  return dest
}

/** Back up a profile's already-read bytes into its own per-name pool (0600). */
export function backupProfileBytes(name, bytes, { keep } = {}) {
  const k = keep ?? loadConfig().backupsKeep ?? 20
  const dir = profileBackupsDir(name)
  const dest = writeBackup(dir, `${backupStamp()}-${process.pid}-${backupNonce()}.json`, bytes)
  pruneDir(dir, k)
  return dest
}

// ---- run/ temp GC ---------------------------------------------------------------

/**
 * Suffix of a run/ session file kept for the user (--save-on-exit could not
 * read it back). Its owner has exited, so owner-pid GC must skip it: it may
 * be the only copy of that session's change.
 */
export const KEPT_RUN_SUFFIX = '.kept.json'

/** GC stale run/ temp files by OWNER-PID liveness (long sessions outlive age thresholds). */
export function gcRunFilesByOwner() {
  let files
  try { files = fs.readdirSync(runDir()) } catch { return }
  for (const f of files) {
    if (f.endsWith(KEPT_RUN_SUFFIX)) continue
    const m = /-(\d+)-[0-9a-f]+\.json$/.exec(f)
    if (!m) continue
    const pid = parseInt(m[1], 10)
    if (!isPidAlive(pid)) {
      try { fs.rmSync(path.join(runDir(), f), { force: true }) } catch {}
    }
  }
}

export { agentSettingsPath, agentConfigDir }
