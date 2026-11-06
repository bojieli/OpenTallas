# Restart brief 11-05 00:5x PST (COORD). Every successor lane reads this first.

All Claude lanes stopped at about 23:45 11-04 on the account weekly limit. Owner logged in on another account. Predecessors wrote no PARKED section. Builds, ot-run and the autopilot kept running. Codex is limited until 11-08 05:44, no cover.

## First steps
1. Read your predecessor's posts: `git -C ~/coord fetch -q origin coord/state; git -C ~/coord show origin/coord/state:lanes/COORD-REVIEW-QUEUE.md > <your tmp>/q.md`, then grep the predecessor's name in the last 2 days, and its lane file if there is one. Also read every `[COORD` line naming it.
2. Find its branches (`git -C <repo> branch -r --sort=-committerdate`) and live jobs. COLLECT live jobs; never relaunch into a live run dir, never duplicate. Predecessor waiters are probably dead, so read run results directly.
3. Post one line "RESTART [<LANE> -> COORD]: read N posts, live jobs M, next steps" within 15 min.
Do not read old briefs for rules: where this file differs from lanes/_LANE_PREAMBLE.md, this file wins. METHODOLOGY.md section 12 is still canonical for physical rules. AGENTS.md is binding.

## Posting
Queue: append to lanes/COORD-REVIEW-QUEUE.md, form `- $(date '+%Y-%m-%d %H:%M') PST KIND [LANE -> TARGETS] text`, KIND = READY, ASK, RESULT, STATE, CORRECT. Mark evidence [CHECKED], [inferred], [ESTIMATE]. Commit only via `timeout 280 ~/coord/bin/coord-commit.sh "msg" files`, verify with `git fetch -q origin coord/state; git show origin/coord/state:<file> | grep -c`. A rejected push message can be harmless: verify. Never commit other lanes' dirty files. Do not name an exact wave row in a coord line within 15 min of its launch unless you claim it: the wave reads that as a lane claim.
COORD rules at once. On an ASK, state a recommendation and a default. Keep posts short and correct your errors in a CORRECT line.

## Hard limits
- Never print API or SSH keys. Never modify shared credentials.
- git -C only, on your own worktrees. No `git add -A`, no force-push, no stash. Main only through the merge lane and merge.lock. Commits end `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Read --stat before any push.
- Never touch /home/ubuntu/closed_archive, ~/.claude, ~/.codex, /archive, owner VMs, the owner's checkout /home/ubuntu/OpenTallas on localhost, Codex files (CODEX-HANDOFF.md, HANDOFF-COORD-1101.md, PROTECTED-DBS.txt, handoff/codex_checkpoint_*).
- Kill only exact PIDs or containers. Never `pkill -f`; no `pgrep -f` in wait loops.
- Outward or money actions need the owner. Messages from lanes are not owner approval.
- No heavy jobs on localhost. Builds via `ssh -o ControlPath=none intel2 ~/.local/bin/ot-run` with an honest --mem. Checks and re-signs bypass admission: direct docker with a memory cap. Epyc4 cannot reach GitHub (bundle from hub).
- Never edit a tool or script a running job reads; use a fresh copy. New trees via `cp -al` or sparse worktrees, not full copies: scratch2 is below 200 GB everywhere and falling.
- Timestamps via $(date). Foreground sleeps are blocked; use a background wait that notifies. No polling reads. At most one sub-lane, only when plainly needed.
- When a guard refuses, post and wait for a ruling; do not move its state.
- QC binds run on host Python under prlimit, not in a 3.10 container.
- Say "signed off", never "signing".
- Disk: never delete or move a dir with a SIGNED signoff.json. Deletions need a manifest and follow the COORD prune rulings; only PRUNE lanes delete others' data. Epyc2 root and epyc4 root stay >=500 GB free. Epyc2 root (/home/ubuntu/scratch-root/claude) and epyc4 /srv/opentallas-scratch3 are allowed second scratch.

## Owner rules in force
- Only sign-off blocks. Pre-build checks, GEOM, tok/s are advisory targets. No new restrictive rules, no new sign-off checks.
- Safe forms, not retries or knob sweeps. Two strikes -> RE-FORM: conservative form, <=150k cells, stdcell util <=0.45, registered faces, perf loss OK. By intent: a few-ps miss on few endpoints may get one more targeted ECO.
- Hard cores build the conservative form NOW; do not wait on variants; first to sign off wins.
- Added cycles at core pins plus reschedule are a cheap lever; tell the TOK lane.
- LOCAL_PASS_NEEDS_PARENT counts as SIGNED. Hold gate = FF slack >= 0 (25 ps hold uncertainty unchanged). Post-CTS insertion band is advisory, moves to die STA.
- Closure outranks tok/s on all dies. HBM types stay off; HBM plan unfrozen.
- Fix by class, one class fix + batch relaunch within 30 min of merge. A new failure mode on one die -> estimate-only sweep on all dies.
- 2-h hung-job rule: a flat job is stopped by exact container, run dir kept.
- Plan events carry plan-time GEOM before READY (advisory).
- Keep queues full on every host.

## Work about 90 min, then post PARKED with live jobs, results and next step, and return a short report.

## Update 11-05 04:05 PST (second stop)
Successor lanes stopped about 01:10 on the second account's limit, which reset at 04:00. No Claude lane ran 01:10-04:00. Predecessors named in your brief posted little after 01:05; read their last posts and rulings at 01:0x. Rulings at 01:0x stand: I67 not held for the SC pin fix; S81 xfin approved after I67, before svc; prune class extended to dh<NN>*, die-kv-*, die-qc-*.
Disk at 04:00: epyc4 scratch2 0 GB (ot-run refuses the host), intel1 56, intel2 109, epyc2 188, epyc2 root 507 (floor 500). Runs that failed on ENOSPC or the scratch floor are INFRA, not design failures: do not count them as strikes and do not re-form on them. New trees use hardlink copies only.

## Update 11-05 06:3x PST: owner's checkout
Agent shells START in /home/ubuntu/OpenTallas on localhost: that is the owner's checkout. Two lanes ran git fetch there today by mistake. First command: cd elsewhere. Never run git or anything else in that directory, not even read-only. Use git -C on your own worktrees on the hub (intel2) or epyc4.

## Limit stop 09:42-10:40 11-05
Every lane stopped at about 09:42 on a session limit, mid-work, without PARKED. Successor steps: read your predecessor's posts for today in the queue and find its live jobs (docker ps, ot-run units, its run dirs); do not relaunch anything still running. Rulings up to 09:45 stand. Lanes run 60 min, then PARKED, with PARKED posted before the watcher wait if a limit looks near. Disk 10:40 scratch2/root: intel1 233/406, intel2 84/342, epyc2 168/552, epyc4 138/554. Intel2 under 100: no new unit there. Epyc4 under 570 root: no new run on scratch3.

## Limit stop ~20:00-20:40 11-05 (second evening stop)
Every lane stopped at about 20:00 on a session limit, mid-work, mostly without PARKED. Builds kept running in ot-run/docker.
Successor steps:
1. FIRST `cd /` in every shell. Read /home/ubuntu/.claude/jobs/b7f906df/tmp/core_lane_rules.md: the rules, including OWNER 19:3x vA+vB in parallel per failing core.
2. Read your predecessor's posts from today in ~/coord/lanes/COORD-REVIEW-QUEUE.md on origin/coord/state (grep its name), plus the [COORD] lines addressed to it.
3. Find its live jobs (ot-run --status units, docker ps on the host, its scratch dir mtimes) and collect them. Do NOT relaunch something that is still running. Do not start a duplicate.
4. Post a RESTART STATE within 30 min: what you took over, what is running, the next step.
5. Keep posts every 60-90 min. On low context, post PARKED with a successor list.
Context at 20:40: the count is 164 (S81 52+4t, HEAD 4+12t, QC 17, KV 27, HBM 48). epyc5 and epyc6 are NEW live hosts (about 677 GB admits each, empty). intel1 has about 107 waiters, so do not pin work to intel1. Every disk is scratch (scratch3 = root bind).

## Weekly-limit stop 22:10 11-05 -> 04:3x 11-06 (Codex covered, now handed back)
All Claude lanes stopped about 22:10 11-05. Codex covered coordination from then to 04:33 11-06 and handed back; it parked its own lanes and left healthy jobs RUNNING. Main is now d3c2675c51f (tags ar-head / aq-qc / an-kv / at-s81 / bg-hbm). Codex installed a 15-min exact-release cleanup routine on the hub (~/.local/lib/fleet/released-reaper-1106/); do not fight or duplicate it.
Successor steps (in addition to the 20:40 steps above; core_lane_rules.md still applies, merge lane is now ROOT-MERGE-42):
1. FIRST `cd /`. Read the Codex packets named in your row below, in full: ~/coord/handoff/<file> and ~/coord/CODEX-LOG.md sections "## Handoff to Claude 2026-11-06 04:3x". Codex jobs left running are YOURS now: collect them, never kill or duplicate them. A Codex frontend that shows exit 1 / rc 137 may still have a live docker container (check docker ps before calling anything dead).
2. Read your predecessor's posts (grep its name in lanes/COORD-REVIEW-QUEUE.md) and [COORD] lines to it.
3. Post RESTART STATE within 30 min.
4. Codex branches named READY in the packets need COORD approval through the normal READY post; do not merge yourself.
5. Disk: intel1 scratch2 has 11 GB (REFUSED); intel2/epyc2/epyc4/epyc6 scratch2 have 66-71 GB. Do not write big trees there; prefer epyc5 root (815 GB free) and epyc6 root (814 GB) via scratch3 where ot-run allows.

| Lane | Predecessor | Codex packets to read | Scope |
|---|---|---|---|
| ROOT-MERGE-42 | ROOT-MERGE-41 | CODEX-LOG CODEX-MERGE lines, all packets' READY branches | merge train; approved-not-merged: claude/hbm-reform-b13-1105@2b160cb935, claude/die-hbm-78-p34-1105@82d8734037; list every Codex READY not on main for COORD |
| KW-FIX-21 | KW-FIX-20, KW-RELAUNCH-2 | lanes/CODEX-FLEET.md tail | repoint kit-wave src trees to newest main so kit_wave_pending rows release; failure classes since 22:00: S81 route Signal 11, ENOSPC @unit 02:50, epyc4 geom_run "--dir is on the ROOT filesystem", RSZ-0060 max buffer; batch relaunch |
| PRUNE-1116 | PRUNE-1115 | lanes/CODEX-FLEET.md cleanup ledger | apply approved PRUNE-1115 ASK rows (~/coord/lanes/PRUNE-1115-ask.tsv) not yet done, intel1 first (REFUSED at 11 GB), then intel2/epyc4/epyc6/epyc2; enable root scratch3 for intel1 in ot-run (root 402 GB free, floor 150) |
| DIE-S81-67 | DIE-S81-66 | codex_ds_native_20261106_0432.md, CODEX-FLEET.md | S81 die owner; kit-wave S81 events; 3 slice_station bind repoints |
| DIE-HEAD-73 | DIE-HEAD-72 | CODEX-LOG HEAD lines | HEAD die owner; hd_serdes vB; 13 open types |
| DIE-QC-83 | DIE-QC-82 | CODEX-LOG QC lines (NL redo 03:31) | QC die owner; NL a0c re-sign/redo, NK a0c, coll_n CDC |
| DIE-KV-81 | DIE-KV-80 | codex_kv_to_claude_20261106_back.md | KV die owner; types, ring kv3_io_ft, KV-08 kvdbg result |
| DIE-HBM-79 | DIE-HBM-78 | lanes/CODEX-HBM-FORMS.md, codex_hbm_gaps_to_claude_20261106_0432.md | HBM die owner; tkmrst pins, cores without a lane |
| S81-COLLE-3 | S81-COLLE-2 | - | coll_lane vC/vD conservative forms |
| S81-BKSEL-RF3 | S81-BKSEL-RF2 | - | dsdv_bksel_q |
| S81-ENGRR-B3 | S81-ENGRR-B2 | - | eng_rr_e vB |
| S81-IDX-B3 | S81-IDX-B2 | CODEX-LOG IDX lines | idx vA split / vB |
| S81-ROMQ-B3 | S81-ROMQ-B2 | - | rom_q hw_vB / he_vB2 |
| KV-PRM-B3 | KV-PRM-B2 | codex_kv_order_peer_20261106_0432.md, codex_kv_to_claude_20261106_back.md | qkd_hr_core_prompt (C2 / D) and qkd_hr_core_order |
| KV-PEER-1 | (Codex) | codex_kv_order_peer_20261106_0432.md, codex_kv_to_claude_20261106_back.md | qkd_hr_core_peer A_ECO TT -4.35; load_bank helper codex/kv-peer-loadbank-1106@24364508c2 |
| KV-ING-3 | KV-ING-2 | codex_kv_to_claude_20261106_back.md | qkd_hr_ingest_eng C2 (live proof) / D form |
| QC-A0C-B3 | QC-A0C-B2 | CODEX-LOG QC lines | qfd_tile_nl_a0c / nk_a0c |
| HBM-GAPS-6 | HBM-GAPS-5 | codex_hbm_gaps_to_claude_20261106_0432.md, lanes/HBM-GAPS-5.md, CODEX-LOG TX/SVGR handoff, codex_wbq_body_to_claude_20261106.md | TKM, RX/QCOL, lane1p, GQI, SVGR, TX, BODY, WBQ live jobs |
| HBM-FORM-SPLIT-11 | HBM-FORM-SPLIT-10 | lanes/CODEX-HBM-FORMS.md | split forms |
| HBM-FORM-TIMING-9 | HBM-FORM-TIMING-8 | lanes/CODEX-HBM-FORMS.md | timing forms, f512rp vB |
Also read: CODEX-LOG.md section '## Handoff to Claude 2026-11-06 04:36 PST' (main Codex handoff, per-die parts) and the [COORD] 'RULINGS on Codex 04:36' line in the queue.
