# Restart after the 11-07 limit (Codex covered 06:15-08:02; written 2026-11-07 08:04 PST)

Every successor, in order:
1. Read lanes/_CORE_LANE_RULES.md in full, especially the last three sections.
2. Read the Handoff to Claude sections of CODEX-LOG.md from line 11129 on, for your scope, plus handoff/codex_takeover_20261107_0615_checkpoint.md, handoff/codex_fleet_ops_20261107_0615_checkpoint.md and handoff/codex_s81_to_claude_20261107_0801.md where relevant.
3. Read your predecessor's posts in lanes/COORD-REVIEW-QUEUE.md (grep its name for today) and the CODEX-* posts for your die.

Rules:
- COLLECT first. Codex forms and kits are now yours to read and continue. Never rebuild or stop a healthy job. Do not duplicate one. Codex stopped launching at 08:02; healthy jobs stayed running.
- Keep Codex's guards: HOLD_ROUTE / ROUTE_STOP files, no RAM guard re-arm, factor 1 on epyc4/5/6.
- OWNER 05:1x: pin cycles on hard cores, no P&R retries, failed form = view geometry and redesign. OWNER 05:3x: late-stage fix on real near misses only, one iteration, never on large misses. Exception, QC NL ecow3 only, once. HEAD TX eco_dh80 stays stopped.
- Critical list uses the direct path: on intel2, ot-run-direct --direct, rows in lanes/NEAR-CLOSE.tsv.
- New work goes on epyc2 scratch3, intel1 scratch2, epyc4 scratch3. Not epyc4/epyc5/epyc6 scratch2, unless AUTOCLEAN-3 posts room.
- Pre-merge branches may be built from at once; re-sign on a main tag after merge.
- First STATE within 30 min: what is alive, what finished, next step. Then post results with [CHECKED host path]. Say "signed off". Be short-lived: finish scope, or PARKED with the exact next step.
- Every shell command starts with cd /. Never git in localhost /home/ubuntu/OpenTallas. Never print keys. Kill only exact PIDs. No git add -A, no force-push, no stash, no git reset in ~/coord. Coord files only via timeout 280 ~/coord/bin/coord-commit.sh "msg" files; verify on origin/coord/state. Commits end with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". Do not touch ~/.codex.
- Before SendMessage grep lanes/agent_ids.tsv.
