import fs from 'node:fs'
import path from 'node:path'
import {
  ensureAcsHome, saveProfile, profileExists, caseVariantOf,
  loadProfileStrict, validateProfileObject,
  loadConfig, saveConfig, withLock,
} from '../store.mjs'
import { deepEqual } from '../settings.mjs'
import { isReserved, isValidProfileName } from '../reserved.mjs'

/**
 * Profile import from a JSON file. The single supported shape is:
 *   { "profiles": [ { "name": "work", "settings": { ... } }, ... ] }
 * Dry-run by default; `--apply` writes. Never overwrites an existing profile
 * (identical → skip; different → conflict). Importing never changes the
 * active profile — run `agentswap use <name>` afterwards to make one active.
 */
export async function importProfiles(file, { apply = false, json = false } = {}) {
  if (!file) return { output: 'usage: agentswap import <file> [--apply]', exitCode: 1 }

  let raw
  try {
    raw = fs.readFileSync(path.resolve(file), 'utf8')
  } catch (e) {
    return fail(json, 'file-unreadable', `cannot read ${file}: ${e.message}`)
  }

  let entries
  try {
    entries = normalize(JSON.parse(raw))
  } catch (e) {
    return fail(json, 'invalid-json', `${file} is not valid JSON: ${e.message}`)
  }
  if (entries == null) {
    return fail(json, 'invalid-shape',
      `${file}: expected { "profiles": [ { "name", "settings" }, ... ] }`)
  }

  // Staging, validation and the commit all run under ONE lock hold, so a
  // concurrent CLI/web mutation can't race the import.
  return await withLock(() => stageAndCommit(entries, { apply, json, file }))
}

function stageAndCommit(entries, { apply, json, file }) {
  // Stage: validate every entry up front.
  const existing = {}
  // Two entries under one name would both stage as new and the second would
  // silently win on apply — refuse both instead of picking one. Names are
  // folded to lower case: on macOS/Windows filesystems "Work" and "work" are
  // one file, and profiles travel between machines.
  const fold = (name) => (typeof name === 'string' ? name.toLowerCase() : null)
  const seen = new Map()
  for (const { name } of entries) seen.set(fold(name), (seen.get(fold(name)) ?? 0) + 1)
  const staged = entries.map(({ name, settings }) => {
    const v = validateProfileObject(settings)
    if (!v.ok) return { name, status: 'error', detail: v.reason, settings: null }
    if (!isValidProfileName(name)) return { name, status: 'invalid-name', detail: 'letters, digits, _ and -; must start with a letter or digit', settings: null }
    if (isReserved(name)) return { name, status: 'reserved', detail: 'reserved command name', settings: null }
    const times = seen.get(fold(name))
    if (times > 1) return { name, status: 'duplicate', detail: `named ${times} times in this file (names are compared ignoring case)`, settings: null }
    // "Work" beside an existing "work" is one file on macOS/Windows.
    const other = caseVariantOf(name)
    if (other) {
      return { name, status: 'conflict', detail: `profile "${other}" already has this name ignoring case (one file on macOS/Windows); refusing to overwrite`, settings }
    }
    if (profileExists(name)) {
      if (!(name in existing)) {
        try { existing[name] = loadProfileStrict(name) } catch { existing[name] = null }
      }
      const cur = existing[name]
      if (cur !== null && deepEqual(cur, settings)) {
        return { name, status: 'skip', detail: 'identical profile already on disk', settings }
      }
      return { name, status: 'conflict', detail: cur === null
        ? 'a profile with this name exists but is unreadable'
        : 'a different profile with this name exists (refusing to overwrite)', settings }
    }
    return { name, status: 'new', detail: null, settings }
  })

  const blocking = staged.some(p => p.status !== 'new' && p.status !== 'skip')
  const counts = { new: 0, skip: 0, conflict: 0, reserved: 0, error: 0, 'invalid-name': 0, duplicate: 0 }
  for (const p of staged) counts[p.status]++

  // Commit (apply + no blocking) BEFORE rendering — the JSON return below must
  // not skip the write.
  let applied = []
  if (apply && !blocking) {
    ensureAcsHome()
    for (const p of staged) {
      if (p.status !== 'new') continue
      saveProfile(p.name, p.settings)
      applied.push(p.name)
    }
    if (applied.length) {
      const config = loadConfig()
      if (!config.profiles || typeof config.profiles !== 'object') config.profiles = {}
      for (const p of staged) {
        if (p.status !== 'new') continue
        config.profiles[p.name] = { notes: '', launchArgs: null, unsetEnv: [] }
      }
      saveConfig(config)
    }
  }

  if (json) {
    return {
      output: JSON.stringify({
        version: 2, dryRun: !apply, blocking,
        profiles: staged.map(p => ({ name: p.name, status: p.status, detail: p.detail })),
        counts, applied,
      }, null, 2),
      exitCode: blocking ? 1 : 0,
    }
  }

  const lines = []
  lines.push(apply ? `import from ${file}:` : `[dry-run] import from ${file}:`)
  for (const p of staged) {
    const tag = p.status.toUpperCase().padEnd(9)
    const det = p.detail ? `  — ${p.detail}` : ''
    lines.push(`  ${tag} ${p.name}${det}`)
  }
  lines.push('')
  if (blocking) {
    lines.push(apply ? 'refusing to apply — resolve the blocking entries above.' : 'refusing to import — resolve the blocking entries above.')
    return { output: lines.join('\n'), exitCode: 1 }
  }
  if (!apply) {
    lines.push(`re-run with --apply to write ${counts.new} new profile(s).`)
    return { output: lines.join('\n'), exitCode: 0 }
  }

  lines.push(`imported ${applied.length} profile(s)${applied.length ? `: ${applied.join(', ')}` : ''}`)
  if (applied.length) lines.push('run `agentswap use <name>` to make one active.')
  return { output: lines.join('\n'), exitCode: 0 }
}

/** Normalize the single supported shape into [{name, settings}]. null = unrecognized. */
function normalize(data) {
  if (data === null || typeof data !== 'object' || Array.isArray(data)) return null
  if (!Array.isArray(data.profiles)) return null
  return data.profiles.map(e => ({
    name: e?.name,
    settings: e?.settings ?? null,
  }))
}

function fail(json, code, human) {
  return { output: json ? JSON.stringify({ version: 2, error: code, detail: human }, null, 2) : human, exitCode: 1 }
}
