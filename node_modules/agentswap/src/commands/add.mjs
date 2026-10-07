import { profilePath, withLock } from '../store.mjs'
import { isReserved, isValidProfileName } from '../reserved.mjs'
import { openInEditor } from '../editor.mjs'
import { normalizePlatform, KNOWN_PLATFORMS } from '../paths.mjs'
import { createProfileCore } from './create-profile.mjs'

/**
 * Create a new profile. `--from-current` snapshots the WHOLE current
 * settings.json verbatim; `--platform <darwin|linux|win32>` templates for a specific platform;
 * otherwise the current running platform's template is used.
 * The existence check + write + metadata registration run under one lock hold.
 */
export async function add(name, { fromCurrent = false, platform = null, json = false } = {}) {
  const fail = (error, detail, exitCode = 1) => ({
    output: json ? JSON.stringify({ version: 2, error, detail }) : detail, exitCode,
  })
  if (!name) return fail('name-required', 'usage: agentswap add <name> [--from-current] [--platform <platform>]')
  if (isReserved(name)) {
    return fail('name-reserved', `'${name}' is a reserved command name — pick another profile name`)
  }
  if (!isValidProfileName(name)) {
    return fail('name-invalid', `invalid profile name: '${name}' (letters, digits, _ and -; must start with a letter or digit)`)
  }

  // Mutually exclusive sources: --from-current vs --platform
  if (fromCurrent && platform !== null && platform !== undefined) {
    return fail('source-conflict', 'cannot combine --from-current with --platform')
  }

  // If platform is specified, it must not be empty or invalid
  const plat = platform === null || platform === undefined ? null : normalizePlatform(platform)
  if (platform !== null && platform !== undefined && plat === null) {
    return fail('invalid-platform', `invalid platform "${platform}". Must be one of: ${KNOWN_PLATFORMS.join(', ')}`)
  }

  const result = await withLock(() => createProfileCore(name, { fromCurrent, platform: plat }))

  if (!result.ok) {
    return fail(result.error, result.detail || result.error, result.exitCode || 1)
  }

  // Only open in $EDITOR when not in --json mode, and not fromCurrent
  if (!fromCurrent && !json) {
    const r = openInEditor(profilePath(name))
    if (!r.ok) {
      return {
        output: `created profile: ${name}\n${r.message}\nedit it later with: agentswap edit ${name}`,
        exitCode: 1,
      }
    }
  }

  if (json) {
    const payload = { version: 2, name, fromCurrent }
    if (result.platform) payload.platform = result.platform
    return { output: JSON.stringify(payload), exitCode: 0 }
  }
  const platSuffix = result.platform ? ` (${result.platform} template)` : ''
  return { output: `created profile: ${name}${fromCurrent ? ' (from current settings)' : platSuffix}`, exitCode: 0 }
}

