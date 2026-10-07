#!/usr/bin/env node
import fsp from 'node:fs/promises'
import { list } from '../src/commands/list.mjs'
import { current } from '../src/commands/current.mjs'
import { show } from '../src/commands/show.mjs'
import { use } from '../src/commands/use.mjs'
import { save } from '../src/commands/save.mjs'
import { run } from '../src/commands/run.mjs'
import { add } from '../src/commands/add.mjs'
import { edit } from '../src/commands/edit.mjs'
import { rm } from '../src/commands/rm.mjs'
import { diff } from '../src/commands/diff.mjs'
import { doctor } from '../src/commands/doctor.mjs'
import { skillInstall } from '../src/commands/skill.mjs'
import { importProfiles } from '../src/commands/import.mjs'
import { backupList, restore } from '../src/commands/backup.mjs'
import { remote } from '../src/commands/remote.mjs'
import { pushProfile, pullProfile, syncAll } from '../src/commands/sync.mjs'
import { syncAgent } from '../src/commands/sync-agent.mjs'
import { startWeb } from '../src/web/server.mjs'
import { launchAgent } from '../src/launch.mjs'
import {
  readTrustedStateV2, listProfileNames, profileExists,
} from '../src/store.mjs'
import { RESERVED } from '../src/reserved.mjs'
import { COMMANDS, MODES, getCommand, renderHelp } from '../src/cli-spec.mjs'

const HELP = renderHelp()

// Only these two flags are intercepted by `agentswap <name>`; everything else
// (including --force/--yes, which the agent itself understands) passes through.
const SWITCH_FLAGS = new Set(['--discard', '--overwrite-profile'])

function parseSubArgs(argv, valueFlags = []) {
  const positional = []
  const flags = {}
  const values = {}
  let passThrough = []
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--') { passThrough = argv.slice(i + 1); break }
    if (a.startsWith('--')) {
      const key = a.slice(2)
      if (valueFlags.includes(key) && i + 1 < argv.length) { values[key] = argv[++i]; continue }
      flags[key] = true
      continue
    }
    positional.push(a)
  }
  return { positional, flags, values, passThrough }
}

function parseRun(rest) {
  let name = null, jsonCmd = false, saveOnExit = false
  const extra = []
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i]
    if (a === '--') { extra.push(...rest.slice(i + 1)); break }
    if (a === '--json-cmd') { jsonCmd = true; continue }
    if (a === '--save-on-exit') { saveOnExit = true; continue }
    if (name === null && !a.startsWith('-')) { name = a; continue }
    extra.push(a)
  }
  return { name, jsonCmd, saveOnExit, extra }
}

function parseProfileArgs(argv) {
  let discard = false, overwriteProfile = false
  const passThrough = []
  let sep = false
  for (const a of argv) {
    if (!sep && a === '--') { sep = true; continue }
    if (!sep && SWITCH_FLAGS.has(a)) {
      if (a === '--overwrite-profile') overwriteProfile = true
      else discard = true
      continue
    }
    passThrough.push(a)
  }
  return { discard, overwriteProfile, passThrough }
}

function suggest(name, names) {
  // Case-blind: names resolve exactly, so "WORK" should point at "work".
  const a = name.toLowerCase()
  let best = null, bestScore = Infinity
  for (const n of names) {
    const b = n.toLowerCase()
    let score = 0
    for (let i = 0; i < Math.max(a.length, b.length); i++) if (a[i] !== b[i]) score++
    if (score < bestScore) { bestScore = score; best = n }
  }
  return bestScore <= 2 ? best : null
}

function commandSpec(cmd) {
  if (cmd === 'ls') return getCommand('list')
  if (cmd === 'remove') return getCommand('rm')
  return getCommand(cmd)
}

function renderCommandHelp(spec) {
  const lines = [`Usage: ${spec.usage}`, '', spec.description]
  if (spec.arguments.length) {
    lines.push('', 'Arguments:')
    for (const a of spec.arguments) {
      lines.push(`  ${a.name}${a.required ? ' (required)' : ''}  ${a.description}`)
    }
  }
  if (spec.options.length) {
    lines.push('', 'Options:')
    for (const o of spec.options) lines.push(`  ${o.flags}  ${o.description}`)
  }
  if (spec.examples.length) {
    lines.push('', 'Examples:')
    for (const example of spec.examples) lines.push(`  ${example}`)
  }
  return lines.join('\n')
}

function helpCommand(name, { json = false } = {}) {
  if (!name) {
    if (json) {
      console.log(JSON.stringify({ version: 2, commands: COMMANDS, modes: MODES }, null, 2))
    } else {
      console.log(HELP)
    }
    return 0
  }

  const spec = commandSpec(name)
  if (!spec) {
    const detail = `unknown command: ${name}`
    if (json) {
      console.log(JSON.stringify({
        version: 2,
        error: 'unknown-command',
        detail,
        hint: 'run `agentswap help --json`',
      }, null, 2))
    } else {
      console.error(`${detail}\nrun \`agentswap help\` to list commands`)
    }
    return 1
  }

  if (json) {
    console.log(JSON.stringify({ version: 2, command: spec }, null, 2))
  } else {
    console.log(renderCommandHelp(spec))
  }
  return 0
}

function failUsage(flags, cmdName, detail = null) {
  const spec = getCommand(cmdName)
  const usage = spec?.usage ?? `agentswap ${cmdName}`
  if (flags.json) {
    console.log(JSON.stringify({
      version: 2,
      error: 'usage',
      ...(detail ? { detail } : {}),
      usage,
      hint: `run \`agentswap help ${cmdName} --json\` for the full schema`,
    }, null, 2))
  } else {
    console.error(`usage: ${usage}${detail ? `\n${detail}` : ''}`)
  }
  return 1
}

/** Bare `agentswap`: relaunch with the current active profile via the shared use() machine. */
async function relaunch(passThrough) {
  const state = readTrustedStateV2()
  const names = listProfileNames()
  if (!state?.activeProfile) {
    console.error('no active profile — run `agentswap <name>` first')
    if (names.length) console.error(`profiles: ${names.join(', ')}`)
    return 1
  }
  const r = await use(state.activeProfile)
  if (r.exitCode !== 0) { console.error(r.output); return r.exitCode }
  if (r.output) console.log(r.output)
  return launchAgent({ args: [...(r.launchArgs ?? []), ...passThrough], env: r.env })
}

/** `agentswap <name> [args…]`: sticky switch (idempotent) + launch. */
async function profileLaunch(name, opts, passThrough) {
  if (!profileExists(name)) {
    const s = suggest(name, listProfileNames())
    const command = suggest(name, [...RESERVED])
    const commandHint = command && RESERVED.has(command)
      ? `\ndid you mean the command: agentswap ${command}?`
      : ''
    console.error(`profile not found: ${name}${s ? `\ndid you mean: ${s}?` : ''}${commandHint}`)
    return 1
  }
  const r = await use(name, opts)
  if (r.exitCode !== 0) { console.error(r.output); return r.exitCode }
  if (r.output) console.log(r.output)
  return launchAgent({ args: [...(r.launchArgs ?? []), ...passThrough], env: r.env })
}

async function dispatch(cmd, rest) {
  const { positional, flags } = parseSubArgs(rest)
  if (flags.help && flags.json) {
    const spec = commandSpec(cmd)
    if (spec) {
      console.log(JSON.stringify({ version: 2, command: spec }, null, 2))
      return 0
    }
  }
  if (flags.help) { console.log(HELP); return 0 }

  if (cmd === 'run') {
    const { name, jsonCmd, saveOnExit, extra } = parseRun(rest)
    if (!name) return failUsage({ json: process.argv.includes('--json') }, 'run')
    const r = await run(name, { extraArgs: extra, jsonCmd, saveOnExit })
    if (r.output) console.log(r.output)
    return r.exitCode
  }

  switch (cmd) {
    case 'list':
    case 'ls':
      console.log(list({ json: !!flags.json }))
      return 0
    case 'current': {
      const r = current({ json: !!flags.json })
      console.log(r.output)
      return r.exitCode
    }
    case 'show': {
      if (!positional[0]) return failUsage(flags, 'show')
      const r = show(positional[0], { reveal: !!flags.reveal, json: !!flags.json })
      console.log(r.output)
      return r.exitCode
    }
    case 'use': {
      if (!positional[0]) return failUsage(flags, 'use')
      const r = await use(positional[0], {
        json: !!flags.json,
        discard: !!(flags.discard || flags.yes),
        overwriteProfile: !!flags['overwrite-profile'],
      })
      console.log(r.output)
      return r.exitCode
    }
    case 'save': {
      const r = await save({ json: !!flags.json, overwriteProfile: !!flags['overwrite-profile'] })
      console.log(r.output)
      return r.exitCode
    }
    case 'add': {
      const { positional: ap, values: av } = parseSubArgs(rest, ['platform'])
      if (!ap[0]) return failUsage(flags, 'add')
      // If --platform flag was given, av.platform contains the string; if given without value, flags.platform is true
      let platArg = null
      if (av.platform !== undefined) {
        platArg = av.platform
      } else if (flags.platform) {
        // Flag present but no value provided: pass empty string so validator rejects it with an error
        platArg = ''
      }
      const r = await add(ap[0], {
        fromCurrent: !!flags['from-current'],
        platform: platArg,
        json: !!flags.json,
      })
      console.log(r.output)
      return r.exitCode
    }
    case 'edit': {
      if (!positional[0]) return failUsage(flags, 'edit')
      const r = edit(positional[0])
      if (r.output) console.error(r.output)
      return r.exitCode
    }
    case 'rm':
    case 'remove': {
      if (!positional[0]) return failUsage(flags, 'rm')
      const r = await rm(positional[0], { force: !!flags.force, json: !!flags.json })
      console.log(r.output)
      return r.exitCode
    }
    case 'diff': {
      if (!positional[0]) return failUsage(flags, 'diff')
      const r = diff(positional[0], positional[1], { json: !!flags.json })
      console.log(r.output)
      return r.exitCode
    }
    case 'backup': {
      if (positional[0] === 'list' || positional[0] === undefined) {
        console.log(backupList({ json: !!flags.json }))
        return 0
      }
      return failUsage(flags, 'backup')
    }
    case 'restore': {
      if (!positional[0]) return failUsage(flags, 'restore')
      const r = await restore(positional[0], { yes: !!flags.yes, json: !!flags.json })
      console.log(r.output)
      return r.exitCode
    }
    case 'version': {
      const pkg = JSON.parse(await fsp.readFile(new URL('../package.json', import.meta.url), 'utf8'))
      console.log(pkg.version)
      return 0
    }
    case 'doctor': {
      const r = doctor({ json: !!flags.json })
      console.log(r.output)
      return r.exitCode
    }
    case 'skill': {
      if (positional[0] === 'install') {
        const r = skillInstall({ force: !!flags.force, json: !!flags.json })
        console.log(r.output)
        return r.exitCode
      }
      return failUsage(flags, 'skill')
    }
    case 'import': {
      if (!positional[0]) return failUsage(flags, 'import')
      const r = await importProfiles(positional[0], { apply: !!flags.apply, json: !!flags.json })
      console.log(r.output)
      return r.exitCode
    }
    case 'remote': {
      const { positional: rp, values } = parseSubArgs(rest, ['host', 'bin'])
      const r = await remote({
        sub: rp[0] ?? 'ls',
        name: rp[1] ?? null,
        host: values.host ?? null,
        bin: values.bin ?? null,
        json: !!flags.json,
      })
      console.log(r.output)
      return r.exitCode
    }
    case 'push': {
      const [name, ...remotes] = positional
      if (!name) return failUsage(flags, 'push')
      const r = await pushProfile(name, remotes, { json: !!flags.json, force: !!flags.force })
      console.log(r.output)
      return r.exitCode
    }
    case 'pull': {
      const [name, ...remotes] = positional
      if (!name) return failUsage(flags, 'pull')
      const r = await pullProfile(name, remotes, { json: !!flags.json, force: !!flags.force })
      console.log(r.output)
      return r.exitCode
    }
    case 'sync': {
      const r = await syncAll(positional, {
        json: !!flags.json,
        forcePush: !!flags['force-push'],
        forcePull: !!flags['force-pull'],
      })
      console.log(r.output)
      return r.exitCode
    }
    case '__sync': {
      const r = await syncAgent(positional[0], positional[1] ?? null)
      console.log(r.output)
      return r.exitCode
    }
    case 'web': {
      // --port takes a value (parseSubArgs treats flags as booleans).
      let port = 0
      const webRest = rest.filter((a, i) => {
        if (a === '--port') { port = parseInt(rest[i + 1], 10); return false }
        if (i > 0 && rest[i - 1] === '--port') return false
        return true
      })
      const { flags } = parseSubArgs(webRest)
      const r = await startWeb({ port: Number.isInteger(port) ? port : 0, open: !flags['no-open'] })
      if (r.output) console.log(r.output)
      return r.exitCode
    }
  }
  return 1
}

async function main() {
  const argv = process.argv.slice(2)
  const head = argv[0]

  if (head === 'help') {
    const { positional, flags } = parseSubArgs(argv.slice(1))
    return helpCommand(positional[0] ?? null, { json: !!flags.json })
  }
  if (head === '--help' || head === '-h') { console.log(HELP); return 0 }

  if (head === undefined) return relaunch([])
  if (head === '--') return relaunch(argv.slice(1))
  if (head.startsWith('-')) return relaunch(argv)

  if (RESERVED.has(head)) return dispatch(head, argv.slice(1))

  const { discard, overwriteProfile, passThrough } = parseProfileArgs(argv.slice(1))
  return profileLaunch(head, { discard, overwriteProfile }, passThrough)
}

// Set exitCode and let the event loop drain — process.exit() truncates large
// piped stdout (an 8 MiB show --json was observed emitting only 64 KiB).
main().then(code => { process.exitCode = code ?? 0 }).catch(e => {
  if (process.argv.includes('--json')) {
    console.log(JSON.stringify({
      version: 2,
      error: e?.code ?? 'unknown',
      detail: e?.message ?? String(e),
    }, null, 2))
    console.error(e?.message ?? String(e))
  } else if (e?.code === 'EBADPROFILENAME' || e?.code === 'EJOURNAL'
    || e?.code === 'ELOCKED' || e?.code === 'ELOCKDISPLACED'
    || e?.code === 'ELOCKFORMAT' || e?.code === 'ESSH'
    || e?.code === 'EREMOTE' || e?.code === 'EREMOTEBADJSON') {
    console.error(`agentswap: ${e.message}`)
  } else {
    console.error(e)
  }
  process.exitCode = 1
})
