import { createHash } from 'node:crypto'

/**
 * Canonical form, content hash, semantic equality, deep diff and secret masking.
 * All pure. Single source of truth for equality and hashing.
 */

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v)
}

/**
 * Deterministic canonical value as a stable JSON string: recursively sort object
 * keys, preserve array order. `null` ≠ missing and number ≠ string stay distinct.
 */
export function canonicalize(value) {
  return JSON.stringify(canonicalValue(value))
}

function canonicalValue(value) {
  if (Array.isArray(value)) return value.map(canonicalValue)
  if (isPlainObject(value)) {
    // Object.create(null): a plain `{}` assignment treats `__proto__` as a
    // setter, so a profile with a __proto__ key would canonicalize to `{}` and
    // collide with a genuinely empty object. Null-proto objects keep it as a
    // real own key (and stringify identically to plain objects).
    const out = Object.create(null)
    for (const key of Object.keys(value).sort()) out[key] = canonicalValue(value[key])
    return out
  }
  return value
}

/** sha256 (hex) of the canonical form. Used as the appliedHash baseline. */
export function contentHash(value) {
  return createHash('sha256').update(canonicalize(value)).digest('hex')
}

/** Canonical semantic equality. Ignores whitespace + key order; arrays order-sensitive. */
export function deepEqual(a, b) {
  return canonicalize(a) === canonicalize(b)
}

/**
 * Generic deep diff → array of { path, a, b } for each differing leaf path
 * (dot notation; arrays by index). Keys absent on one side surface as `undefined`.
 */
export function jsonDiff(a, b) {
  const out = []
  diffWalk('', a, b, out)
  return out
}

function diffWalk(path, a, b, out) {
  if (isPlainObject(a) && isPlainObject(b)) {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)])
    for (const k of [...keys].sort()) diffWalk(path ? `${path}.${k}` : k, a[k], b[k], out)
    return
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    const len = Math.max(a.length, b.length)
    for (let i = 0; i < len; i++) diffWalk(path ? `${path}.${i}` : String(i), a[i], b[i], out)
    return
  }
  if (!deepEqual(a, b)) out.push({ path, a, b })
}

// ---- terminal sanitization ---------------------------------------------------
//
// Profile strings (including ones pulled from a remote) are printed to a TTY
// by show/diff. CSI/OSC in a value can hijack the agent's terminal; strip them
// at the display chokepoint, never from canonical hashes (those compare raw).

const CSI_RE = /\x1b\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]/g
const OSC_RE = /\x1b\](?:[^\x07\x1b]|\x1b(?!\\))*?(?:\x07|\x1b\\)/g

/**
 * Strip CSI (`ESC [` … final byte), OSC (`ESC ]` … BEL or ST), then any
 * leftover bare ESC, from a string. Non-strings pass through unchanged.
 *
 * @param {unknown} value
 * @returns {unknown}
 */
export function sanitizeTerminal(value) {
  if (typeof value !== 'string') return value
  return value.replace(CSI_RE, '').replace(OSC_RE, '').replace(/\x1b/g, '')
}

// ---- masking ----------------------------------------------------------------

/** Normalize a key for secret matching: camelCase → snake_case, then any non-alphanumeric run (hyphens, dots, spaces) → underscore, lowercase. */
function normalizeKey(key) {
  return String(key)
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
}

// Word-boundary secret vocabulary on the NORMALIZED key. `api_?key` covers both
// `api_key` and `apikey`; `auth(orization|entication)?` covers auth /
// authorization / authentication; `oauth2?` covers oauth / oauth2. Boundaries
// keep `monkey`/`keyboard`/`author` untainted.
const SECRET_WORD_RE = /(^|_)(token|api_?key|secret|password|passwd|credential|auth(orization|entication)?|oauth2?|private_?key|access_?key)(_|$)/

/** Secret key-name test, camelCase/delimiter-insensitive (apiKey, private_key, AUTH_TOKEN). */
export function isSecretKey(key) {
  return SECRET_WORD_RE.test(normalizeKey(key))
}

const SECRET_PREFIXES = ['sk_live_', 'sk_test_', 'sk-', 'plat_', 'Bearer ', 'Basic ', 'Digest ']

/** Keep a last-4 hint only at/above this length; shorter values reveal nothing. */
const KEEP_SUFFIX_MIN = 8

/**
 * Format-heuristic mask (fallback when a key name doesn't flag a secret). Masks
 * strings that LOOK like secrets: known prefixes, long hex (≥32), or token-ish
 * (≥24 chars containing `_`/`-`).
 */
export function maskValue(v) {
  if (typeof v !== 'string' || v.length === 0) return v
  const suffix = v.length >= KEEP_SUFFIX_MIN ? v.slice(-4) : ''
  for (const p of SECRET_PREFIXES) {
    if (v.startsWith(p)) return `${p}…${suffix}(len=${v.length})`
  }
  if (v.length >= 32 && /^[0-9a-fA-F]+$/.test(v)) return `…${v.slice(-4)}(len=${v.length})`
  if (v.length >= 24 && /[_-]/.test(v)) return `…${v.slice(-4)}(len=${v.length})`
  return v
}

/** Force-mask a string: keep a format hint if recognized, else a fixed placeholder. */
function forceMask(v) {
  if (typeof v !== 'string' || v.length === 0) return v
  const h = maskValue(v)
  if (h !== v) return h
  if (v.length < KEEP_SUFFIX_MIN) return `••••(len=${v.length})`
  return `…${v.slice(-4)}(len=${v.length})`
}

/**
 * Mask a single diff leaf value, using its dot-path for context: an `env`
 * segment or any secret-named segment taints the value. Diff compares RAW
 * structures first (so two different secrets can't collide into "no diff"),
 * then masks only the leaves it is about to print.
 *
 * A leaf is not always a string: a key present on one side only (or whose
 * type changed) is ONE leaf holding the whole subtree, so it is masked with
 * the same recursive rules as `show`, seeded with the path's taint.
 *
 * The whole path is tested as ONE key too: a literal dot-key like
 * `x.api.key` would otherwise split into innocent segments (x/api/key) and
 * leak its value, while `show` masks it via the whole-key test.
 */
export function maskDiffLeaf(path, value) {
  const p = String(path)
  const tainted = isSecretKey(p) || p.split('.').some(seg => seg === 'env')
  return maskNode(value, tainted, false)
}

/**
 * Recursive masking for show/diff. Never mutates the input.
 *   (a) any ANCESTOR key matching the secret vocabulary taints the whole subtree;
 *   (b) every string directly under an `env` object is masked regardless of name;
 *   (c) otherwise the maskValue format heuristic applies.
 */
export function maskSettings(obj) {
  return maskNode(obj, false, false)
}

function maskNode(value, tainted, envContainer) {
  if (Array.isArray(value)) return value.map(el => maskNode(el, tainted, false))
  if (isPlainObject(value)) {
    const out = Object.create(null) // keep a __proto__ key as a real own property
    for (const k of Object.keys(value)) {
      const child = value[k]
      const childTainted = tainted || isSecretKey(k)
      if (typeof child === 'string') {
        out[k] = sanitizeTerminal((childTainted || envContainer) ? forceMask(child) : maskValue(child))
      } else {
        out[k] = maskNode(child, childTainted, k === 'env')
      }
    }
    return out
  }
  if (typeof value === 'string') return sanitizeTerminal(tainted ? forceMask(value) : maskValue(value))
  return value
}
