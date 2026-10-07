import fs from 'node:fs'
import { templatesPath, KNOWN_PLATFORMS, normalizePlatform } from './paths.mjs'
import { validateProfileObject, writeJson } from './store.mjs'
import { contentHash } from './settings.mjs'

/**
 * Return a fresh instance of the default 3 platform templates.
 * Each platform defaults to `{ env: {} }`.
 */
export function defaultTemplates() {
  return {
    darwin: { env: {} },
    linux: { env: {} },
    win32: { env: {} },
  }
}

/**
 * Read the templates file.
 * - Absent: returns default 3 templates.
 * - Present: must be valid JSON object containing valid objects for ALL known platforms.
 *   Missing any known platform is an invalid file (EINVALIDTEMPLATES).
 * - Malformed / invalid: throws an Error (never silent fallback).
 */
export function loadTemplates() {
  const file = templatesPath()
  let raw
  try {
    raw = fs.readFileSync(file, 'utf8')
  } catch (e) {
    if (e.code === 'ENOENT') return defaultTemplates()
    throw e
  }

  let parsed
  try {
    parsed = JSON.parse(raw)
  } catch {
    const err = new Error(`cannot parse templates file ${file}: invalid JSON`)
    err.code = 'ETEMPLATESPARSE'
    throw err
  }

  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    const err = new Error(`templates file ${file} must contain a JSON object`)
    err.code = 'EINVALIDTEMPLATES'
    throw err
  }

  // File exists: ALL known platforms must be present and valid
  for (const plat of KNOWN_PLATFORMS) {
    if (!(plat in parsed)) {
      const err = new Error(`templates file ${file} is missing required platform "${plat}"`)
      err.code = 'EINVALIDTEMPLATES'
      throw err
    }
    const v = validateProfileObject(parsed[plat])
    if (!v.ok) {
      const err = new Error(`template for "${plat}" is invalid: ${v.reason}`)
      err.code = 'EINVALIDTEMPLATES'
      throw err
    }
  }

  // Return the parsed object directly (so unknown top-level keys like __proto__ or custom keys are retained)
  return parsed
}

/**
 * Save templates object atomically.
 */
export function saveTemplates(templatesObj) {
  writeJson(templatesPath(), templatesObj)
}

/**
 * Get the settings snapshot for a given platform.
 * Throws if platform is invalid or template file is corrupt.
 */
export function getTemplateForPlatform(platform) {
  const norm = normalizePlatform(platform)
  if (!norm) {
    const err = new Error(`invalid platform "${platform}". Must be one of: ${KNOWN_PLATFORMS.join(', ')}`)
    err.code = 'EBADPLATFORM'
    throw err
  }
  const all = loadTemplates()
  const tmpl = all[norm]
  // Deep clone so caller cannot mutate loaded object
  return JSON.parse(JSON.stringify(tmpl))
}

/**
 * Summary of all 3 templates for API consumption:
 * [{ platform, settings, hash }]
 */
export function listTemplatesSummary() {
  const all = loadTemplates()
  return KNOWN_PLATFORMS.map(platform => {
    const settings = all[platform]
    return {
      platform,
      settings,
      hash: contentHash(settings),
    }
  })
}

/**
 * Update a specific platform's template with compare-and-swap (expectedHash).
 * Must be called within withLock to ensure freshness and prevent concurrent lost updates.
 * Reads fresh templates inside lock, checks only the target platform's hash,
 * replaces only that platform's key on the parsed object, and saves.
 *
 * expectedHash must be a non-empty string.
 * Returns { ok: true, platform, hash, settings } or throws conflict / validation error.
 */
export function updateTemplateCAS(platform, { settings, expectedHash }) {
  const norm = normalizePlatform(platform)
  if (!norm) {
    const err = new Error(`invalid platform "${platform}". Must be one of: ${KNOWN_PLATFORMS.join(', ')}`)
    err.code = 'EBADPLATFORM'
    throw err
  }

  if (typeof expectedHash !== 'string' || expectedHash.trim() === '') {
    const err = new Error('expectedHash must be a non-empty string')
    err.code = 'EMISSINGEXPECTEDHASH'
    throw err
  }

  const v = validateProfileObject(settings)
  if (!v.ok) {
    const err = new Error(`invalid settings object for template "${platform}": ${v.reason}`)
    err.code = 'EINVALIDPROFILE'
    throw err
  }

  // Load FRESH templates under the lock (throws if corrupt or missing required platforms)
  const all = loadTemplates()
  const currentSettings = all[norm]
  const currentHash = contentHash(currentSettings)

  if (expectedHash !== currentHash) {
    const err = new Error(`template conflict for "${platform}": expected hash ${expectedHash}, current hash is ${currentHash}`)
    err.code = 'ETEMPLATECONFLICT'
    err.currentHash = currentHash
    throw err
  }

  // Mutate directly on the loaded object to preserve any existing custom/prototype properties
  all[norm] = settings
  saveTemplates(all)

  const newHash = contentHash(settings)
  return { ok: true, platform: norm, hash: newHash, settings }
}
