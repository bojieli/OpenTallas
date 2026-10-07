/**
 * Pure write-back rules for the Advanced row editors: string lists
 * (permissions.allow, …), enabledPlugins and extraKnownMarketplaces. The DOM
 * gathers plain rows; these decide the value, so the rules are testable.
 *
 * Shared contract, given the hydration snapshot { had, raw, hyd } (did the
 * file have the key, its raw value, what the rows showed right after load):
 *   - rows still showing exactly `hyd` → the original `raw` verbatim, or the
 *     key's original absence;
 *   - otherwise the rows as edited — a cell still showing its hydrated text
 *     keeps it exactly, an edited cell is trimmed, and a row left empty is not
 *     a value;
 *   - every row removed → an empty list / map when the file had the key,
 *     absent otherwise.
 *
 * Returns { value } or { absent: true }.
 */

/** Own-key write that plain assignment would swallow (__proto__). */
function defineOwn(obj, key, value) {
  Object.defineProperty(obj, key, { value, writable: true, enumerable: true, configurable: true })
}

const same = (shown, hyd) => JSON.stringify(shown) === JSON.stringify(hyd)
const original = ({ had, raw }) => (had ? { value: raw } : { absent: true })
/** Every row removed: the file's key stays, emptied — restoring `raw` would undo the deletion. */
const emptied = ({ had }, empty) => (had ? { value: empty } : { absent: true })
/** A cell's text: verbatim while it still shows what was loaded, trimmed once edited. */
const cell = (value, hyd) => (hyd !== undefined && value === hyd ? value : value.trim())

/** rows: [{ value, hyd }] — `hyd` is undefined for a row the user added. */
export function collectList(rows, snap) {
  if (same(rows.map((r) => r.value), snap.hyd)) return original(snap)
  const values = []
  for (const r of rows) {
    const v = cell(r.value, r.hyd)
    if (v || r.value === r.hyd) values.push(v) // an untouched '' is the file's own value
  }
  return values.length ? { value: values } : emptied(snap, [])
}

/** rows: [{ name, hyd, on }] — `hyd` is the name as hydrated. */
export function collectPlugins(rows, snap) {
  if (same(rows.map((r) => [r.name, r.on]), snap.hyd)) return original(snap)
  const out = Object.create(null) // a plugin named __proto__ must stay a real key
  for (const r of rows) {
    const key = cell(r.name, r.hyd)
    if (key) defineOwn(out, key, r.on)
  }
  return Object.keys(out).length ? { value: out } : emptied(snap, Object.create(null))
}

/**
 * rows: [{ name, nameHyd, type, field, value, valueHyd, autoUpdate, hadAuto }]
 * — `field` is the source key the type stores its value under (github → repo).
 */
export function collectMarkets(rows, snap) {
  const shown = rows.map(({ name, type, value, autoUpdate, hadAuto }) => ({ name, type, value, autoUpdate, hadAuto }))
  if (same(shown, snap.hyd)) return original(snap)
  const out = Object.create(null)
  for (const r of rows) {
    const name = cell(r.name, r.nameHyd)
    const value = cell(r.value, r.valueHyd)
    if (!name || !value || !r.field) continue
    const entry = { source: { source: r.type, [r.field]: value } }
    // absent and false are different keys in the file
    if (r.autoUpdate || r.hadAuto) entry.autoUpdate = r.autoUpdate
    defineOwn(out, name, entry)
  }
  return Object.keys(out).length ? { value: out } : emptied(snap, Object.create(null))
}
