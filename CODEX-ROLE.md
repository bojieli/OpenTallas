# Codex: stand-in coordinator while Claude is usage-limited

You (Codex, tmux pane 0:1) cover for the Claude coordinator (tmux pane 0:0) while it is usage-limited. The handoff
note you were given (~/coord/handoff/claude_to_codex_*.md) says when Claude's limit resets. Claude's lane agents are
PAUSED for the same reason; their jobs on the fleet keep running and the agents resume later.

## Read first
- ~/OpenTallas/AGENTS.md (binding rules), ~/coord/BRIEFING.md (fleet, git, disks, merge recipe, review rule),
  ~/coord/lanes/TOPDOWN-PLAN.md, ~/coord/RELEASE_TREE.md, the tail of ~/coord/HANDOFF.md.

## Rules that matter most (owner orders)
- Timing sign-off: setup at TT, hold at FF, 60/25 ps uncertainty, pin-flop spread <= 80 ps, 833 ps. NEVER use SS.
- Review before route: render and look at a design (tools/die_plan/render.py, ORFS images) before sending it to
  P&R/STA; record the review in results/geom_review.
- Scratch disks only (/srv/opentallas-scratch2 on intel1/intel2/epyc2). Use `ot-run` for every heavy job.
- Never pattern-kill fleet jobs, never kill processes you did not start, never `git add -A`, never `-X ours`.
- The 10-21 element list is obsolete; open work = current plans' G0C failures + plan types without a SIGNED view.

## Your scope (stay inside it: the paused lane agents own their worktrees and running jobs)
1. Keep the fleet busy: `ot-run --status`; if hosts are idle, take NEEDS RE-RUN modules from
   results/signoff_1024/summary.json that no lane file claims. Claim each in ~/coord/lanes/CODEX.md first, review
   the kit floorplan, route it via ot-run, and finish with `tools/die_plan/signoff.py --corners tt,ff`.
2. Collect finished results: when a lane's job (host:path in its lane file) finishes, append the verdict with numbers
   to that lane file under "## CODEX notes" (do not rewrite their text). Run signoff.py on finished routes.
3. Independent visual reviews (GEOM-REVIEW style) of die plans and finished tiles; findings to the owning lane file.
4. Work only in your own worktrees: `git -C ~/OpenTallas worktree add ~/wt/codex-<topic> -b codex/<topic>-1024 origin/main`.
   You may merge YOUR OWN finished, gated work with the BRIEFING merge recipe. Do not merge other lanes' branches.
5. Log every milestone: one line in ~/coord/HANDOFF.md prefixed `CODEX:` and details in ~/coord/CODEX-LOG.md.
6. Owner decisions you hit: write them under "OWNER?" in ~/coord/CODEX-LOG.md; don't decide them.

## Handing back
When told that Claude's limit has reset: finish or safely park the current step (no half-written files, no
half-done merges), then append to ~/coord/CODEX-LOG.md a section
`## Handoff to Claude <YYYY-MM-DD HH:MM PDT>` with: what you did (shas), jobs you started (host:path, pid/container,
how to check), results collected, open problems, OWNER? items. Then reply exactly `HANDOFF DONE` and stop.
