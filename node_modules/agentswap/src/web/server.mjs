import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { fileURLToPath } from 'node:url'
import {
  listProfileNames, loadProfileStrict, loadConfig, saveConfig,
  saveProfile, readTrustedStateV2, writeStateV2,
  withLock, validateProfileObject, profilePath, caseVariantOf,
} from '../store.mjs'
import { agentSettingsPath, isValidPlatform } from '../paths.mjs'
import { contentHash } from '../settings.mjs'
import { reconcile } from '../reconcile.mjs'
import { readLiveSettings } from '../live.mjs'
import { use } from '../commands/use.mjs'
import { isReserved, isValidProfileName } from '../reserved.mjs'
import { listRemotes, getRemote, addRemote, removeRemote } from '../remotes.mjs'
import { runRemoteJson } from '../ssh.mjs'
import { syncUnitHash, readSyncState, syncBaseline } from '../sync.mjs'
import { listHookPresets, normalize, saveHookPreset, deleteHookPreset } from './hook-store.mjs'
import { listTemplatesSummary, updateTemplateCAS } from '../templates.mjs'
import { createProfileCore } from '../commands/create-profile.mjs'
import { rm } from '../commands/rm.mjs'
import { openUrl } from '../launch.mjs'



const here = path.dirname(fileURLToPath(import.meta.url))
const publicDir = path.join(here, 'public')
const appVersion = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'package.json'), 'utf8')).version

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
}

// The server binds to loopback, but Host/Origin checks still matter: they block
// DNS-rebinding (a public hostname resolving to 127.0.0.1) and cross-origin
// pages from riding the user's browser into the API.
const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '::1'])

function hostIsLoopback(value) {
  if (!value) return false
  try {
    const h = new URL(`http://${value}`).hostname.replace(/^\[|\]$/g, '').toLowerCase()
    return LOOPBACK_HOSTS.has(h)
  } catch {
    return false
  }
}

// Origin is a FULL url (http://127.0.0.1:port) — parse it as such, not as a
// host:port (the browser sends Origin on every same-origin POST/PUT/DELETE).
function originIsLoopback(value) {
  if (!value) return false
  try {
    const h = new URL(value).hostname.replace(/^\[|\]$/g, '').toLowerCase()
    return LOOPBACK_HOSTS.has(h)
  } catch {
    return false
  }
}

function json(res, code, obj) {
  const body = JSON.stringify(obj)
  res.writeHead(code, { 'content-type': 'application/json; charset=utf-8', 'content-length': Buffer.byteLength(body) })
  res.end(body)
}

function readBody(req, limit = 4 * 1024 * 1024) {
  return new Promise((resolve, reject) => {
    let size = 0
    const chunks = []
    req.on('data', (c) => {
      size += c.length
      if (size > limit) { reject(new Error('body too large')); req.destroy(); return }
      chunks.push(c)
    })
    req.on('end', () => {
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')) }
      catch (e) { reject(e) }
    })
    req.on('error', reject)
  })
}

/** Per-profile view for the sidebar (active profile gets a live reconcile status). */
function profileViews() {
  const names = listProfileNames()
  const cfg = loadConfig()
  // Trusted state only: state written for a DIFFERENT CLAUDE_CONFIG_DIR must
  // not mark a profile active here (its baseline describes another live file).
  const state = readTrustedStateV2()
  const active = state?.activeProfile ?? null
  const metas = cfg.profiles || {}

  const lr = readLiveSettings(agentSettingsPath())
  const liveHash = lr.ok ? lr.liveHash : null

  return names.map((name) => {
    const meta = metas[name] || {}
    const view = {
      name,
      notes: meta.notes || '',
      active: name === active,
      hasLaunchArgsOverride: Array.isArray(meta.launchArgs),
      status: null,
      unsaved: null,
    }
    if (name === active) {
      let profileHash = null
      try { profileHash = contentHash(loadProfileStrict(name)) } catch { /* unreadable */ }
      const baseline = state?.appliedHash ?? null
      if (profileHash != null && baseline != null) {
        const r = reconcile({ liveHash, profileHash, baselineHash: baseline })
        view.status = r.state
        view.unsaved = r.state === 'live-unsaved' || r.state === 'conflict'
      } else {
        view.status = 'unknown'
      }
    }
    return view
  })
}

function fullProfile(name) {
  const settings = loadProfileStrict(name)
  if (settings == null) return null
  const meta = loadConfig().profiles?.[name] || {}
  return {
    name,
    notes: meta.notes || '',
    launchArgs: Array.isArray(meta.launchArgs) ? meta.launchArgs : null,
    unsetEnv: Array.isArray(meta.unsetEnv) ? meta.unsetEnv : [],
    settings,
    // Hash of the whole sync unit (settings + meta) at read time — the PUT's
    // expectedHash. Settings alone would let a meta-only edit (notes, sync
    // membership) slip past the CAS.
    hash: syncUnitHash(settings, meta),
  }
}

/** Remotes that hold (or are meant to hold) a copy of this profile: its
 * membership plus any remote with a recorded sync baseline for it. */
function syncedRemotes(name) {
  const members = loadConfig().profiles?.[name]?.remotes
  const sync = readSyncState()
  const baselined = Object.keys(sync.remotes).filter((r) => syncBaseline(sync, r, name) !== null)
  return [...new Set([...(Array.isArray(members) ? members : []), ...baselined])].sort()
}

function setMeta(name, { notes, launchArgs, unsetEnv } = {}) {
  const cfg = loadConfig()
  if (!cfg.profiles || typeof cfg.profiles !== 'object') cfg.profiles = {}
  const cur = cfg.profiles[name] || {}
  cfg.profiles[name] = {
    ...cur, // keys the editor doesn't carry (sync membership) must survive
    notes: notes !== undefined ? String(notes) : (cur.notes || ''),
    launchArgs: launchArgs !== undefined ? launchArgs : (Array.isArray(cur.launchArgs) ? cur.launchArgs : null),
    unsetEnv: unsetEnv !== undefined ? unsetEnv : (Array.isArray(cur.unsetEnv) ? cur.unsetEnv : []),
  }
  saveConfig(cfg)
}

export async function startWeb({ port = 0, open = true } = {}) {
  const { server, url, token } = await createWebServer({ port })
  const urlWithToken = `${url}/#token=${token}`
  console.log(`agentswap web → ${urlWithToken}\n(local only; Ctrl-C to stop)`)
  if (open) openUrl(urlWithToken)

  // Stay alive until SIGINT/SIGTERM (the listener alone would keep the event
  // loop alive, but bin's main() would otherwise resolve and exit the process).
  await new Promise((resolve) => {
    const shutdown = () => {
      server.close(() => resolve())
    }
    process.on('SIGINT', shutdown)
    process.on('SIGTERM', shutdown)
  })

  return {
    output: '',
    exitCode: 0,
    server,
    url,
  }
}

/** Create + listen the server; resolves once bound. Returns the app server,
 * the session token, and the loopback URL. */
export async function createWebServer({ port = 0 } = {}) {
  const token = crypto.randomBytes(16).toString('hex')
  const server = http.createServer(webHandler(token))

  await new Promise((resolve, reject) => {
    server.on('error', reject)
    server.listen(port, '127.0.0.1', resolve)
  })

  const addr = server.address()
  return {
    server,
    token,
    url: `http://127.0.0.1:${addr.port}`,
  }
}

// ---------- model probing ----------
// OpenAI-compatible GET /v1/models, aligned with the provider editor's model_fetch:
// try {base}/v1/models (or {base}/models when the base URL already ends in a
// version segment), then fall back to stripping known Anthropic-compat path
// suffixes (/anthropic, /api/anthropic, /claudecode, …) and retrying the root.
const KNOWN_COMPAT_SUFFIXES = [
  '/api/claudecode', '/api/anthropic', '/apps/anthropic', '/api/coding',
  '/claudecode', '/anthropic', '/step_plan', '/coding', '/claude',
]

function endsWithVersionSegment(url) {
  const last = url.split('/').pop() || ''
  const digits = last.startsWith('v') ? last.slice(1) : ''
  return digits.length > 0 && /^[0-9]+$/.test(digits)
}

function stripCompatSuffix(baseUrl) {
  for (const suffix of KNOWN_COMPAT_SUFFIXES) {
    if (baseUrl.endsWith(suffix)) return baseUrl.slice(0, baseUrl.length - suffix.length)
  }
  return null
}

function buildModelUrlCandidates(baseUrl) {
  const trimmed = baseUrl.trim().replace(/\/+$/, '')
  if (!trimmed) return []
  const candidates = []
  if (endsWithVersionSegment(trimmed)) {
    candidates.push(`${trimmed}/models`)
    if (!trimmed.endsWith('/v1')) candidates.push(`${trimmed}/v1/models`)
  } else {
    candidates.push(`${trimmed}/v1/models`)
  }
  const stripped = stripCompatSuffix(trimmed)
  if (stripped) {
    const root = stripped.replace(/\/+$/, '')
    if (root && root.includes('://')) {
      candidates.push(`${root}/v1/models`)
      candidates.push(`${root}/models`)
    }
  }
  return [...new Set(candidates)]
}

function probeErrorKind(e) {
  if (e.status === 401 || e.status === 403) return 'auth'
  if (e.status === 404 || e.status === 405) return 'not-found'
  const msg = e.message || ''
  if (msg.includes('timeout') || msg.includes('aborted')) return 'timeout'
  if (msg.includes('Failed to parse')) return 'parse'
  return 'other'
}

async function fetchModelList(url, token) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 15000)
  try {
    const res = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'x-api-key': token,
        'accept': 'application/json',
        'user-agent': `agentswap-web/${appVersion}`,
      },
      signal: controller.signal,
    })
    if (!res.ok) {
      const body = await res.text().catch(() => '')
      const err = new Error(`HTTP ${res.status}: ${body.slice(0, 512)}`)
      err.status = res.status
      throw err
    }
    const parsed = await res.json()
    const data = Array.isArray(parsed.data) ? parsed.data : []
    return data.map((m) => ({ id: String(m.id), ownedBy: m.owned_by ?? null }))
  } finally {
    clearTimeout(timer)
  }
}

async function probeModels({ baseUrl, authToken }) {
  const candidates = buildModelUrlCandidates(baseUrl)
  if (candidates.length === 0) throw Object.assign(new Error('Base URL is empty'), { status: 0 })
  let lastErr = null
  for (const url of candidates) {
    try {
      const models = await fetchModelList(url, authToken)
      models.sort((a, b) => a.id.localeCompare(b.id))
      return models
    } catch (e) {
      if (e.status === 404 || e.status === 405) { lastErr = e; continue }
      throw e
    }
  }
  throw lastErr || new Error('no candidates')
}

/** Map a __sync transport/protocol failure onto an HTTP response. The remote's
 * own application errors (conflict, not-found) ride the same envelope as
 * transport failures, so they are split here by remoteError code. */
function remoteErrorResponse(res, e) {
  if (e.code === 'EREMOTE') {
    if (e.remoteError === 'conflict') return json(res, 409, { error: 'remote-conflict', detail: e.message })
    if (e.remoteError === 'not-found') return json(res, 404, { error: 'not-found' })
    return json(res, 502, { error: 'remote-error', kind: e.remoteError, detail: e.message })
  }
  return json(res, 502, { error: 'remote-unreachable', kind: e.code || 'ESSH', detail: e.message })
}

function webHandler(token) {
  return async (req, res) => {
    try {
      const host = (req.headers.host || '').toLowerCase()
      if (!hostIsLoopback(host)) return json(res, 403, { error: 'forbidden-host' })

      const url = new URL(req.url, 'http://localhost')
      const pathname = url.pathname
      const method = req.method

      // ---- API ----
      // Every API call — reads included — requires the per-session capability
      // token. The token is only delivered via the #fragment of the startup
      // URL (fragments never reach the server or its logs), so another local
      // process fetching the page cannot obtain it.
      if (pathname.startsWith('/api/')) {
        if (req.headers['x-agentswap-token'] !== token) {
          return json(res, 403, { error: 'bad-token' })
        }
        const mutating = method !== 'GET' && method !== 'HEAD'
        if (mutating && req.headers.origin && !originIsLoopback(req.headers.origin)) {
          return json(res, 403, { error: 'forbidden-origin' })
        }

        // GET /api/state
        if (method === 'GET' && pathname === '/api/state') {
          return json(res, 200, { version: 2, appVersion, active: readTrustedStateV2()?.activeProfile ?? null, profiles: profileViews() })
        }

        // POST /api/probe-models  {baseUrl, authToken} — fetch the provider's
        // available model list (OpenAI-compatible /v1/models). Read-only: makes
        // an outbound request to the user's own relay, mutates no state.
        if (method === 'POST' && pathname === '/api/probe-models') {
          const body = await readBody(req)
          const baseUrl = String(body.baseUrl || '').trim()
          const authToken = String(body.authToken || '').trim()
          if (!baseUrl) return json(res, 400, { error: 'base-url-required' })
          if (!authToken) return json(res, 400, { error: 'token-required' })
          let parsed
          try { parsed = new URL(baseUrl) } catch { return json(res, 400, { error: 'base-url-invalid' }) }
          if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
            return json(res, 400, { error: 'base-url-invalid' })
          }
          try {
            const models = await probeModels({ baseUrl, authToken })
            return json(res, 200, { models })
          } catch (e) {
            return json(res, 502, { error: 'probe-failed', kind: probeErrorKind(e), detail: e.message })
          }
        }

        // GET /api/profiles/:name
        const profMatch = /^\/api\/profiles\/([^/]+)$/.exec(pathname)
        if (profMatch) {
          const name = decodeURIComponent(profMatch[1])
          if (!isValidProfileName(name)) return json(res, 400, { error: 'name-invalid' })
          if (method === 'GET') {
            // Under the lock so settings + meta are one coherent snapshot —
            // this hash is the CAS token a later PUT presents.
            let p = null
            await withLock(() => { p = fullProfile(name) })
            return p ? json(res, 200, p) : json(res, 404, { error: 'not-found' })
          }
          if (method === 'PUT') {
            const body = await readBody(req)
            let settings = body.settings
            if (typeof settings === 'string') {
              try { settings = JSON.parse(settings) } catch (e) { return json(res, 400, { error: 'invalid-json', detail: e.message }) }
            }
            const v = validateProfileObject(settings)
            if (!v.ok) return json(res, 400, { error: 'invalid-profile', detail: v.reason })
            // Compare-and-swap, mirroring the remote write path: expectedHash
            // (from the GET) makes an edit that raced a CLI/other-tab write a
            // 409 instead of a silent overwrite. Omitting it is the force path.
            let notFound = false, conflict = false, conflictHash = null, newHash = null
            await withLock(() => {
              // re-check under the lock — a concurrent delete must win
              if (!listProfileNames().includes(name)) { notFound = true; return }
              if (typeof body.expectedHash === 'string') {
                let current = null
                try { current = syncUnitHash(loadProfileStrict(name), loadConfig().profiles?.[name] || {}) }
                catch { /* unreadable → treat as changed */ }
                if (current !== body.expectedHash) { conflict = true; conflictHash = current; return }
              }
              saveProfile(name, settings)
              setMeta(name, body)
              newHash = syncUnitHash(settings, loadConfig().profiles?.[name] || {})
            })
            if (notFound) return json(res, 404, { error: 'not-found' })
            if (conflict) return json(res, 409, { error: 'profile-conflict', hash: conflictHash })
            return json(res, 200, { ok: true, hash: newHash })
          }
          if (method === 'DELETE') {
            // The CLI's rm, forced: the web UI confirms before deleting.
            const r = await rm(name, { force: true, json: true })
            if (r.exitCode !== 0) return json(res, 404, { error: 'not-found' })
            return json(res, 200, { ok: true, clearedActive: JSON.parse(r.output).clearedActive })
          }
          return json(res, 405, { error: 'method-not-allowed' })
        }

        // POST /api/profiles/:name/rename  {newName} — moves the profile file,
        // its config metadata, and the active pointer (if any). Content is
        // untouched: a same-filesystem rename(2), no re-serialization.
        const renameMatch = /^\/api\/profiles\/([^/]+)\/rename$/.exec(pathname)
        if (renameMatch) {
          if (method !== 'POST') return json(res, 405, { error: 'method-not-allowed' })
          const name = decodeURIComponent(renameMatch[1])
          if (!isValidProfileName(name)) return json(res, 400, { error: 'name-invalid' })
          const body = await readBody(req)
          const newName = String(body.newName || '').trim()
          if (!newName) return json(res, 400, { error: 'name-required' })
          if (isReserved(newName)) return json(res, 400, { error: 'name-reserved' })
          if (!isValidProfileName(newName)) return json(res, 400, { error: 'name-invalid' })
          let notFound = false, nameExists = false, syncedWith = []
          await withLock(() => {
            if (!listProfileNames().includes(name)) { notFound = true; return }
            // Names stay unique ignoring case: on macOS/Windows "Work" IS
            // work.json, and renaming onto it would replace that profile. Only
            // a case-only rename of this very profile is free.
            if (listProfileNames().includes(newName)) { nameExists = true; return }
            const other = caseVariantOf(newName)
            if (other && other !== name) { nameExists = true; return }
            // A rename cannot propagate (deletions don't): every remote that
            // holds this profile would hand the old name back on the next sync.
            syncedWith = syncedRemotes(name)
            if (syncedWith.length) return
            fs.renameSync(profilePath(name), profilePath(newName))
            const cfg = loadConfig()
            if (cfg.profiles?.[name]) {
              cfg.profiles[newName] = cfg.profiles[name]
              delete cfg.profiles[name]
              saveConfig(cfg)
            }
            const st = readTrustedStateV2()
            if (st?.activeProfile === name) {
              writeStateV2({ activeProfile: newName, appliedHash: st.appliedHash })
            }
          })
          if (notFound) return json(res, 404, { error: 'not-found' })
          if (nameExists) return json(res, 409, { error: 'name-exists' })
          if (syncedWith.length) {
            return json(res, 409, {
              error: 'profile-synced',
              detail: `"${name}" is synced with ${syncedWith.join(', ')}: a rename cannot reach the remote copies, and the next sync would pull "${name}" back`,
            })
          }
          return json(res, 200, { ok: true, name: newName })
        }

        // POST /api/profiles  {name, fromCurrent?, settings?, platform?, notes?}
        if (method === 'POST' && pathname === '/api/profiles') {
          const body = await readBody(req)
          const name = String(body.name || '').trim()
          if (!name) return json(res, 400, { error: 'name-required' })
          if (isReserved(name)) return json(res, 400, { error: 'name-reserved' })
          if (!isValidProfileName(name)) return json(res, 400, { error: 'name-invalid' })

          // Source mutual exclusivity check
          const sources = [
            body.fromCurrent ? 'fromCurrent' : null,
            body.settings !== undefined && body.settings !== null ? 'settings' : null,
            body.platform !== undefined && body.platform !== null ? 'platform' : null,
          ].filter(Boolean)

          if (sources.length > 1) {
            return json(res, 400, { error: 'source-conflict', detail: `cannot combine ${sources.join(' and ')}` })
          }

          if (body.platform !== undefined && body.platform !== null && !isValidPlatform(body.platform)) {
            return json(res, 400, { error: 'invalid-platform', detail: `platform must be one of: darwin, linux, win32` })
          }

          const resCreate = await withLock(() => {
            return createProfileCore(name, {
              fromCurrent: !!body.fromCurrent,
              settings: body.settings ?? null,
              platform: body.platform ?? null,
              notes: body.notes || '',
            })
          })

          if (!resCreate.ok) {
            if (resCreate.error === 'name-exists') return json(res, 409, { error: 'name-exists' })
            return json(res, 400, { error: resCreate.error, detail: resCreate.detail })
          }

          return json(res, 201, { ok: true, name, platform: resCreate.platform })
        }

        // ---- templates API ----
        // GET /api/templates -> { version: 2, platform: <running platform>, templates: [{ platform, settings, hash }] }
        // PUT /api/templates/:platform { settings, expectedHash } -> { version: 2, ok: true, hash }
        if (pathname === '/api/templates') {
          if (method === 'GET') {
            try {
              const summary = listTemplatesSummary()
              return json(res, 200, { version: 2, platform: process.platform, templates: summary })
            } catch (e) {
              return json(res, 500, { version: 2, error: 'templates-unreadable', detail: e.message })
            }
          }
          return json(res, 405, { version: 2, error: 'method-not-allowed' })
        }

        const templateMatch = /^\/api\/templates\/([^/]+)$/.exec(pathname)
        if (templateMatch) {
          if (method !== 'PUT') return json(res, 405, { version: 2, error: 'method-not-allowed' })
          const plat = decodeURIComponent(templateMatch[1])
          if (!isValidPlatform(plat)) {
            return json(res, 400, { version: 2, error: 'invalid-platform', detail: `platform must be one of: darwin, linux, win32` })
          }
          const body = await readBody(req)
          if (!body.settings || typeof body.settings !== 'object') {
            return json(res, 400, { version: 2, error: 'invalid-settings', detail: 'settings object is required' })
          }
          if (typeof body.expectedHash !== 'string' || body.expectedHash.trim() === '') {
            return json(res, 400, { version: 2, error: 'expected-hash-required', detail: 'expectedHash non-empty string is required' })
          }

          try {
            const updated = await withLock(() => {
              return updateTemplateCAS(plat, {
                settings: body.settings,
                expectedHash: body.expectedHash,
              })
            })
            return json(res, 200, { version: 2, ok: true, hash: updated.hash })
          } catch (e) {
            if (e.code === 'ETEMPLATECONFLICT') {
              return json(res, 409, { version: 2, error: 'template-conflict', currentHash: e.currentHash })
            }
            if (e.code === 'EINVALIDPROFILE' || e.code === 'EINVALIDTEMPLATES') {
              return json(res, 400, { version: 2, error: 'invalid-template', detail: e.message })
            }
            return json(res, 500, { version: 2, error: e.code || 'template-error', detail: e.message })
          }
        }


        // POST /api/switch  {name, discard?}
        if (method === 'POST' && pathname === '/api/switch') {
          const body = await readBody(req)
          if (!body.name || !listProfileNames().includes(body.name)) {
            return json(res, 404, { error: 'not-found' })
          }
          const r = await use(body.name, { json: true, discard: !!body.discard, overwriteProfile: !!body.overwriteProfile })
          // use() returns JSON string with {version, error?} on failure
          let parsed
          try { parsed = JSON.parse(r.output) } catch { parsed = null }
          if (r.exitCode !== 0) {
            return json(res, 409, { error: 'switch-blocked', exitCode: r.exitCode, detail: parsed ?? r.output })
          }
          return json(res, 200, { ok: true, ...(parsed || {}) })
        }

        // ---- hook library ----
        // A shelf of hook presets, not profile state: GET lists the bundled
        // ones plus this machine's saved ones, POST adds one, DELETE removes
        // a saved one. `platform` tells the browser which command variant to
        // preselect; it can still insert another machine's.
        if (pathname === '/api/hooks') {
          if (method === 'GET') {
            return json(res, 200, { version: 2, platform: process.platform, presets: listHookPresets() })
          }
          if (method === 'POST') {
            const body = await readBody(req)
            const v = normalize(body)
            if (!v.ok) return json(res, 400, { error: 'invalid-preset', detail: v.reason })
            const saved = await withLock(() => saveHookPreset(v.preset))
            if (!saved.ok) return json(res, 409, { error: 'save-failed', detail: saved.reason })
            return json(res, 201, { ok: true, preset: saved.preset })
          }
          return json(res, 405, { error: 'method-not-allowed' })
        }

        const hookItemMatch = /^\/api\/hooks\/([^/]+)$/.exec(pathname)
        if (hookItemMatch) {
          if (method !== 'DELETE') return json(res, 405, { error: 'method-not-allowed' })
          const id = decodeURIComponent(hookItemMatch[1])
          const r = await withLock(() => deleteHookPreset(id))
          if (!r.ok) {
            if (r.reason === 'builtin') return json(res, 403, { error: 'preset-builtin' })
            return json(res, 404, { error: 'not-found' })
          }
          return json(res, 200, { ok: true })
        }

        // ---- remotes ----
        // The web UI operates registered remotes through the same __sync
        // protocol the CLI uses (SSH transport, whole-file CAS). No new
        // surface on the remote side.

        // /api/remotes — GET lists every registered remote with a live
        // profile listing (probed in parallel; one unreachable remote is
        // reported, not fatal to the others). POST registers a new remote:
        // the same probe-then-lock path as `remote add`, so an unreachable
        // or agentswap-less machine is refused before it enters the registry.
        if (pathname === '/api/remotes') {
          if (method === 'GET') {
            const items = await Promise.all(Object.entries(listRemotes()).map(async ([name, r]) => {
              try {
                const parsed = await runRemoteJson(r, 'list')
                const profiles = Object.entries(parsed.profiles || {})
                  .map(([pname, hash]) => ({ name: pname, hash }))
                  .sort((a, b) => a.name.localeCompare(b.name))
                return { name, host: r.host, bin: r.bin, ok: true, profiles, errors: parsed.errors || [] }
              } catch (e) {
                return { name, host: r.host, bin: r.bin, ok: false, profiles: [], error: e.message, kind: e.code || 'ESSH' }
              }
            }))
            items.sort((a, b) => a.name.localeCompare(b.name))
            return json(res, 200, { version: 2, remotes: items })
          }

          if (method === 'POST') {
            const body = await readBody(req)
            const name = String(body.name || '').trim()
            const host = String(body.host || '').trim()
            const bin = body.bin ? String(body.bin).trim() : undefined
            const r = await addRemote(name, { host, bin, json: true })
            let parsed = null
            try { parsed = JSON.parse(r.output) } catch { /* non-JSON output */ }
            if (r.exitCode !== 0) {
              const err = parsed?.error || 'add-failed'
              if (err === 'exists') return json(res, 409, { error: 'remote-exists', detail: parsed?.detail })
              if (err === 'invalid-remote') return json(res, 400, { error: 'invalid-remote', detail: parsed?.detail })
              return json(res, 502, { error: 'add-failed', kind: err, detail: parsed?.detail })
            }
            return json(res, 201, { ok: true, name: parsed?.added ?? name, remote: parsed?.remote ?? null })
          }

          return json(res, 405, { error: 'method-not-allowed' })
        }

        // DELETE /api/remotes/:name — unregister a remote (same as
        // `remote rm`: strips membership from every profile and drops its
        // sync baselines). Profiles on the remote machine are not deleted.
        const remoteItemMatch = /^\/api\/remotes\/([^/]+)$/.exec(pathname)
        if (remoteItemMatch) {
          if (method !== 'DELETE') return json(res, 405, { error: 'method-not-allowed' })
          const name = decodeURIComponent(remoteItemMatch[1])
          if (!isValidProfileName(name)) return json(res, 400, { error: 'name-invalid' })
          const r = await removeRemote(name, { json: true })
          if (r.exitCode !== 0) {
            let parsed = null
            try { parsed = JSON.parse(r.output) } catch { /* ignore */ }
            if (parsed?.error === 'not-found') return json(res, 404, { error: 'remote-not-found' })
            return json(res, 502, { error: 'remove-failed', detail: parsed?.detail })
          }
          return json(res, 200, { ok: true })
        }

        // GET /api/remotes/:remote/profiles/:name — read one remote profile
        //   (settings + sanitized meta + sync-unit hash).
        // PUT /api/remotes/:remote/profiles/:name — CAS-write it back. The
        //   body carries expectedHash from the GET; a stale hash is a 409.
        //   `force: true` overwrites unconditionally (the protocol's
        //   force path: no expectedHash key at all).
        const remoteProfMatch = /^\/api\/remotes\/([^/]+)\/profiles\/([^/]+)$/.exec(pathname)
        if (remoteProfMatch) {
          const remoteName = decodeURIComponent(remoteProfMatch[1])
          const profName = decodeURIComponent(remoteProfMatch[2])
          if (!isValidProfileName(remoteName) || !isValidProfileName(profName)) {
            return json(res, 400, { error: 'name-invalid' })
          }
          const remote = getRemote(remoteName)
          if (!remote) return json(res, 404, { error: 'remote-not-found' })

          if (method === 'GET') {
            let parsed
            try {
              parsed = await runRemoteJson(remote, 'read', profName)
            } catch (e) {
              return remoteErrorResponse(res, e)
            }
            return json(res, 200, { name: profName, settings: parsed.profile, meta: parsed.meta, hash: parsed.hash })
          }

          if (method === 'PUT') {
            const body = await readBody(req)
            let settings = body.settings
            if (typeof settings === 'string') {
              try { settings = JSON.parse(settings) } catch (e) { return json(res, 400, { error: 'invalid-json', detail: e.message }) }
            }
            const v = validateProfileObject(settings)
            if (!v.ok) return json(res, 400, { error: 'invalid-profile', detail: v.reason })
            // Membership round-trips from the GET: the editor never edits it,
            // and dropping it would silently strip the profile's sync
            // topology on the remote (the write overwrites the whole meta).
            const meta = {
              notes: typeof body.notes === 'string' ? body.notes : '',
              launchArgs: Array.isArray(body.launchArgs) ? body.launchArgs : null,
              unsetEnv: Array.isArray(body.unsetEnv) ? body.unsetEnv : [],
              remotes: Array.isArray(body.remotes) ? body.remotes.filter(isValidProfileName) : [],
            }
            const writeBody = { profile: settings, meta }
            if (body.force === true) {
              // force path: expectedHash key absent entirely
            } else if (Object.prototype.hasOwnProperty.call(body, 'expectedHash')) {
              writeBody.expectedHash = body.expectedHash
            } else {
              return json(res, 400, { error: 'expected-hash-required' })
            }
            let parsed
            try {
              parsed = await runRemoteJson(remote, 'write', profName, JSON.stringify(writeBody))
            } catch (e) {
              return remoteErrorResponse(res, e)
            }
            return json(res, 200, { ok: true, hash: parsed.hash })
          }

          return json(res, 405, { error: 'method-not-allowed' })
        }

        return json(res, 404, { error: 'not-found' })
      }

      // ---- static ----
      if (method !== 'GET' && method !== 'HEAD') return json(res, 405, { error: 'method-not-allowed' })
      let rel = pathname === '/' ? 'index.html' : pathname.slice(1)
      const file = path.normalize(path.join(publicDir, rel))
      if (!file.startsWith(publicDir)) return json(res, 403, { error: 'forbidden' })
      if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
        return json(res, 404, { error: 'not-found' })
      }
      const ext = path.extname(file).toLowerCase()
      const type = MIME[ext] || 'application/octet-stream'
      const bytes = fs.readFileSync(file)
      res.writeHead(200, { 'content-type': type, 'content-length': bytes.length, 'cache-control': 'no-store' })
      res.end(bytes)
    } catch (e) {
      json(res, 500, { error: 'internal', detail: e.message })
    }
  }
}
