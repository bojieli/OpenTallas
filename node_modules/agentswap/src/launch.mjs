import { spawn, execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'

/** win32 extensions spawn can run directly (.exe/.com) or through cmd.exe (.cmd/.bat). */
const LAUNCHABLE_EXTS = ['.exe', '.com', '.cmd', '.bat']

/**
 * Resolve how to spawn the agent CLI for a given platform. Pure-ish so the
 * win32 branch is unit-testable: takes the platform + `where` output instead
 * of touching the real system.
 *
 * @returns {{cmd: string, verbatim: boolean, shim: (string|null)}}
 *   shim is set for npm .cmd/.bat shims — launchAgent then builds a single
 *   properly-quoted cmd.exe command line (see cmdCommandLine).
 */
export function resolveAgentCommand(platform, whereOutput, binName = 'claude') {
  if (platform !== 'win32') return { cmd: binName, verbatim: false, shim: null }
  // `where` also lists what neither CreateProcess nor cmd.exe can run — a
  // global npm install's extensionless sh shim (printed FIRST, beside the
  // .cmd) and its .ps1 — so take the first entry we can actually launch.
  const first = String(whereOutput ?? '').split(/\r?\n/).map(s => s.trim())
    .find(p => LAUNCHABLE_EXTS.includes(path.win32.extname(p).toLowerCase()))
  if (!first) return { cmd: binName, verbatim: false, shim: null }
  const lower = first.toLowerCase()
  if (lower.endsWith('.cmd') || lower.endsWith('.bat')) {
    // npm shim: run via cmd.exe with a fully quoted command line.
    return { cmd: 'cmd.exe', verbatim: true, shim: first }
  }
  return { cmd: first, verbatim: false, shim: null }
}

/**
 * Quote one argument for cmd.exe: wrap in double quotes when it contains
 * whitespace or cmd metacharacters; escape embedded quotes and trailing
 * backslashes C-runtime style.
 *
 * This is the FALLBACK path only. npm .cmd shims are normally bypassed via
 * resolveShimJsEntry (direct node spawn, no cmd.exe in the chain), which avoids
 * cmd.exe's `%VAR%` expansion — a layer behavior no argv quoting can disable.
 * The fallback's args are the user's own validated profile name, launchArgs
 * config, and command line, so the residual expansion is self-affecting.
 */
export function quoteCmdArg(arg) {
  const s = String(arg)
  if (s === '') return '""'
  if (!/[\s"&|<>()^]/.test(s)) return s
  let out = s.replace(/(\\*)"/g, '$1$1\\"')
  out = out.replace(/(\\+)$/, '$1$1')
  return `"${out}"`
}

/**
 * Build the single command-line string for `cmd /d /s /c`. The whole line is
 * wrapped in one outer pair of quotes (with /s, cmd strips exactly the first
 * and last quote), and every part is individually quoted — so spaces in paths
 * and shell metacharacters in pass-through args can neither split nor inject.
 */
export function cmdCommandLine(binPath, args) {
  return '"' + [binPath, ...args].map(quoteCmdArg).join(' ') + '"'
}

/**
 * Parse the interpreter args between the quoted interpreter and the quoted
 * script entry. npm cmd-shims pass node flags here (--enable-source-maps,
 * --no-warnings=…). Only bare flags are accepted: anything quoting, using cmd
 * metacharacters, or referencing %VARS% is a shape we can't reproduce with a
 * direct node spawn, so it returns null and the caller falls back to cmd.exe.
 */
function parseNodeArgs(s) {
  const tokens = s.trim().split(/\s+/).filter(Boolean)
  if (tokens.some(t => /["&|<>()^%]/.test(t) || !t.startsWith('-'))) return null
  return tokens
}

/**
 * Extract the JS entry AND its interpreter args from an npm .cmd shim's `%*`
 * line, or null for unrecognized shapes. npm shims end with a line like:
 *   "%_prog%"  [--node-flags…]  "%dp0%\node_modules\<pkg>\bin\<file>.js" %*
 * (older variants hardcode "%~dp0\node.exe"). Returns { entry, interpreterArgs }.
 *
 * The interpreter is the FIRST quoted token on the execution line, anchored:
 * matching any quoted token would re-sync at a quoted arg VALUE — npm's
 * official shape `node --conditions "node" "cli.js" %*` would restart at the
 * value "node", accept it as the interpreter, and silently drop --conditions.
 * A matched interpreter followed by args we can't reproduce (quoted values,
 * %VARS%) returns null so the caller falls back to cmd.exe.
 */
export function parseShimJsEntry(shimPath) {
  let text
  try { text = fs.readFileSync(shimPath, 'utf8') } catch { return null }
  const execLine = text.split(/\r?\n/).find((l) => /%\*/.test(l))
  if (!execLine) return null
  // Slice from the first quote so the match can only start at the first
  // quoted token (the interpreter) — no re-syncing at later quoted args.
  const firstQuote = execLine.indexOf('"')
  if (firstQuote < 0) return null
  const m = /^"([^"]+)"\s+([^"]*?)"([^"]+\.(?:m?js|cjs))"\s+%\*\s*$/i.exec(execLine.slice(firstQuote))
  if (!m) return null
  if (!/(?:^|[\\/])%_prog%$|(?:^|[\\/])node(?:\.exe)?$/i.test(m[1])) return null
  const interpreterArgs = parseNodeArgs(m[2])
  if (interpreterArgs === null) return null
  return { entry: m[3], interpreterArgs }
}

/**
 * Best-effort bypass of cmd.exe for npm .cmd shims: extract the JS entry the
 * shim invokes and spawn it with node directly. This avoids cmd.exe's %VAR%
 * expansion and quote rewriting entirely — the documented limitation of the
 * fallback path. Returns { jsPath, interpreterArgs }, or null for shim formats
 * we don't recognize; the caller then falls back to the quoted cmd.exe line.
 */
export function resolveShimJsEntry(shimPath) {
  const parsed = parseShimJsEntry(shimPath)
  if (!parsed) return null
  // The arg always carries its own separator right after the variable
  // ("%dp0%\node_modules\…"), so the replacement is the bare dirname.
  // Normalized: a shim written with "/" would otherwise yield a mixed path.
  const jsPath = path.normalize(parsed.entry.replace(/%~dp0|%dp0%/gi, () => path.dirname(shimPath)))
  try {
    if (!fs.existsSync(jsPath) || !fs.statSync(jsPath).isFile()) return null
  } catch { return null }
  return { jsPath, interpreterArgs: parsed.interpreterArgs }
}

function whereBin(name) {
  try {
    // argv, not a command string: the name may come from $EDITOR
    return execFileSync('where', [name], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] })
  } catch {
    return null
  }
}

/** Open `url` in the default browser, detached. Best effort: headless
 * machines have none, and the caller has already printed the URL. */
export function openUrl(url) {
  try {
    const child = process.platform === 'win32'
      ? spawn('cmd.exe', ['/d', '/s', '/c', 'start', '', url], { stdio: 'ignore', detached: true })
      : spawn(process.platform === 'darwin' ? 'open' : 'xdg-open', [url], { stdio: 'ignore', detached: true })
    child.on('error', () => {})
    child.unref()
  } catch { /* no browser to open */ }
}

/** The editor when neither $EDITOR nor $VISUAL is set. */
export const DEFAULT_EDITOR = process.platform === 'win32' ? 'notepad' : 'vi'

/**
 * How to spawn `bin` with `args` on this machine: { cmd, args, verbatim } for
 * spawn/spawnSync (never a shell). On win32 a bare name goes through `where`
 * — npm and VS Code install .cmd shims, which spawn cannot run by name — and
 * a path is taken as given. Agent launches, doctor's probe and the editor all
 * share it, so doctor checks the very binary a launch would run.
 */
export function commandInvocation(bin, args = []) {
  const platform = process.platform
  const located = platform !== 'win32' ? null : /[\\/]/.test(bin) ? bin : whereBin(bin)
  const { cmd, verbatim, shim } = resolveAgentCommand(platform, located, bin)
  const jsEntry = shim ? resolveShimJsEntry(shim) : null
  if (jsEntry) {
    // Direct node spawn of the shim's JS entry — no cmd.exe in the chain.
    // The shim's own node flags (--enable-source-maps, …) are forwarded.
    return { cmd: process.execPath, args: [...jsEntry.interpreterArgs, jsEntry.jsPath, ...args], verbatim: false }
  }
  return { cmd, args: shim ? ['/d', '/s', '/c', cmdCommandLine(shim, args)] : args, verbatim }
}

/**
 * Launch the agent CLI, forwarding exit code. Uses spawn (not exec) so Windows
 * works; parent ignores SIGINT so Ctrl-C goes to child.
 */
export function launchAgent({ args = [], env = process.env, cwd, binName = 'claude' } = {}) {
  const inv = commandInvocation(binName, args)
  const child = spawn(inv.cmd, inv.args, {
    stdio: 'inherit',
    env,
    cwd,
    shell: false,
    windowsVerbatimArguments: inv.verbatim,
  })
  process.on('SIGINT', () => {})
  return new Promise((resolve) => {
    child.on('exit', (code, signal) => {
      resolve(signal ? 128 + (os.constants.signals[signal] ?? 0) : (code ?? 0))
    })
    child.on('error', (err) => {
      console.error(`failed to launch ${binName}: ${err.message}`)
      resolve(1)
    })
  })
}

/** Build argv for run mode: exclude user layer, point at effective settings file. */
export function runArgs(settingsFile, launchArgs = [], extraArgs = []) {
  return [
    '--setting-sources', 'project,local',
    '--settings', settingsFile,
    ...launchArgs,
    ...extraArgs,
  ]
}

/**
 * The auth/routing env namespace. A controlled launch strips these inherited
 * parent-env keys before injecting the profile's own env, so a stale inherited
 * token can't shadow the profile's provider. Scope:
 *   - the whole ANTHROPIC_ namespace (auth token, api key, base URL, routing);
 *   - auth-ish CLAUDE_CODE_ (OAuth token, api keys, secrets, Bedrock/Vertex routing).
 * Non-auth CLAUDE_CODE_* config is left alone.
 */
export function isAuthRoutingEnvKey(key) {
  if (/^ANTHROPIC_/.test(key)) return true
  if (/^CLAUDE_CODE_/.test(key)) {
    // Word-boundary matching so CLAUDE_CODE_MAX_OUTPUT_TOKENS (contains the
    // substring TOKEN) is NOT stripped, while CLAUDE_CODE_OAUTH_TOKEN /
    // CLAUDE_CODE_API_KEY are.
    if (/(^|_)(TOKEN|KEY|AUTH|SECRET|BEARER|CREDENTIAL)(_|$)/i.test(key)) return true
    if (/^CLAUDE_CODE_USE_(BEDROCK|VERTEX)$/i.test(key)) return true
    return false
  }
  return false
}

/**
 * Build the child env for a controlled launch, shared by sticky and run modes.
 * Start from the parent env, delete the auth/routing namespace plus any explicit
 * `unsetEnv`, then inject the profile's env. A profile value of `null` deletes
 * that key.
 */
export function launchEnv(profileEnv = {}, { baseEnv = process.env, unsetEnv = [] } = {}) {
  const next = { ...baseEnv }
  for (const k of Object.keys(next)) if (isAuthRoutingEnvKey(k)) delete next[k]
  for (const k of unsetEnv || []) delete next[k]
  for (const [k, v] of Object.entries(profileEnv || {})) {
    if (v === null || v === undefined) delete next[k]
    else next[k] = String(v)
  }
  return next
}
