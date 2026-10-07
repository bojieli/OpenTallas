import { spawnSync } from 'node:child_process'
import { commandInvocation, DEFAULT_EDITOR } from './launch.mjs'

/**
 * Split an $EDITOR value into argv: whitespace separates words, and double
 * or single quotes group one, so a path with spaces can be quoted
 * ("C:\Program Files\…\code.cmd" --wait). Backslashes are literal — on
 * Windows they are path separators, not escapes.
 *
 * @param {string} s
 * @returns {string[]}
 */
export function splitCommandLine(s) {
  const out = []
  let cur = '', inWord = false, quote = null
  for (const ch of s) {
    if (quote) { if (ch === quote) quote = null; else cur += ch; continue }
    if (ch === '"' || ch === "'") { quote = ch; inWord = true; continue }
    if (/\s/.test(ch)) { if (inWord) { out.push(cur); cur = ''; inWord = false } continue }
    cur += ch
    inWord = true
  }
  if (inWord) out.push(cur)
  return out
}

/**
 * Open `file` in the user's editor and report the outcome.
 *
 * $EDITOR / $VISUAL may legitimately contain arguments ("code --wait"). The
 * command is resolved the way agent launches are, so a Windows .cmd shim
 * (VS Code's `code`) runs by bare name. A spawn error or nonzero exit is
 * never silently swallowed as success.
 *
 * @returns {{ok: true} | {ok: false, message: string}}
 */
export function openInEditor(file) {
  const editor = process.env.EDITOR || process.env.VISUAL || DEFAULT_EDITOR
  const [cmd, ...args] = splitCommandLine(editor)
  if (!cmd) return { ok: false, message: 'EDITOR is set but empty' }

  const inv = commandInvocation(cmd, [...args, file])
  const r = spawnSync(inv.cmd, inv.args, { stdio: 'inherit', windowsVerbatimArguments: inv.verbatim })
  if (r.error) {
    return { ok: false, message: `cannot launch editor '${editor}': ${r.error.message}` }
  }
  if (r.status !== 0) {
    return { ok: false, message: `editor '${editor}' exited with status ${r.status ?? `signal ${r.signal}`}` }
  }
  return { ok: true }
}
