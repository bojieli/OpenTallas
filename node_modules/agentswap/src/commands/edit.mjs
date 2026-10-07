import { profilePath, profileExists } from '../store.mjs'
import { openInEditor } from '../editor.mjs'

/**
 * Open an existing profile in $EDITOR. The profile is a plain settings JSON
 * file. The name must exist exactly: where the filesystem ignores case,
 * editing "WORK" would otherwise open work.json, and a new name would be
 * created by the editor behind `add`'s back.
 */
export function edit(name) {
  if (!name) return { output: 'usage: agentswap edit <name>', exitCode: 1 }
  if (!profileExists(name)) return { output: `profile not found: ${name} — create it with: agentswap add ${name}`, exitCode: 1 }
  const r = openInEditor(profilePath(name))
  if (!r.ok) return { output: r.message, exitCode: 1 }
  return { output: '', exitCode: 0 }
}
