import { loadProfileStrict, loadConfig } from '../store.mjs'
import { maskSettings, sanitizeTerminal } from '../settings.mjs'

/**
 * Show a profile's full settings. Secrets are best-effort masked; `--reveal`
 * prints them verbatim.
 */
export function show(name, { reveal = false, json = false } = {}) {
  let profile
  try {
    profile = loadProfileStrict(name)
  } catch (e) {
    return { output: `profile "${name}" is unreadable: ${e.message}`, exitCode: 1 }
  }
  if (profile == null) return { output: `profile not found: ${name}`, exitCode: 1 }

  // --reveal bypasses maskSettings; still strip CSI/OSC so a synced profile
  // cannot hijack the terminal. maskSettings already sanitizes its strings.
  const settings = reveal ? sanitizeDeep(profile) : maskSettings(profile)
  const meta = loadConfig().profiles?.[name] || {}

  if (json) {
    return {
      output: JSON.stringify({
        version: 2,
        name,
        notes: sanitizeTerminal(meta.notes || ''),
        hasLaunchArgsOverride: Array.isArray(meta.launchArgs),
        settings,
        revealed: reveal,
      }, null, 2),
      exitCode: 0,
    }
  }

  const lines = [`# ${name}`]
  if (meta.notes) lines.push(`# notes: ${sanitizeTerminal(meta.notes)}`)
  if (Array.isArray(meta.launchArgs)) {
    lines.push(`# launchArgs: ${meta.launchArgs.map(a => sanitizeTerminal(String(a))).join(' ')}`)
  }
  lines.push(JSON.stringify(settings, null, 2))
  if (!reveal) lines.push('# (secrets masked best-effort — use --reveal to see full values)')
  return { output: lines.join('\n'), exitCode: 0 }
}

function sanitizeDeep(value) {
  if (typeof value === 'string') return sanitizeTerminal(value)
  if (Array.isArray(value)) return value.map(sanitizeDeep)
  if (value !== null && typeof value === 'object') {
    const out = Object.create(null)
    for (const k of Object.keys(value)) out[k] = sanitizeDeep(value[k])
    return out
  }
  return value
}
