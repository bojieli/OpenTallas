import { spawn } from 'node:child_process'

/**
 * POSIX single-quote escaping for a remote-shell token. Single quotes are the
 * only quoting that disables every expansion (`$`, backticks, `!`); an
 * embedded quote is closed, escaped, and reopened (`'foo'\''bar'`).
 *
 * @param {string} s
 * @returns {string}
 */
export function shellQuote(s) {
  return `'${String(s).replace(/'/g, `'\\''`)}'`
}

/**
 * Build the remote command string: `'<bin>' __sync <sub>[ '<name>'] --json`.
 * Names are already validated [a-z0-9_-]; quoting is still applied so a
 * future charset change cannot turn the token into extra argv.
 *
 * @param {string} bin
 * @param {string} sub
 * @param {string|null} [name]
 * @returns {string}
 */
export function buildRemoteCommand(bin, sub, name = null) {
  const parts = [shellQuote(bin), '__sync', sub]
  if (name != null) parts.push(shellQuote(name))
  parts.push('--json')
  return parts.join(' ')
}

/**
 * One-shot SSH. BatchMode=yes is mandatory: a password prompt would hang a
 * sync and eat the JSON piped to a write's stdin. Rejects on non-zero exit
 * or spawn error with code ESSH. stdout/stderr are attached to the error so
 * runRemoteJson can still parse a __sync error envelope (exit 1 + JSON on
 * stdout) instead of swallowing it as a transport failure.
 *
 * @param {string} host
 * @param {string} command
 * @param {{ input?: string|null }} [opts]
 * @returns {Promise<{ stdout: string, stderr: string }>}
 */
export function sshRun(host, command, { input = null } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn('ssh', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', host, command], {
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    let stdout = ''
    let stderr = ''
    let settled = false

    const fail = (detail) => {
      if (settled) return
      settled = true
      const err = new Error(`agentswap: ssh to ${host} failed: ${detail}`)
      err.code = 'ESSH'
      err.stdout = stdout
      err.stderr = stderr
      reject(err)
    }

    child.stdout.setEncoding('utf8')
    child.stderr.setEncoding('utf8')
    child.stdout.on('data', (chunk) => { stdout += chunk })
    child.stderr.on('data', (chunk) => { stderr += chunk })
    // ssh can exit before reading the whole request (connection refused, an
    // unknown host): the unread rest of a large body is an EPIPE on stdin,
    // and an unhandled stream error would crash the process (the web server
    // included). Record it; `close` decides, and a request that never fully
    // went out is a failure even if ssh itself exited 0.
    let stdinErr = null
    child.stdin.on('error', (e) => { stdinErr = e })
    child.on('error', (e) => fail(e.message))
    child.on('close', (code) => {
      if (settled) return
      if (code !== 0) {
        fail(stderr.trim() || `ssh exited ${code}`)
        return
      }
      if (stdinErr) {
        fail(`could not send the request: ${stdinErr.message}`)
        return
      }
      settled = true
      resolve({ stdout, stderr })
    })
    if (input != null) child.stdin.write(input)
    child.stdin.end()
  })
}

/**
 * Run a __sync subcommand against a remote and parse the JSON envelope.
 * A non-zero ssh status with parseable JSON is a remote application error
 * (conflict, not-found), not a transport failure — __sync writes JSON to
 * stdout and uses a nonzero exit the same way every other command does.
 *
 * @param {{ host: string, bin: string }} remote
 * @param {string} sub
 * @param {string|null} [name]
 * @param {string|null} [input]
 * @returns {Promise<object>}
 */
export async function runRemoteJson(remote, sub, name = null, input = null) {
  const command = buildRemoteCommand(remote.bin, sub, name)
  let stdout
  let sshErr = null
  try {
    stdout = (await sshRun(remote.host, command, { input })).stdout
  } catch (e) {
    if (e.code !== 'ESSH' || typeof e.stdout !== 'string') throw e
    stdout = e.stdout
    sshErr = e
  }
  let parsed
  try {
    parsed = JSON.parse(stdout)
  } catch (e) {
    if (sshErr) throw sshErr
    const err = new Error(`agentswap: remote ${remote.host} returned non-JSON output: ${e.message}`)
    err.code = 'EREMOTEBADJSON'
    throw err
  }
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed) && parsed.error) {
    const err = new Error(`agentswap: remote ${remote.host}: ${parsed.detail || parsed.error}`)
    err.code = 'EREMOTE'
    err.remoteError = parsed.error
    throw err
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed) || parsed.version !== 2) {
    const err = new Error(`agentswap: remote ${remote.host} returned an unrecognized envelope (expected { version: 2, ... })`)
    err.code = 'EREMOTEBADJSON'
    throw err
  }
  return parsed
}

/**
 * Capability handshake for `remote add`: the remote must answer the __sync
 * protocol, not just print a version string (an older agentswap without
 * __sync would otherwise register fine and fail at the first sync).
 *
 * @param {{ host: string, bin: string }} remote
 * @returns {Promise<void>}
 */
export async function probeRemote({ host, bin }) {
  await runRemoteJson({ host, bin }, 'list')
}
