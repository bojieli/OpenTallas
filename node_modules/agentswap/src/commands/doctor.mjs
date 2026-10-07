import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import {
  agentSettingsPath, agentCredentialsPath, runDir, backupsDir, configPath,
} from '../paths.mjs'
import {
  readTrustedStateV2, listProfileNames, loadProfileStrict, KEPT_RUN_SUFFIX,
} from '../store.mjs'
import { reconcile } from '../reconcile.mjs'
import { contentHash, isSecretKey } from '../settings.mjs'
import { isReserved } from '../reserved.mjs'
import { readLiveSettings } from '../live.mjs'
import { commandInvocation } from '../launch.mjs'

/**
 * doctor — diagnostics. Every check is ok / warn / fail; exit is nonzero iff
 * any check FAILS (warnings are advisory).
 */

const SYMBOL = { ok: '✓', warn: '⚠', fail: '✗' }

// Auth env keys that sit ABOVE persistent OAuth in precedence. Reported by
// presence only, never value.
const AUTH_ENV_KEYS = ['ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN']

export function doctor({ json = false } = {}) {
  const checks = []
  const push = (name, level, detail) => checks.push({ name, level, detail })

  // 1. settings.json parseable. Absent/blank = fine; corrupt or non-object = fail.
  //    Uses the SAME live reader as use/save/current so the tools can't disagree.
  let liveSettings = {}
  let liveHash = null
  let liveExists = false
  const settingsPath = agentSettingsPath()
  const lr = readLiveSettings(settingsPath)
  if (!lr.ok) {
    push('settings.json', 'fail', `${lr.detail} — fix it before any switch`)
  } else if (lr.liveBytes == null) {
    push('settings.json', 'ok', 'absent or blank (treated as empty — nothing applied yet)')
  } else {
    liveSettings = lr.live
    liveHash = lr.liveHash
    liveExists = true
    push('settings.json', 'ok', 'parsed')
  }
  const liveParseOk = lr.ok

  // 2. UNSAVED — the reconcile state machine.
  const state = readTrustedStateV2()
  const active = state?.activeProfile ?? null
  if (!liveParseOk) {
    push('unsaved', 'fail', 'cannot evaluate: settings.json is unreadable')
  } else if (!active) {
    push('unsaved', state === null ? 'ok' : 'warn', state === null
      ? 'no active profile (nothing to compare)'
      : 'state present but no active profile set')
  } else {
    let profileHash = null
    let profileErr = null
    try {
      const prof = loadProfileStrict(active)
      if (prof === null) profileErr = 'is missing on disk'
      else profileHash = contentHash(prof)
    } catch (e) {
      profileErr = e.message
    }
    if (profileErr) {
      push('unsaved', 'fail', `active profile "${active}" ${profileErr} — state untrusted (unknown)`)
    } else if (!liveExists) {
      push('unsaved', 'warn', `settings.json absent but active is "${active}" — run \`agentswap use ${active}\` to write it`)
    } else {
      const baselineHash = state.appliedHash ?? null
      const r = reconcile({ liveHash, profileHash, baselineHash })
      push('unsaved', ...unsavedResult(r, active))
    }
  }

  // 3. profiles valid: strict load, reserved names, meta orphans.
  const names = listProfileNames()
  const invalid = []
  for (const n of names) {
    try { loadProfileStrict(n) } catch (e) { invalid.push(`${n} (${e.message})`) }
  }
  const reservedNames = names.filter(isReserved)
  const orphans = orphanMeta(names)
  if (invalid.length) {
    push('profiles', 'fail', `invalid profile(s): ${invalid.join('; ')}`)
  } else if (reservedNames.length || orphans.length) {
    const bits = []
    if (reservedNames.length) bits.push(`reserved name(s) unreachable via \`agentswap <name>\`: ${reservedNames.join(', ')}`)
    if (orphans.length) bits.push(`config.profiles metadata with no profile file: ${orphans.join(', ')}`)
    push('profiles', 'warn', `${names.length} profile(s); ${bits.join('; ')}`)
  } else {
    push('profiles', 'ok', `${names.length} profile(s) valid`)
  }

  // 4. AUTH SOURCES — presence/types ONLY, never values.
  const sources = []
  const shadowing = []
  for (const k of AUTH_ENV_KEYS) {
    if (process.env[k]) { sources.push(`process-env:${k}`); shadowing.push(k) }
  }
  const envObj = (liveSettings && typeof liveSettings === 'object' && !Array.isArray(liveSettings)
    && liveSettings.env && typeof liveSettings.env === 'object' && !Array.isArray(liveSettings.env))
    ? liveSettings.env : {}
  for (const k of Object.keys(envObj)) {
    if (AUTH_ENV_KEYS.includes(k) || isSecretKey(k)) sources.push(`settings.env:${k}`)
  }
  let credPresent = false
  try { credPresent = fs.existsSync(agentCredentialsPath()) } catch {}
  if (credPresent) sources.push('credentials.json:present')
  const srcList = sources.length ? sources.join(', ') : 'none detected'
  if (shadowing.length) {
    push('auth sources', 'warn', `${srcList} — inherited env auth (${shadowing.join(', ')}) can shadow OAuth (values not shown)`)
  } else {
    push('auth sources', 'ok', `${srcList} (types/presence only; values not shown)`)
  }

  // 5. agent CLI supports --settings / --setting-sources (run-mode guard).
  push('agent CLI', ...agentFlags())

  // 6. backups/ + run/ leftovers → cleanup hints.
  push('leftovers', ...leftovers())

  const exitCode = checks.some(c => c.level === 'fail') ? 1 : 0
  if (json) {
    return { output: JSON.stringify({ version: 2, checks }, null, 2), exitCode }
  }
  const lines = checks.map(c => `${SYMBOL[c.level]} ${c.name}: ${c.detail}`)
  return { output: lines.join('\n'), exitCode }
}

function unsavedResult(r, active) {
  switch (r.state) {
    case 'in-sync':
      return ['ok', 'in sync (live settings.json matches active profile and baseline)']
    case 'converged':
      return ['ok', 'live and profile agree (baseline stale but consistent)']
    case 'live-unsaved':
      return ['warn', `live settings.json has unsaved changes → run \`agentswap save\` to store them into "${active}"`]
    case 'profile-edited':
      return ['warn', `profile "${active}" was edited since last apply → run \`agentswap use ${active}\` to apply it`]
    case 'conflict':
      return ['fail', `live settings.json and profile "${active}" both changed and differ → run \`agentswap use ${active} --discard\` (keep profile) or \`--overwrite-profile\` (keep live)`]
    case 'no-baseline':
      return r.needsChoice
        ? ['warn', `no trusted baseline for "${active}" (unknown) — run \`agentswap use ${active} --discard\` to establish one`]
        : ['ok', `no baseline yet, but live matches profile "${active}"`]
    default:
      return ['warn', `unknown sync state: ${r.state}`]
  }
}

function orphanMeta(names) {
  let cfg = null
  try { cfg = JSON.parse(fs.readFileSync(configPath(), 'utf8')) } catch { return [] }
  if (!cfg || typeof cfg.profiles !== 'object' || cfg.profiles === null) return []
  const set = new Set(names)
  return Object.keys(cfg.profiles).filter(n => !set.has(n))
}

function agentFlags() {
  // No shell: a shell turns "not found" into ordinary output (`… || true`
  // even into success), which then reads as an agent missing both flags.
  const inv = commandInvocation('claude', ['--help'])
  const r = spawnSync(inv.cmd, inv.args, { encoding: 'utf8', timeout: 5000, windowsVerbatimArguments: inv.verbatim })
  if (r.error?.code === 'ENOENT') return ['warn', 'agent CLI not found in PATH — run mode unavailable here']
  if (r.error) return ['warn', `could not run the agent CLI's --help: ${r.error.message}`]
  const help = `${r.stdout}${r.stderr}`
  const hasSources = /--setting-sources/.test(help)
  const hasSettings = /--settings\b/.test(help)
  if (hasSources && hasSettings) {
    return ['ok', 'supports --settings and --setting-sources (run mode available)']
  }
  const missing = `${hasSources ? '' : '--setting-sources '}${hasSettings ? '' : '--settings'}`.trim()
  return ['fail', `missing flag(s): ${missing} — \`agentswap run\` will fail on this agent version`]
}

function leftovers() {
  const count = (dir, filter = () => true) => {
    try { return fs.readdirSync(dir).filter(filter).length } catch { return 0 }
  }
  const keptN = count(runDir(), f => f.endsWith(KEPT_RUN_SUFFIX))
  const runN = count(runDir(), f => !f.endsWith(KEPT_RUN_SUFFIX))
  const backupN = count(path.join(backupsDir(), 'settings'))
  const bits = []
  if (keptN > 0) bits.push(`${keptN} session file(s) kept after a failed --save-on-exit (run/*${KEPT_RUN_SUFFIX}) — review them before deleting`)
  if (runN > 0) bits.push(`${runN} leftover run/ temp file(s) — safe to delete if no \`agentswap run\` is active`)
  if (bits.length) return ['warn', `${bits.join('; ')}; ${backupN} settings backup(s)`]
  return ['ok', `run/ clean; ${backupN} settings backup(s) retained`]
}
