import crypto from 'node:crypto'
import { readJsonSafe, writeJson } from '../store.mjs'
import { hookLibraryPath } from '../paths.mjs'
import { BUILTIN_HOOKS, HOOK_PLATFORMS } from './hook-library.mjs'

/**
 * The hook library: the bundled presets plus the ones this machine saved.
 *
 * Saved presets live in `AGENTSWAP_HOME/hooks.json` and are deliberately NOT
 * part of a profile — a profile is a settings.json snapshot, and a library is
 * a shelf you pick from. Nothing here is ever applied on its own; the browser
 * inserts a chosen preset into the profile being edited, and from that moment
 * it is ordinary profile content.
 *
 * A corrupt library file reads as empty rather than failing the page: the
 * shelf being unreadable must not stop you editing a profile.
 */

const MAX_PRESETS = 200
const MAX_COMMAND = 8000
const MAX_TEXT = 200
const MAX_DESC = 1000
// A whole preset is capped too: without it, a 4 MiB body could arrive 200
// times over and turn hooks.json into a file the page can no longer load.
const MAX_PRESET_BYTES = 40 * 1024

const isStr = (v) => typeof v === 'string'
const isPlain = (v) => v !== null && typeof v === 'object' && !Array.isArray(v)

/** A display string, or a { en, zh, … } map of them. Every branch is length-capped. */
function localizedText(v, max) {
  if (isStr(v)) return v.length <= max ? v : null
  if (!isPlain(v)) return null
  const keys = Object.keys(v)
  if (!keys.length || keys.length > 8) return null
  const out = {}
  for (const k of keys) {
    if (!/^[a-z]{2}(-[A-Za-z]{2,8})?$/.test(k)) return null
    if (!isStr(v[k]) || v[k].length > max) return null
    out[k] = v[k]
  }
  return out
}

/** Bundled first, then this machine's own. Both shapes are identical to the browser. */
export function listHookPresets() {
  return [
    ...BUILTIN_HOOKS.map((p) => ({ ...p, builtin: true })),
    ...readUserPresets(),
  ]
}

function readUserPresets() {
  const file = readJsonSafe(hookLibraryPath())
  const list = isPlain(file) && Array.isArray(file.presets) ? file.presets : []
  return list.filter((p) => normalize(p).ok).map((p) => ({ ...normalize(p).preset, builtin: false }))
}

/**
 * Validate an incoming preset. Commands are stored verbatim — a hook IS a
 * shell command, so there is nothing to sanitize here; the guard that matters
 * is that only this machine's browser can reach the API at all.
 */
export function normalize(input) {
  if (!isPlain(input)) return { ok: false, reason: 'preset must be an object' }
  const name = localizedText(input.name, MAX_TEXT)
  const named = isStr(name) ? name.trim().length > 0
    : name !== null && Object.values(name).some((v) => v.trim().length > 0)
  if (!named) return { ok: false, reason: 'name is required' }
  if (!isStr(input.event) || !/^[A-Za-z][A-Za-z0-9]{0,63}$/.test(input.event)) {
    return { ok: false, reason: 'event must be an event name' }
  }
  if (!isPlain(input.commands)) return { ok: false, reason: 'commands is required' }

  const commands = {}
  for (const plat of HOOK_PLATFORMS) {
    const c = input.commands[plat]
    if (c === undefined || c === null || c === '') continue
    if (!isStr(c)) return { ok: false, reason: `commands.${plat} must be a string` }
    if (c.length > MAX_COMMAND) return { ok: false, reason: `commands.${plat} is too long` }
    commands[plat] = c
  }
  if (!Object.keys(commands).length) return { ok: false, reason: 'at least one platform command is required' }

  const preset = { id: isStr(input.id) && input.id.length <= MAX_TEXT ? input.id : '', name, event: input.event, commands }
  if (isStr(input.matcher) && input.matcher.length <= MAX_TEXT) preset.matcher = input.matcher
  if (input.description !== undefined) {
    const desc = localizedText(input.description, MAX_DESC)
    if (desc === null) return { ok: false, reason: 'description is too long or malformed' }
    preset.description = desc
  }
  if (Number.isInteger(input.timeout) && input.timeout > 0 && input.timeout <= 86400) preset.timeout = input.timeout
  if (input.shell === 'bash' || input.shell === 'powershell') preset.shell = input.shell
  if (input.async === true) preset.async = true
  if (input.blocking === true) preset.blocking = true
  if (Array.isArray(input.requires)) {
    preset.requires = input.requires.filter((r) => isStr(r) && r.length <= 64).slice(0, 8)
  }
  const size = Buffer.byteLength(JSON.stringify(preset))
  if (size > MAX_PRESET_BYTES) return { ok: false, reason: 'preset is too large' }
  return { ok: true, preset }
}

/** Append one preset. Call inside withLock — this is a read-modify-write. */
export function saveHookPreset(preset) {
  const file = readJsonSafe(hookLibraryPath())
  const list = isPlain(file) && Array.isArray(file.presets) ? file.presets : []
  if (list.length >= MAX_PRESETS) return { ok: false, reason: 'library is full' }
  if (BUILTIN_HOOKS.some((b) => b.id === preset.id)) return { ok: false, reason: 'id is reserved' }
  const id = preset.id && !list.some((p) => p.id === preset.id)
    ? preset.id
    : 'u-' + crypto.randomBytes(6).toString('hex')
  const saved = { ...preset, id }
  writeJson(hookLibraryPath(), { version: 2, presets: [...list, saved] })
  return { ok: true, preset: saved }
}

/** Remove one saved preset by id. Built-ins are not removable. Call inside withLock. */
export function deleteHookPreset(id) {
  if (BUILTIN_HOOKS.some((b) => b.id === id)) return { ok: false, reason: 'builtin' }
  const file = readJsonSafe(hookLibraryPath())
  const list = isPlain(file) && Array.isArray(file.presets) ? file.presets : []
  const next = list.filter((p) => p.id !== id)
  if (next.length === list.length) return { ok: false, reason: 'not-found' }
  writeJson(hookLibraryPath(), { version: 2, presets: next })
  return { ok: true }
}
