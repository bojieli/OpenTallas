import { loadProfileStrict } from '../store.mjs'
import { agentSettingsPath } from '../paths.mjs'
import { jsonDiff, maskDiffLeaf, sanitizeTerminal } from '../settings.mjs'
import { readLiveSettings } from '../live.mjs'

/**
 * Diff two profiles, or a profile against the live settings. The RAW structures
 * are compared first (two different secrets can't collide into "no diff");
 * only the leaves that are printed are masked.
 */
export function diff(a, b, { json = false } = {}) {
  let pa
  try {
    pa = loadProfileStrict(a)
  } catch (e) {
    return { output: `profile "${a}" is unreadable: ${e.message}`, exitCode: 1 }
  }
  if (pa == null) return { output: `profile not found: ${a}`, exitCode: 1 }

  let pb, bLabel
  if (b) {
    try {
      pb = loadProfileStrict(b)
    } catch (e) {
      return { output: `profile "${b}" is unreadable: ${e.message}`, exitCode: 1 }
    }
    if (pb == null) return { output: `profile not found: ${b}`, exitCode: 1 }
    bLabel = b
  } else {
    const lr = readLiveSettings(agentSettingsPath())
    if (!lr.ok) return { output: `cannot read current settings: ${lr.detail}`, exitCode: 1 }
    pb = lr.live
    bLabel = '(current live settings)'
  }

  const changes = jsonDiff(pa, pb)
    .map(c => ({
      // Mask with the raw path (secret-name detection), then sanitize the
      // printed path: a CSI-bearing key would otherwise land in `@@ path @@`.
      path: sanitizeTerminal(c.path),
      a: maskDiffLeaf(c.path, c.a),
      b: maskDiffLeaf(c.path, c.b),
    }))

  if (json) {
    return {
      output: JSON.stringify({
        version: 2,
        a,
        b: b || null,
        changes: changes.map(c => ({ path: c.path, a: c.a, b: c.b })),
      }, null, 2),
      exitCode: 0,
    }
  }

  if (!changes.length) return { output: '(no differences)', exitCode: 0 }
  const lines = [`--- ${a}`, `+++ ${bLabel}`]
  for (const c of changes) {
    lines.push(`@@ ${c.path} @@`)
    lines.push(`- ${JSON.stringify(c.a)}`)
    lines.push(`+ ${JSON.stringify(c.b)}`)
  }
  return { output: lines.join('\n'), exitCode: 0 }
}
