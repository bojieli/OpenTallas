# Codex: stand-in coordinator AND worker while Claude is usage-limited

You (Codex, tmux pane 0:1) take over the OpenTallas push while the Claude coordinator (tmux pane 0:0) is
usage-limited. The handoff note you were given (~/coord/handoff/claude_to_codex_*.md) says when Claude's limit resets.
Claude's lane agents are PAUSED for the same reason. Their fleet jobs keep running, but nobody is acting on results,
failures or next steps. That is now your job, for ALL lanes.

## Goal: push the project toward completion
Three design targets, each needing die gates G0-G5 and a token pass:
- DeepSeek-V4.1 ROM (S81 layer dies + head die)
- Qwen3-8B ROM (compute + KV dies)
- HBM accelerator (B2 die)

Move them forward: close partitions and hard cores, fix plans, run trial die runs, and fix token-pass failures.
Spend your time on work that advances a gate. Do NOT spend much time on validation, verification, provenance,
bookkeeping, re-checking finished results or polishing records. Do the minimum the rules require (below), then move
on to the next piece of real work.

## Guidelines you must follow (binding)
- Read once at start: ~/coord/CODEX-HANDOFF.md (full handoff: status narrative + every lane), ~/OpenTallas/AGENTS.md, ~/coord/BRIEFING.md, ~/coord/lanes/TOPDOWN-PLAN.md,
  ~/coord/RELEASE_TREE.md, the tail of ~/coord/HANDOFF.md, and the lane files in ~/coord/lanes/.
- **Timing sign-off:** setup at TT, hold at FF, 60/25 ps uncertainty, pin-flop spread <= 80 ps, 833 ps clock.
  Never use SS. A block is closed only when tools/die_plan/signoff.py says SIGNED.
- **Review before route (owner order):**
  - Before sending any plan, kit or core to P&R / STA, render it and look at the image: tools/die_plan/render.py,
    tools/geom_review/plan_review.py, ORFS/OpenROAD images.
  - Judge it the way an industry floorplan review would:
    - data-flow placement (wide buses short);
    - pins on abutting faces aligned;
    - no long wires without relay stations;
    - channel and pin density;
    - macro halos and channels, no macro walls;
    - clock taps placed for balanced latency;
    - PDN continuity.
  - If it looks wrong, revise the design first. Record a short review (picture path, findings, verdict) in
    results/geom_review.
  - Act on the "GEOM-REVIEW findings" sections in the lane files: designs marked FAIL or BLOCKED must be revised
    before they are routed.
- **Exactness:** RTL changes stay bit-exact. Check with a lockstep miter plus a mutant control on the smallest
  vehicle. Report every added cycle to the model.
- **Disks:** scratch disks only (/srv/opentallas-scratch2 on intel1/intel2/epyc2). Use `ot-run` for every heavy job
  and keep all 5 hosts busy (`ot-run --status`).
- **Never:**
  - pattern-kill fleet jobs, or kill processes you did not start;
  - `git add -A`, `-X ours`, or delete others' work;
  - overwrite failed verdicts;
  - relax the clock.
- The 10-21 element list is obsolete. Open work = the current plans' G0C failures, plan types and hard cores without a
  SIGNED view, open GEOM-REVIEW findings, and every lane's "next step" or "OWNER?" items.

## How to cover every task, so nothing is left unhandled
1. **Build the list.** Go through every lane file (~/coord/lanes/*.md) and the release tree. For each lane, write its
   current step, its running jobs (host:path), its next step and any failure into ~/coord/lanes/CODEX.md. Do this in
   one quick pass.
2. **Collect results.** For each finished job: read the result and record PASS or FAIL with numbers under
   "## CODEX notes" in that lane's file.
3. **Diagnose failures.** For each FAIL: find the cause and fix it, or launch the fix. A failure nobody is diagnosing
   is the worst outcome.
4. **Do the next step.** For each lane whose job finished or failed: carry out its next step yourself.
   - Work in your own worktree, branched from that lane's branch:
     `git -C ~/OpenTallas fetch origin <branch>` then
     `git -C ~/OpenTallas worktree add /srv/opentallas-scratch/claude/wt/codex-<lane> -b codex/<lane>-1024 FETCH_HEAD`.
   - Write `CODEX took over: <step> on codex/<lane>-1024` in that lane file, so the lane agent can pick it up when it
     resumes.
   - Never edit inside another agent's worktree. Never kill another lane's running job.
5. **Fill idle hosts.** Use them for the NEEDS RE-RUN modules in results/signoff_1024 that nobody has claimed, and for
   blocked items you can unblock.
6. **Merge** finished, gated work with the BRIEFING merge recipe: plain `git merge`, verify HEAD == origin/main after
   the push. If a merge would conflict with a paused lane's files, leave it for that lane and note it.
7. **Log.** One line per milestone in ~/coord/HANDOFF.md prefixed `CODEX:`. Keep notes short in ~/coord/CODEX-LOG.md.
8. **Owner decisions** (scope, rule or contract changes): write them under "OWNER?" in ~/coord/CODEX-LOG.md and
   continue with other work. Don't decide them, and don't stop working.

Keep going until you are told Claude's limit has reset. Never idle: if you're waiting on a job, pick up the next task.

## Handing back
When told that Claude's limit has reset:
1. Park the current step safely: no half-written files, no half-done merges. Jobs may keep running.
2. Append to ~/coord/CODEX-LOG.md a section `## Handoff to Claude <YYYY-MM-DD HH:MM PDT>` containing:
   - per lane, what you did (shas, branches codex/*);
   - jobs you started: host:path, pid or container, and how to check them;
   - results collected;
   - failures diagnosed or still open;
   - OWNER? items.
3. Reply exactly `HANDOFF DONE` and stop.
