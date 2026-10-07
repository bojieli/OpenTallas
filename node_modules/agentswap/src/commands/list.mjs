import { listProfileNames, loadConfig, readTrustedStateV2 } from '../store.mjs'

/**
 * List profiles. A profile is a complete settings snapshot; metadata (notes,
 * launchArgs override) lives in config.profiles, not in the profile file.
 */
export function list({ json = false } = {}) {
  const names = listProfileNames()
  const cfg = loadConfig()
  const state = readTrustedStateV2()
  const active = state?.activeProfile ?? null
  const metas = cfg.profiles || {}

  const items = names.map(name => {
    const meta = metas[name] || {}
    return {
      name,
      notes: meta.notes || '',
      hasLaunchArgsOverride: Array.isArray(meta.launchArgs),
      active: name === active,
    }
  })

  if (json) {
    return JSON.stringify({ version: 2, active, profiles: items }, null, 2)
  }

  const lines = []
  for (const it of items) {
    const mark = it.active ? '*' : ' '
    const notes = it.notes ? `  — ${it.notes}` : ''
    lines.push(`${mark} ${it.name}${notes}`)
  }
  if (!lines.length) lines.push('(no profiles — try `agentswap add <name>`)')
  return lines.join('\n')
}
