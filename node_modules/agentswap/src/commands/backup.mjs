import fs from 'node:fs'
import path from 'node:path'
import {
  withLock, backupSettingsBytes, backupProfileBytes, profilePath, writeAtomic, validateProfileObject,
} from '../store.mjs'
import { backupsDir, agentSettingsPath, agentConfigDir } from '../paths.mjs'
import { isValidProfileName } from '../reserved.mjs'

/** Enumerate the split backup pools (newest first), read-only. */
export function backupList({ json = false } = {}) {
  const settingsDir = path.join(backupsDir(), 'settings')
  const profilesRoot = path.join(backupsDir(), 'profiles')
  const settings = safeList(settingsDir).map(f => path.join(settingsDir, f))
  const profiles = {}
  for (const name of safeSubdirs(profilesRoot)) {
    const dir = path.join(profilesRoot, name)
    profiles[name] = safeList(dir).map(f => path.join(dir, f))
  }
  if (json) return JSON.stringify({ version: 2, settings, profiles }, null, 2)
  const lines = []
  lines.push(`settings backups (${settings.length}):`)
  for (const p of settings) lines.push(`  ${p}`)
  for (const [name, ps] of Object.entries(profiles)) {
    lines.push(`profile "${name}" backups (${ps.length}):`)
    for (const p of ps) lines.push(`  ${p}`)
  }
  if (!settings.length && !Object.keys(profiles).length) lines.push('(no backups yet)')
  return lines.join('\n')
}

/**
 * Restore a backup file to its target, inferred from the backup pool path:
 *   backups/settings/…        → the agent's settings.json
 *   backups/profiles/<name>/… → profiles/<name>.json
 * The source must live strictly inside THIS agentswap home's backups pool (realpath
 * containment — a path that merely contains "/backups/settings/" is not
 * enough), and the current target is itself backed up first, so restore is
 * reversible.
 *
 * Without `yes` it is a dry run: every check above still runs, and the
 * result names the target without writing it.
 */
export async function restore(file, { yes = false, json = false } = {}) {
  const abs = path.resolve(file)
  let real
  try { real = fs.realpathSync(abs) } catch (e) {
    return fail(json, 'backup-unreadable', `cannot read backup: ${abs} (${e.message})`)
  }
  let bytes
  try { bytes = fs.readFileSync(real, 'utf8') } catch (e) {
    return fail(json, 'backup-unreadable', `cannot read backup: ${real} (${e.message})`)
  }
  let parsed
  try { parsed = JSON.parse(bytes) } catch (e) {
    return fail(json, 'backup-invalid', `backup is not valid JSON: ${e.message}`)
  }
  // The backup pools also hold run-session quarantine copies, which may be
  // unparseable-as-profile garbage (arrays, null). Syntax alone is not enough:
  // restoring one would install an invalid settings root.
  const v = validateProfileObject(parsed)
  if (!v.ok) {
    return fail(json, 'backup-invalid', `backup is not a valid settings object: ${v.reason}`)
  }

  let root
  try { root = fs.realpathSync(backupsDir()) } catch { root = path.resolve(backupsDir()) }
  const rel = path.relative(root, real)
  if (rel.startsWith('..') || path.isAbsolute(rel)) {
    return fail(json, 'restore-outside', `refusing to restore: ${real} is outside the backups pool ${root}`)
  }
  const seg = rel.split(path.sep)
  let target, kind, profileName = null
  if (seg[0] === 'settings' && seg.length >= 2) {
    target = agentSettingsPath(); kind = 'settings'
  } else if (seg[0] === 'profiles' && seg.length >= 3) {
    profileName = seg[1]
    if (!isValidProfileName(profileName)) {
      return fail(json, 'restore-target', `cannot determine profile name from backup path: ${JSON.stringify(profileName)}`)
    }
    target = profilePath(profileName); kind = 'profile'
  } else {
    return fail(json, 'restore-target',
      `cannot determine restore target from path — pass a file under backups/settings/ or backups/profiles/<name>/`)
  }

  if (!yes) {
    if (json) {
      return { output: JSON.stringify({ version: 2, dryRun: true, restored: null, target, from: abs, kind }), exitCode: 0 }
    }
    return {
      output: `[dry-run] would restore ${kind} ← ${abs}\n  → ${target}\nre-run with --yes to write it (the current ${kind} is backed up first)`,
      exitCode: 0,
    }
  }

  await withLock(() => {
    let curBytes = null
    try { curBytes = fs.readFileSync(target, 'utf8') } catch {}
    if (curBytes != null) {
      if (kind === 'settings') backupSettingsBytes(Buffer.from(curBytes))
      else backupProfileBytes(profileName, Buffer.from(curBytes))
    }
    if (kind === 'settings') fs.mkdirSync(agentConfigDir(), { recursive: true })
    writeAtomic(target, bytes)
  })

  if (json) return { output: JSON.stringify({ version: 2, dryRun: false, restored: target, from: abs, kind }), exitCode: 0 }
  return { output: `restored ${kind} ← ${abs}\n  → ${target}\n(run \`agentswap current\` to review; state was not changed)`, exitCode: 0 }
}

function safeList(dir) {
  try { return fs.readdirSync(dir).filter(f => f.endsWith('.json')).sort().reverse() } catch { return [] }
}
function safeSubdirs(dir) {
  try {
    return fs.readdirSync(dir, { withFileTypes: true }).filter(e => e.isDirectory()).map(e => e.name).sort()
  } catch { return [] }
}
function fail(json, error, msg) {
  return { output: json ? JSON.stringify({ version: 2, error, detail: msg }) : msg, exitCode: 1 }
}
