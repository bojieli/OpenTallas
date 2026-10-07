/**
 * Pure env projection over a settings.json object.
 *
 * The daily editor is an arbitrary env key→string table. JSON stays canonical:
 * this module only reads/writes `settings.env` string entries. Non-env keys
 * (including top-level `model`), unknown fields, and non-string env values are
 * left untouched. Deleting a key is not the same as setting it to "".
 */

export const PLATFORMS = ['darwin', 'linux', 'win32']

export const PLATFORM_LABEL = {
  darwin: 'macOS',
  linux: 'Linux',
  win32: 'Windows',
}

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v)
}

function cloneJson(v) {
  return JSON.parse(JSON.stringify(v))
}

/** Own-key write that plain assignment would swallow (__proto__) or shadow. */
function defineOwn(obj, key, value) {
  Object.defineProperty(obj, key, { value, writable: true, enumerable: true, configurable: true })
}

function hasOwn(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj, key)
}

/**
 * Project `settings.env` into editable rows.
 * @returns {{ kind: 'ok'|'missing'|'locked', rows: Array, reason?: string }}
 */
export function projectEnv(settings) {
  if (!isPlainObject(settings)) {
    return { kind: 'locked', rows: [], reason: 'settings-not-object' }
  }
  if (!hasOwn(settings, 'env')) {
    return { kind: 'missing', rows: [] }
  }
  const env = settings.env
  if (!isPlainObject(env)) {
    return { kind: 'locked', rows: [], reason: 'env-not-object' }
  }
  const rows = []
  for (const key of Object.keys(env)) {
    const value = env[key]
    if (typeof value === 'string') {
      rows.push({ key, value, locked: false })
    } else {
      rows.push({
        key,
        value,
        locked: true,
        reason: value === null ? 'null' : Array.isArray(value) ? 'array' : typeof value,
      })
    }
  }
  return { kind: 'ok', rows }
}

/**
 * Apply a complete string-row table onto a settings object.
 * Locked (non-string) env entries are preserved verbatim and cannot be
 * overwritten or deleted here — use the advanced JSON editor for those.
 *
 * Key order: walk the original `env` keys and keep locked entries in place;
 * string keys present in `entries` stay at their original index; string keys
 * omitted from `entries` are deleted; brand-new keys append in entries order.
 * A no-op edit therefore does not reshuffle keys.
 *
 * @param {object} settings
 * @param {{ entries: Array<{key: string, value: string}> }} edit
 * @returns {{ ok: true, settings: object } | { ok: false, reason: string, key?: string }}
 */
export function applyEnvEdit(settings, { entries }) {
  if (!isPlainObject(settings)) {
    return { ok: false, reason: 'settings-not-object' }
  }
  if (!Array.isArray(entries)) {
    return { ok: false, reason: 'entries-not-array' }
  }

  const hadEnv = hasOwn(settings, 'env')
  if (hadEnv && !isPlainObject(settings.env)) {
    return { ok: false, reason: 'env-locked' }
  }

  const next = cloneJson(settings)
  // Null-proto + defineOwn: a plain `{}` / `obj[k]=` swallows `__proto__`
  // (and can rebind the prototype for a non-string value). Same rule as
  // settings.mjs canonicalize and the web hooks/plugins collectors.
  const locked = Object.create(null)
  const origKeys = hadEnv ? Object.keys(settings.env) : []
  if (hadEnv) {
    for (const k of origKeys) {
      const v = settings.env[k]
      if (typeof v !== 'string') defineOwn(locked, k, cloneJson(v))
    }
  }

  const wanted = Object.create(null)
  const entryOrder = []
  for (const row of entries) {
    if (!row || typeof row !== 'object') {
      return { ok: false, reason: 'entry-not-object' }
    }
    const key = row.key
    if (typeof key !== 'string' || key === '') {
      return { ok: false, reason: 'key-invalid' }
    }
    if (hasOwn(locked, key)) {
      return { ok: false, reason: 'locked-key', key }
    }
    if (hasOwn(wanted, key)) return { ok: false, reason: 'duplicate-key', key }
    if (typeof row.value !== 'string') {
      return { ok: false, reason: 'value-not-string', key }
    }
    defineOwn(wanted, key, row.value)
    entryOrder.push(key)
  }

  const env = Object.create(null)
  const placed = new Set()
  for (const k of origKeys) {
    if (hasOwn(locked, k)) {
      defineOwn(env, k, locked[k])
      placed.add(k)
      continue
    }
    // Original string key: keep only if the table still lists it.
    if (hasOwn(wanted, k)) {
      defineOwn(env, k, wanted[k])
      placed.add(k)
    }
  }
  for (const k of entryOrder) {
    if (placed.has(k)) continue
    defineOwn(env, k, wanted[k])
  }

  if (!hadEnv && Object.keys(env).length === 0) {
    // Absence is a value: don't invent `env` when nothing was there and
    // the table is still empty.
    return { ok: true, settings: next }
  }

  next.env = env
  return { ok: true, settings: next }
}

/** Space-split launchArgs text — only used after the user edits the field. */
export function parseLaunchArgsText(text) {
  const t = String(text ?? '').trim()
  return t ? t.split(/\s+/) : null
}

/** Comma-split unsetEnv text — only used after the user edits the field. */
export function parseUnsetEnvText(text) {
  const t = String(text ?? '').trim()
  return t ? t.split(',').map((s) => s.trim()).filter(Boolean) : []
}

/**
 * Resolve launch metadata for a save. Unedited fields keep the loaded values
 * (so a space inside an original launchArgs entry is not re-split by an
 * env-only save). Edited fields are collected with the text parsers above.
 *
 * @param {{ notes: string, launchArgs: string[]|null, unsetEnv: string[] }} orig
 * @param {{ notes?: boolean, launchArgs?: boolean, unsetEnv?: boolean }} dirty
 * @param {{ notes: string, launchArgsText: string, unsetEnvText: string }} fields
 */
export function resolveMeta(orig, dirty, fields) {
  return {
    notes: dirty.notes ? String(fields.notes ?? '') : orig.notes,
    launchArgs: dirty.launchArgs
      ? parseLaunchArgsText(fields.launchArgsText)
      : (Array.isArray(orig.launchArgs) ? orig.launchArgs.slice() : orig.launchArgs),
    unsetEnv: dirty.unsetEnv
      ? parseUnsetEnvText(fields.unsetEnvText)
      : (Array.isArray(orig.unsetEnv) ? orig.unsetEnv.slice() : []),
  }
}
