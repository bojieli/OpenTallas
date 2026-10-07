import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Where agent skills live. Default: ~/.claude/skills (the agent's own skill
 * directory). Overridable with ACS_SKILLS_DIR.
 */
function skillsDir() {
  if (process.env.ACS_SKILLS_DIR) return path.resolve(process.env.ACS_SKILLS_DIR)
  return path.join(os.homedir(), '.claude', 'skills')
}

function listFiles(dir, prefix = '') {
  const out = []
  for (const e of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const rel = prefix ? path.join(prefix, e.name) : e.name
    if (e.isDirectory()) out.push(...listFiles(path.join(dir, e.name), rel))
    else out.push(rel)
  }
  return out
}

function treeDiff(a, b) {
  const fa = listFiles(a)
  const fb = listFiles(b)
  const all = new Set([...fa, ...fb])
  const differing = []
  for (const rel of [...all].sort()) {
    const pa = path.join(a, rel)
    const pb = path.join(b, rel)
    if (!fs.existsSync(pa) || !fs.existsSync(pb)) { differing.push(rel); continue }
    if (!fs.readFileSync(pa).equals(fs.readFileSync(pb))) differing.push(rel)
  }
  return differing
}

export function skillInstall({ force = false, json = false } = {}) {
  const here = path.dirname(fileURLToPath(import.meta.url))
  const src = path.resolve(here, '..', '..', 'skills', 'agentswap')
  if (!fs.existsSync(src)) {
    return { output: `bundled skill not found at ${src}`, exitCode: 1 }
  }

  const dest = path.join(skillsDir(), 'agentswap')
  const exists = fs.existsSync(dest)

  if (exists && !force) {
    const differing = treeDiff(src, dest)
    if (differing.length === 0) {
      if (json) return { output: JSON.stringify({ version: 2, installed: dest, upToDate: true }), exitCode: 0 }
      return { output: `agentswap skill already up to date at ${dest}`, exitCode: 0 }
    }
    if (json) {
      return { output: JSON.stringify({ version: 2, error: 'skill-differs', dest, differing }), exitCode: 1 }
    }
    return {
      output: `skill at ${dest} differs from the bundled version:\n` +
        differing.map(f => `  ${f}`).join('\n') + '\n' +
        `re-run with --force to overwrite`,
      exitCode: 1,
    }
  }

  fs.mkdirSync(path.dirname(dest), { recursive: true })
  if (exists) fs.rmSync(dest, { recursive: true, force: true })
  fs.cpSync(src, dest, { recursive: true })

  if (json) return { output: JSON.stringify({ version: 2, installed: dest }), exitCode: 0 }
  return { output: `installed agentswap skill → ${dest}`, exitCode: 0 }
}
