# EPYC1-RETIRE (OWNER 2026-10-26 23:3x "release EPYC1"; deadline DELETE 2026-10-27 05:25 PDT)

epyc1 = tender-ray, Cherry server 1042435, 84.32.71.203 (project 294737, team 216188).

## New hub = intel2 (tolerant-swine, 185.8.106.226) -- LIVE since 2026-10-26 23:46 PDT
Why intel2, not epyc2: epyc2 scratch2 has ~150-200 GB free vs intel2 2.26 TB; intel2 was already the documented, dry-run standby (OTRUN-HUB-RECOVERY.md).
- ot-run head: `ssh -o ControlPath=none intel2 ~/.local/bin/ot-run --mem G --threads N [--dir D] -- cmd` (rtx-pro ~/.local/bin/ot-run forwards to intel2). In its tables intel2 = "localhost", epyc1 = held worker. Tested 23:30: selftest choose PASS (29), tiny jobs RAN on epyc2/intel1/intel2 exit 0 (CHECKED).
- epyc1 held on BOTH heads since 23:27 (~/.config/ot-run/held_hosts). Old epyc1 head still serves its existing clients; do not submit there.
- merge.lock: `flock 9 9>~/coord/merge.lock` ON intel2 (`ssh intel2`); central merge checkout = intel2 ~/OpenTallas (origin = GitHub; intel2 pushes with the epyc1 GitHub key copied on the OWNER decision 23:4x). Merge worktrees: intel2:/srv/opentallas-scratch2/claude/wt/rmNN.
- coord hub mirror: intel2 ~/coord -> /srv/opentallas-scratch2/claude/hub-coord (worktree of ~/OpenTallas on coord/state), synced by hub-git-sync before each tick.
- Timers moved (epyc1 stopped+disabled 23:40, intel2 enabled 23:43): autopilot, stall-watch, release-task-watch, flow-canary, die-ci-nightly (die-ci-commit was already inactive). Drop-ins OT_HUB_NAME=intel2; autopilot/stall-watch/die-ci run pinned tools /srv/opentallas-scratch2/claude/epyc1-retire/pinned-211fb91d6e = main 278c7c4e85 + claude/epyc1-retire-hub-1026@211fb91d6e (hub name from OT_HUB_NAME; default epyc1 = unchanged). First intel2 autopilot tick 23:41 OK; stall-watch OK; flow-canary trigger OK (no submit, 2 live).
- autopilot state: 34 jobs whose kits were on epyc1 repointed to their verified copies (AP_KIT_MOVES.tsv); backup state.json.bak-epyc1-retire-*. Left: 356c4f07415a/41a5a6c0e052 (path-kv/astk/W1,W2 kits absent on epyc1), 3ffc2afa4c46 (ORPHAN, kit absent).
- rtx-pro: crontab lines (TASKS_STALE/STALLS rsync, autopilot mirror rsync, release cache push) -> intel2; otrun-hub-archive.sh pulls intel2; claude-autocontinue.py / make-codex-handoff.py status -> intel2 (backups *.bak-epyc1-retire-1026).
- epyc2/intel1 ~/.ssh/config `hub` alias -> intel2 (their keys added to intel2 authorized_keys); intel2 origin -> GitHub.
- NOT moved: epyc1 wt-reaper (intel2 runs its own wt-reaper timer already).

## Rescue / data (manifests in intel2:/srv/opentallas-scratch2/claude/epyc1-retire/)
- Git: 72 rescue/epyc1-* refs pushed (ls-remote verified); 86 dirty checkouts -> git-patches/ (126 MB). LIVE epyc1 worktrees to re-create on intel1/intel2: clock-kv-r14, codex-kv-pv-image-0733, path-s81-pd5-1026, head-rtl5-1026, head-rtl4-1026, rm27, path-hbm-r15-1026, qc-su-f4g-1026, rm26 (+ ~/OpenTallas, ~/coord). A FINAL patch pass is needed ~05:00.
- Closed evidence archived: AGIdock /archive/epyc1-retire-1026 (46,160 files, 3.30 GB, verified).
- Kits/live dirs: bulk copy to intel1/intel2 same paths (~1.5 TB, ~1 GB/s, ETA ~01:00) -> DATA-MANIFEST.tsv.

## Jobs on epyc1 (JOBS.tsv/JOBS.md in intel2:/srv/opentallas-scratch2/claude/epyc1-retire/, ETAs UNCHECKED)
- KILLED 23:29: GRT(B) path-s81-pd4-1026 signal-only (COORD-approved; GRT(A) untouched).
- RERUN now: flow-canary qwen_kvsys_core_278c7c4e8 (intel1 unit 3261682-1793084050) and hbm_a90c886f6 (intel1 unit 3360501-1793084188), same run paths; TOPK link_static LEC (intel2 unit 3427267-1793083036; may stall in the same ABC cone -> PATH-HBM picks a LEC strategy); rm26 SVCROWX miter/mut6/7/8 HEDGE on intel2 (units 3465812/3465642/3465821/3465822-1793083196), epyc1 original ETA ~02:30.
- LEAVE + COLLECT before 05:25: hold-coll-r1 coll_ftc route (ETA ~00:30-01:30, copy hold-coll-r1 to intel1 after it ends), rm26 epyc1 original (~02:30), docker dtrial-grt-647494 ft-m89-probe/hbm/base50 (no owner; collect grt.log ~02:00 or drop).
- NOT rerun (stuck/superseded, evidence in JOBS.tsv; die with epyc1 unless COORD objects): mu32_r13 probes, rq0_kvpool synth (31 h OPT_DFF loop), qx LEC r2, master-plan b1n6, tok-qk-b48 boot sims, docker kvhr2_fp_core_peer.
- Clients on epyc1 for units on other hosts (die at 05:25, units keep running, outputs local to workers; no open spill records): see JOBS.md. die-ci client 2d11h on intel2 (>48 h rule) -> COORD.
- Canary follow-up: when the intel1 canaries end, copy runs/<two>/canary.json + logs to intel2 flow-canary/runs (canary home); delete intel1 flow-canary.spillcopy-stale-20261026 and intel2 wt/rm26 partial tree after ROOT-MERGE-27 collects.

## Remaining steps (deadline 05:25)
1. JOBS: rerun on intel1/intel2 every epyc1 job that would run past 04:30 (JOBS.tsv); GRT(B) may be killed.
2. Finish/verify bulk copies (DATA-MANIFEST.tsv: files+bytes src=dst), final rsync pass of live dirs ~04:45.
3. ~05:00 final git rescue pass of the live epyc1 worktrees (new rescue refs + patches).
4. Final epyc1 ~/coord check (HEAD = origin, no dirty tracked files); copy ~/coord/autopilot/jobs/ logs again.
5. GET https://api.cherryservers.com/v1/servers/1042435 -> verify id/hostname tender-ray/IP 84.32.71.203; DELETE; GET -> 404.
6. After: drop epyc1 from intel2 ot-run/ot-sizes-sync HOSTS (`otrun-hub-retarget.py` --drop-old equivalent: remove "epyc1"), held_hosts line, ssh aliases (rtx-pro, intel2), fleet-viz host lists; HANDOFF line.
