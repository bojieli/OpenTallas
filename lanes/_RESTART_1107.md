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

# Second restart, 11-07 13:0x (limit about 11:50-13:00; Codex covered 12:09-13:03)

Every successor, in order:
1. `cd /` first in every shell command. Read lanes/_CORE_LANE_RULES.md in full, especially the last three sections.
2. Read the Handoff to Claude sections of CODEX-LOG.md from line 11549 on, for your scope. Read handoff/codex_takeover_20261107_1209_checkpoint.md and handoff/codex_fleet_ops_20261107_1209.md, plus your die's lanes/CODEX-*-1209.md or other CODEX-* lane file.
3. Read your predecessor's posts in lanes/COORD-REVIEW-QUEUE.md (grep its name for today), the CODEX-* posts for your die, and COORD's 13:0x RULING.

Rules:
- COLLECT first. Codex's forms, branches and kits are now yours. Never rebuild, stop or duplicate a healthy job. Keep Codex's guards: HOLD_ROUTE / ROUTE_STOP files, no RAM guard re-arm, factor 1 on epyc4/5/6.
- OWNER: pin cycles on hard cores, no P&R retries, failed form = view geometry and redesign. Late-stage fix on real near misses only (setup/hold <=30 ps worse, <=100 endpoints, <=20 slew nets, DRC <50, cause local), one iteration, never on large misses. QC NL ecow3 exception used; HEAD eco_dh80 stays stopped. rootctl_e1 second ECO, lane_c second ECO and n4 vCF2a exception are NOT granted.
- Conservative form: <=150k cells, registered faces, fanout <=8, util <=0.40 cores / <=0.35 types, signals <=M6, memories on edge with a channel, feedthrough flops <=450 um, +1 pin cycle for setup reach, pipelined reset. Only sign-off blocks; pre-build checks are advisory. Batch by class. View place/GRT/route renders (Read the PNG) and post "SMELLS: ..." using the 10-item checklist. Do not wait for merges before rebuilding; re-sign on a main tag after merge.
- Critical list uses the direct path: on intel2 `ot-run --direct` (or ot-run-direct), rows in lanes/NEAR-CLOSE.tsv. Direct jobs are charged request minus use: declare a truthful request, read /usr/local/bin/ot-direct-pending per host before choosing, stop your own bookings whose answer is no longer needed. No admission code changes.
- Disks: never new work on intel2 scratch2 (hub) or intel2 root. Tight today: epyc2 root (guard 95%), epyc5 scratch2, epyc6 root. Read df first; intel1 scratch2 and epyc4 scratch3 had the most room. Source clones: sparse, on a non-hub disk, removed when done. Clean up after each job.
- First STATE within 30 min: what is alive, what finished, next step. Then results with [CHECKED host path]. Measured versus inferred kept apart; correct your own errors in the queue. Say "signed off". Hold gate FF >= 0; NEEDS_PARENT counts. Do not end your turn while your jobs are pending: keep working from Monitor or background-bash events. Foreground sleep is blocked. End with PARKED naming exact next steps.
- Remote calls: `timeout N ssh -n -o ControlPath=none -o ConnectTimeout=10 host ...`; `python3 -I`; timestamps via $(date). Never print keys. Never run git in localhost /home/ubuntu/OpenTallas or in intel2:/home/ubuntu/OpenTallas (read-only GIT_OPTIONAL_LOCKS=0 only). Never touch ~/.codex or ~/.claude. Kill only exact PIDs or containers, your own or named by a ruling; never pkill -f. No git add -A, no force-push, no stash, no git reset in ~/coord. Coord files only via timeout 280 ~/coord/bin/coord-commit.sh "msg" files; verify on origin/coord/state. Commits end with Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>. Post READY with hub branch@sha; main changes only through ROOT-MERGE-49. Plan events need a count dry run. Owner questions go to COORD in the queue, not to the owner. Before SendMessage grep lanes/agent_ids.tsv. Deletion only under the prune rules with a manifest, and only in AUTOCLEAN lanes or your own run dirs.

# Third restart, 11-07 17:1x (limit 15:51-17:05; Codex covered, handback 17:04)

Every successor, in order:
1. `cd /` first in every shell command. Read lanes/_CORE_LANE_RULES.md, and the "Second restart" section above (its rules all still apply).
2. Read handoff/codex_to_claude_20261107_1704.md in full, the CODEX-LOG "Handoff to Claude 2026-11-07 17:04" section, and your die's Codex 1551 lane or checkpoint file named in that handback (for example lanes/CODEX-QC-1551.md, handoff/codex_kv_1551_checkpoint_20261107.md, handoff/codex_s81_20261107_1705.md, lanes/CODEX-S81-TYPES-1551.md, lanes/CODEX-SVC-HARDENING-1209.md, handoff/codex_token_to_claude_20261107_1551_back.md, handoff/codex_fleet_ops_20261107_1551.md).
3. Read your predecessor's posts today in lanes/COORD-REVIEW-QUEUE.md and COORD's RULING at 17:1x.
Rules: COLLECT first; Codex's units, branches and kits are yours; never stop, rebuild or duplicate a healthy job. Codex parked new work at 17:04, so its "next" items are now yours to start. Disks are tight (epyc6 root, intel1 scratch, epyc5 scratch2): read df and the ot-run status first; epyc2, epyc4 and localhost-admitted ot-run have room. A frontend NOTRUN after an actual admission can be false; check the unit before relaunching anything.
