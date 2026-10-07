import {
  saveProfile, profileExists, caseVariantOf, registerProfileMeta,
  validateProfileObject, ensureAcsHome,
} from '../store.mjs'
import { agentSettingsPath, isValidPlatform, KNOWN_PLATFORMS } from '../paths.mjs'
import { getTemplateForPlatform } from '../templates.mjs'
import { readLiveSettings } from '../live.mjs'

/**
 * Shared profile creation logic across CLI and Web.
 * Sources:
 * - fromCurrent: boolean (snapshot live settings)
 * - settings: object (verbatim settings provided explicitly)
 * - platform: string ('darwin'|'linux'|'win32')
 * When neither fromCurrent nor settings is given and platform is omitted, platform defaults to process.platform.
 *
 * Sources are mutually exclusive: cannot specify more than one of fromCurrent, settings, or explicit platform.
 * Returns { ok: true, name, settings, platform } or { ok: false, error, code, detail, exitCode }
 */
export function createProfileCore(name, {
  fromCurrent = false,
  settings = null,
  platform = null,
  notes = '',
  launchArgs = null,
  unsetEnv = [],
} = {}) {
  // Mutual exclusivity of explicit sources
  const explicitSources = [
    fromCurrent ? 'fromCurrent' : null,
    settings !== null && settings !== undefined ? 'settings' : null,
    platform !== null && platform !== undefined ? 'platform' : null,
  ].filter(Boolean)

  if (explicitSources.length > 1) {
    return {
      ok: false,
      error: 'source-conflict',
      detail: `cannot combine ${explicitSources.join(' and ')}`,
      exitCode: 1,
    }
  }

  let finalSettings
  let effectivePlatform = null

  if (fromCurrent) {
    // The same live reader use/save/current/doctor use: absent or blank → {},
    // unreadable or not an object → refused.
    const lr = readLiveSettings(agentSettingsPath())
    if (!lr.ok) return { ok: false, error: 'settings-unreadable', detail: `cannot read ${agentSettingsPath()}: ${lr.detail}`, exitCode: 1 }
    finalSettings = lr.live
  } else if (settings !== null && settings !== undefined) {
    let s = settings
    if (typeof s === 'string') {
      try { s = JSON.parse(s) } catch (e) { return { ok: false, error: 'invalid-json', detail: 'settings must be valid JSON', exitCode: 1 } }
    }
    const v = validateProfileObject(s)
    if (!v.ok) return { ok: false, error: 'invalid-profile', detail: v.reason, exitCode: 1 }
    finalSettings = s
  } else {
    // Platform template source
    effectivePlatform = platform || process.platform
    if (platform !== null && platform !== undefined && !isValidPlatform(platform)) {
      return {
        ok: false,
        error: 'invalid-platform',
        detail: `invalid platform "${platform}". Must be one of: ${KNOWN_PLATFORMS.join(', ')}`,
        exitCode: 1,
      }
    }
    try {
      finalSettings = getTemplateForPlatform(effectivePlatform)
    } catch (e) {
      return { ok: false, error: e.code || 'template-error', detail: e.message, exitCode: 1 }
    }
  }

  if (profileExists(name)) {
    return { ok: false, error: 'name-exists', detail: `profile already exists: ${name}`, exitCode: 1 }
  }
  const other = caseVariantOf(name)
  if (other) {
    return { ok: false, error: 'name-exists', detail: `profile "${other}" already exists (names are case-insensitive: one file on macOS/Windows)`, exitCode: 1 }
  }

  ensureAcsHome()
  saveProfile(name, finalSettings)
  registerProfileMeta(name, { notes, launchArgs, unsetEnv })

  return {
    ok: true,
    name,
    settings: finalSettings,
    fromCurrent,
    platform: effectivePlatform,
  }
}
