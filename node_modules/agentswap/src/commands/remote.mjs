import { addRemote, removeRemote, listRemotes } from '../remotes.mjs'

const ADD_USAGE = 'usage: agentswap remote add <name> --host <ssh-host> [--bin <path>]'
const RM_USAGE = 'usage: agentswap remote rm <name>'
const USAGE = 'usage: agentswap remote add <name> --host <ssh-host> [--bin <path>]\n'
  + '       agentswap remote ls\n'
  + '       agentswap remote rm <name>'

/**
 * `agentswap remote` — add / ls / rm the machine-local remote registry.
 *
 * @param {{ sub?: string|null, name?: string|null, host?: string|null, bin?: string|null, json?: boolean }} opts
 * @returns {Promise<{ output: string, exitCode: number }>}
 */
export async function remote({ sub, name = null, host = null, bin = null, json = false } = {}) {
  const cmd = sub ?? 'ls'
  if (cmd === 'add') {
    if (!name || !host) return fail(json, 'usage', ADD_USAGE)
    return addRemote(name, { host, bin: bin || undefined, json })
  }
  if (cmd === 'ls') return listCmd(json)
  if (cmd === 'rm') {
    if (!name) return fail(json, 'usage', RM_USAGE)
    return removeRemote(name, { json })
  }
  return fail(json, 'usage', USAGE)
}

function listCmd(json) {
  const remotes = listRemotes()
  const items = Object.keys(remotes).sort().map(name => ({
    name,
    host: remotes[name].host,
    bin: remotes[name].bin,
  }))
  if (json) {
    return { output: JSON.stringify({ version: 2, remotes: items }, null, 2), exitCode: 0 }
  }
  if (!items.length) {
    return { output: 'no remotes — add one with: agentswap remote add <name> --host <ssh-host>', exitCode: 0 }
  }
  const rows = [['NAME', 'HOST', 'BIN'], ...items.map(it => [it.name, it.host, it.bin])]
  const widths = [0, 1, 2].map(i => Math.max(...rows.map(r => String(r[i]).length)))
  const lines = rows.map(r => r.map((c, i) => String(c).padEnd(widths[i])).join('  '))
  return { output: lines.join('\n'), exitCode: 0 }
}

function fail(json, error, detail, hint = null) {
  return {
    output: json
      ? JSON.stringify({ version: 2, error, detail, ...(hint ? { hint } : {}) }, null, 2)
      : detail,
    exitCode: 1,
  }
}
