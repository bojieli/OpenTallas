# KW-FIX-46 lane handoff (refreshed 2026-11-12 13:50 PST)

## 0 State at 11:56 (supersedes older lines below)
- LIVE runtime /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot = main 9c8ff818ef19 tools/autopilot + host-gap patch; kit_wave.py md5 acea0a8097c8. Deployed 11:43 under kit_wave.lock (COORD approved). Full pre-deploy backup: rt/tools/autopilot.bak-kw46-predeploy-1112 (roll back = rsync it back under the lock). Dry decision diff old vs new: 0 different of 9.
- Branch claude/kw-fix-46-live-kitwave-1112 @ edf6623be211 LANDED in main (9c8ff818ef19).
- Branch claude/kw-fix-46-hostgap-1112 @ b8e6e2ed9a61 (pushed): collect-time INFRA auto-class (FLOW 'tool input file missing'/KIT_NOT_SELF_CONTAINED on a host in st[src_incomplete_last] -> INFRA, log KIT-WAVE HOST-GAP). Live already; needs ROOT-MERGE-60 merge.
- ot-run: fleet/kw43-rootreal/ot-run rebased 09:32 = byte copy of main backend (backup ot-run.bak-kw46-rebase-1112). kw44-seal-ap/sealed-{wave,ap}.json sealed_backend -> fleet/isolate-1-kw46m-590d7d62e7/ot-run (backups *.json.bak-kw46-1112). DONE, nothing pending.
- Fleet fill 11:5x: wave capacity is not the limit (inflight 8/300, queue_fill on). Picks are few because rows are held by rulings (QC/S81/KV WAIT-FORM, S81 STA-2204 FLOW no-retry x11, HBM WAIT-CHILD on ot_pdie_serdes_rx_bm3_rest). Posted to COORD 11:5x.
- 12:19 LIVE form-wait fix: kit_wave.py md5 e80c38ab368f (backup kit_wave.py.bak-kw46-formwait-1112); branch claude/kw-fix-46-formwait-1112 @ 0b0d2b5425fb (hub) = hostgap + verdict_attempt_dir (WAIT-FORM finds the rated attempt in arm/sibling dirs). READY for ROOT-MERGE-60. Worktree /srv/opentallas-scratch2/claude/wt/kw-fix-46-wf. Open: q_su21@3 unit kw-hbm-qsu21-3-13699 runs the BAD form, stop only on COORD word.
- 12:3x STA2204-1: main gp_noconverge_gate.tcl (md5 8739596e35f3) in bsrc4_r12ng on epyc8/epyc9/intel1 (was hardlinked, replaced by mv, .bak-kw46-sta2204-1112 kept); retry 6 S81 rows committed 824ed7ca091, all launched 12:47. Next: watch them through place 3_4.
- 13:4x: autopilot.py LIVE md5 6f10f7602534 (backup autopilot.py.bak-kw46-oom-1112): MAX_OOM_RESUBMITS=2 + watchdog STOP attribution by sealed ot-job dir. Re-enqueued hbm PHY_NC 2731c12447d5 a2 (--mem 48) and q_mcb_ne 58ab1566e512 a3 (--mem 108) at 13:40. q_su21@3 record CANCELLED/WAIT-FORM.
- Branch claude/kw-fix-46-formwait-1112 @ 66d6df6af0ac READY (2 commits on main 59f6e468468a): OOM/watchdog + resign.py ff_vclk_args (STA2204-1 bound-ff replay, --source-record). watchdog.py and resign.py/auto_resign.py go live only via the merge. pytest venv: /srv/opentallas-scratch2/claude/rm-ai-1031/venv/bin/python.
- Watching 6 S81 STA2204 rows to place 3_4: /tmp/kw46_watch6.sh on intel2 -> /tmp/kw46_watch6.final (attempts t2 27, t4 17, t13 26, t15cl 10, t16 18, kv512 34 after RESTAGE). Then report and stop.
- Stopped per COORD 11:41. Next: ROOT-MERGE-60 merge of the hostgap branch; a class fix for s81 resize.tcl STA-2204 if COORD assigns it.

## 1 Scope
Owner of the kit-wave autopilot code: hub runtime kit_wave.py, ot-run admission, autoclean/reaper keep lists. Fix FAIL classes once per class, hold and retry rows in ~/coord/autopilot/kit_wave.json. The sidecar-coverage preflight now belongs to GEN-CLASS-1 (COORD 11-12), not this lane.

## 2 Worktrees (all on intel2)
- /srv/opentallas-scratch2/claude/wt/kw-fix-46, branch claude/kw-fix-46-live-kitwave-1112, HEAD 3ed2a56b106 (pushed, clean; + src import-closure probe, test_kit_wave_import_probe.py). Holds the live runtime hunks merged onto main, plus: stale place-service set-aside, held_stop_reason (stopped held rows go to WAIT-FORM), sidecar_preflight, and VISUAL-QUEUE stale filter (visual_gate_since). New tests: test_kit_wave_held_stop.py, test_kit_wave_sidecar_preflight.py, test_kit_wave_visual_stale.py; test_kit_wave_flow_tag.py was fixed.
- /srv/opentallas-scratch2/claude/wt/kw-fix-46-rac, branch claude/kw-fix-46-read-at-commit-1112, HEAD f4224a7f4900 (pushed, clean). gen_core_kit_hbm.fetch() reads REPO/.kw_at_commit/<commit>/<file> when git show fails (a wave src is a plain copy). Test: physical/die_plan/hbm_arch_cores/test_fetch_at_commit_store.py.
- Base for test comparison: /srv/opentallas-scratch2/claude/wt/kw-fix-46-base (origin/main).
- LIVE runtime: /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot/kit_wave.py, md5 9ed07addba1d. It is patched in place. Backups are kit_wave.py.bak-kw46-{stalesvc,heldstop,sidecar,vq,imports}-1112. The runtime lags main: it lacks FAILFAST-1 stop_cancelled_rows, type_overlay, bind_preflight and plan_sha_mismatch. Do NOT deploy main's tools/autopilot without COORD approval.

## 3 Running jobs
- intel2 nohup /tmp/kw46_all_tests.sh -> /tmp/kw46_all_tests.log. Runs the unittest comparison of base vs branch. Check: `pgrep -f kw46_all_tests.sh`, then diff the per-file lines (format: "<wt> <file> Ran.. OK/FAILED").
- The ot-run / autopilot ticks are the normal systemd user units, not mine.

## 4 Watchers/scripts
- Scratch helpers: localhost /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/kw46/. post.sh appends to the queue and commits. Also patch_*.py (runtime patches), retry_*.py (retry edits under kit_wave.lock) and at_commit.py (materialises read_at_commit files). intel2 copies are at /tmp/kw46_*.
- READ_AT_COMMIT store: intel2 /srv/opentallas-scratch2/claude/kw46/at_commit{,.tgz} (368 files). Deployed to REPO/.kw_at_commit in kw45/src_hbm_{main,rd1_main}_9fc09952cd_q0g_p18 and src_hbm_trainN_aaede on epyc2/7/8/9. Those trees' gen_core_kit_hbm.py is patched too.
- No Monitor armed now. Re-arm an hourly FAIL-class scan of ~/coord/autopilot/log.txt ("KIT-WAVE FAIL").

## 5 Results not yet posted
- hbm/ot_svgr_top: the cause is the READ_AT_COMMIT recipe (recipes_b2 read_at_commit=True, commit 9410cf281442). It runs `git show` in a plain-copy src, which always fails. Fixed via the store plus the fetch fallback. Retry ot_svgr_top@1 is in config (coord-commit had nothing to stage because the tick already committed the file). 4 recipe files are still MISS at their commits (hnx_rp3h_xs @4d6f5439, ot_hbm_idx_score_hcol_h0_ra @1add0934 and 2 more; see intel2 /srv/opentallas-scratch2/claude/kw46/at_commit.log).
- vp4_banks_cp: the row is ot_hgi_dma_back_static_vp4_banks_cp@4, SUPERSEDED-KEEP by hold_items (DIE-HBM-66 form dma13). It was not relaunched, by design.
- ot-run --status 06:4x: sane. Hosts are epyc2/intel1/localhost/epyc4/epyc7/epyc8/epyc9; epyc5 is gone. epyc2 has 69 waiters with 212 GB free on scratch.
- S81 gen_args --clock-landing = bsrc4_main/.../landed_sidecar_h2_psplit_all.json, sha 574a1db01f52 (identical in bsrc4_r12ng; checked on epyc8/9).

## 6 Next steps (in order)
1. Read /tmp/kw46_all_tests.log. If the branch has no new FAILED relative to base, post READY for claude/kw-fix-46-live-kitwave-1112 (4e1726ea9342) and claude/kw-fix-46-read-at-commit-1112 (f4224a7f4900) with the test table. If a test regressed, fix it on the branch first.
2. Watch the ot_svgr_top@1 relaunch (`grep ot_svgr_top ~/coord/autopilot/log.txt | tail`). If gen passes, post RESULT. If it fails with a new "missing" message, add the file to the store and rerun at_commit.py.
3. epyc4 (07:30 URGENT): EVERY die src there is a self-loop (scratch2/claude/kw45 -> scratch3/claude/kw45, entries link to themselves), qc_s28 included; FLEET-2 restore IS live (10 rsync; my 07:30 no-rsync claim was a bad pgrep pattern: pgrep ERE, use "rsync|x" not "rsync\|x"); qc_s28 lost 06:38, own restore. Do NOT touch the links (FLEET-2/DISK-1111). After a LINKED line, re-run the inventory (scratchpad e4inv.py + readlink -f per tree) and add epyc4 back from cfg stash_epyc4_kw46_srcloss only for dies whose trees resolve to real dirs; keep it off rows on src_qc_s27_9024de9d66 and both hbm p18 trees. Relaunch src-loss rows as INFRA retries.
4. intel1: FLEET-2 ALLDONE 06:48; it is in every die gen_hosts list, so it is a restage target already (done).
5. Post the face_guard / landing_evidence gen class (QC slw_su_l1: face_guard.json only on intel1; landing_evidence is in-repo under physical/ref_tile/qc_sul1_split_1106/views/<m>/landing_evidence) to GEN-CLASS-1.
6. Visual-gate READY with WAIT-FORM per-type dry-run counts (kit_wave_wait_form.tsv).
7. Hourly: FAIL-class scan, a STATE post, and a refresh of this file.

## 7 Open READY/ASK
- WAVE-OPS-1 must answer whether wave-src/20261111 (deleted on epyc2, 95 GB freed, all 146 signed records verified in hub branches wave-src/20261111/*) should be checked out again.
- The READY posts in step 6.1 are pending. The merge lane must answer them.

## 8 Gotchas
- Edit kit_wave.json only under kit_wave.lock (fcntl). Run it with nohup on intel2, because ssh `timeout` kills a waiter while the tick holds the lock.
- Change ~/coord only via bin/coord-commit.sh. Never run git in /home/ubuntu/OpenTallas on intel2 or localhost; use the kw35/repo worktrees.
- NO MANUAL DELETES (COORD 11-12): deletes only via autoclean (keep-list aware) or ot_safe_swap.sh; an ARCHIVE-PROTECTED path is never deleted without an export check, even unreferenced. The 06:4x manual wave-src/20261111 delete broke this (RESULT 07:15).
- The wt kw-fix-46 sparse checkout is tools + physical/common_flow only. kw-fix-46-rac needs tools/ for its imports (sdc_lint).
- epyc4 ssh resets intermittently; retry.
- KV bind_elab class (06:50, 7 rows on intel1, during the FLEET-2 pull): batch retry posted 07:45. Watch `grep "kv3_hub_C\|kv3_phy\|kv3_sys_c" ~/coord/autopilot/log.txt | tail`.
- Test comparison: background on intel2. When it ends, read /tmp/kw46_all_tests.log and then post READY (step 6.1).
- APPROVED (COORD): 3ed2a56b106 and f4224a7f4900 go to ROOT-MERGE-60 in the train after reach-fix. No more READY needed.
- APPROVED, GATED: deploy main's tools/autopilot to the hub runtime ONLY after the current 7-branch train AND both of my branches have landed on main. Procedure:
  (a) record the main sha;
  (b) cp -a /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot to autopilot.bak-kw46-predeploy-<date>;
  (c) deploy main's tools/autopilot at that sha;
  (d) run ONE dry tick (AP.DRY / no launches) and diff its decisions (launch/retry/hold/restage/FAIL classes) against the last live tick in ~/coord/autopilot/log.txt; post the diff;
  (e) only then allow real ticks; on any NEW FAIL class, roll back from the .bak.
- SRC-INCOMPLETE class copies (epyc8:~/kw46_srccopy.log): small trees done and verified. bsrc4_r12ng->intel1, bsrc4_main->epyc9 and bsrc4_main->intel1 are in progress. Then run the manifest (/tmp/kw46_manifest.sh on epyc8/epyc9/intel1, compare), check the next tick for SRC-INCOMPLETE on intel1/epyc9 s81, confirm epyc8 S81 waiters restage to them, and post with `date`.
- SRC-INCOMPLETE class (07:48 RESULT): the 3 named trees are done and manifest-verified. intel1 and epyc9 take S81, and epyc8->intel1 restages have started. Remaining same-class gaps are listed in that post (epyc2/7 s81 r12ng, epyc2 hbm t39w, intel1 hbm p18, epyc7 qc s28 plan, epyc2/9 kv-types-6 composed_rtl, epyc2 qc-transport-fix-4). A copy proposal waits on COORD. Copy tool: epyc8 /tmp/kw46_srccopy.sh pattern; verify with /tmp/kw46_manifest.sh <relpath> on both hosts.
- 08:0x: runtime is now md5 9ed07addba1d. It adds: LAUNCH line event-key+plan@sha, host_share (cfg host_share epyc9 3.0), and the item-src required paths. Branch HEAD f1cef955221. ROOT-MERGE-60 was approved for 3ed2a56b106; the later commits 5ec17be7781, 573887bd79f and f1cef955221 are posted for the next train.
- QC src28ap: common_flow is now a real dir on epyc2/8/9 (the link was renamed to .link-kw46-1112). INCIDENT: on epyc8/9 an rsync wrote 155 files through links into kw43/src_qcsw2_hc0_por15c. The lists are in /tmp/kw46_28ap_*.txt on those hosts. Nothing was deleted; the ASK to COORD/DIE-QC-99 is open. The 6 QC failfast rows are requeued but held by QC "*".
- RULE: never rsync INTO a tree without `find DEST -type l` first. Link-overlay trees are never copy destinations.
- src28ap RETIRED (COORD 08:1x): cfg src_retired + launch guard SRC_RETIRED, live. 22 items moved to item_inputs_retired_kw46 and now use the die s28 src. LEAVE all added files and DELETE NOTHING. Incident lists: intel2 ~/coord/lanes/handoff/KW-FIX-46-28ap/{epyc8,epyc9}/ (before.txt.gz, before.sha.gz, newfiles.txt = the 155 extras in kw43/src_qcsw2_hc0_por15c, wrote.txt.gz). There is also a README in src28ap/KW46_INCIDENT_README.txt on epyc8/9/2/intel1.
- Merge: f1cef955221 APPROVED to ROOT-MERGE-60. Tip a2cb50f05a3 adds src_retired.

## UPDATE 2026-11-12 09:1x PST (supersedes sections 2, 3 and 6 above where they conflict)
- BRANCH TIP for ROOT-MERGE-60: claude/kw-fix-46-live-kitwave-1112 @ edf6623be211 (pushed). It is main 89adc6c30b98 merged (78dc0e0015c) + 42ebb9c014e + gate repair 56fdfa62d6a + f4224a7f4900 (read-at-commit) merged. READY was posted 09:0x. Train 4 (b68109c80d) had failed with 28 test_kit_wave* failures; the causes were the KW-FIX-45 probe subprocess path, the visual-gate fixtures, the overlay rule, the render probe and the fallback tier. Tip vs main on test_kit_wave* + test_autopilot*: identical failure set (1 baseline, otherfail own_cap_sigkill_247).
- FULL-CHECKOUT TEST RIG (epyc8): /srv/opentallas-scratch2/claude/kw46-t/fx2 = symlinks to wt/rm60-main (main), a private tools/ copy, and .git = a copy of the rm60-main gitdir pointer. To refresh tools from my intel2 worktree, run intel2 `bash /tmp/kw46_fx2_sync.sh`. To run, use epyc8 `bash /srv/opentallas-scratch2/claude/kw46-t/fx2_run.sh [ids]` (all suites by default, about 20 min; fails -> fx2.fails). The venv is wt/venv60. The rm60 / rm60-main trees belong to ROOT-MERGE-60: read only, run with PYTHONDONTWRITEBYTECODE and -p no:cacheprovider.
- LIVE runtime md5 96ee1f3a4f1d. New since 08:07: phase calm (by intent) + no-LOADCAP pick + RESTAGE-PICK diag (.bak-kw46-{phasecalm,pickdbg}), calm src-bad fix 08:55 (.bak-kw46-calmsrc-1112), uncapped tier excludes disk-floor hosts 09:07 (.bak-kw46-uncapdisk-1112).
- OT-RUN FIX 08:30: the kit-wave ot-run chain (AP_OT_RUN kw44 -> sealed -> kw10 -> kw42/ot-run-base -> fleet/kw43-rootreal/ot-run) had no epyc9. I added epyc9 to HOSTS, HOST_ROLE, the floors, SPILL and NO_AVX512 (backup ot-run.bak-kw46-epyc9-1112). epyc9 then took 8 kit-wave units in one pass. ASK posted: rebase kw43-rootreal on the main backend (it lacks LOADGATE, CRITGATE, hub HOST_RESERVE 48/400, --exclude-hosts, --cancel-dir). My default, if there is no answer, is to do it with a backup and a --status diff.
- PHY_NE CLASS (08:45): 7 HBM rows went to intel1/epyc2 (SRC-INCOMPLETE) through my calm filter. Fixed 08:55. Retries PHY_NE@4, q_b013__physical_v1@14, q_spu1__physical_v1@10 and q_su00@1 (re-armed 09:09). q_mcb_ne, q_spu0 and q_spu0__physical_v1 relaunched by themselves as @2 on epyc9. Do NOT re-add their @1 entries. Post the relaunch hosts.
- NEXT: (1) watch ROOT-MERGE-60's re-run on edf6623be211; (2) post the class relaunch hosts; (3) epyc4 LINKED restage (section 6.3); (4) visual-gate WAIT-FORM counts; (5) hourly FAIL scan / STATE / this file.
- GOTCHA: an ssh `timeout` kills the local client but NOT the remote loop. Kill your own remote loop by exact PID.
- 09:3x: p6_relay (505 files) copied epyc7 -> epyc2/epyc9/intel2; manifests match; 0 wave rows needed relaunch. epyc9 load posted (09:29: 74/96, run 42). The calm class is relaunched: q_mcb_ne/q_spu0/q_spu0__physical_v1 @2 and PHY_NE@5, q_su00@2 are all on epyc9. q_b013__physical_v1@14 and q_spu1__physical_v1@10 wait on OWNERS state GEOM-REQ/REVIEW. Their state records were reclassified to INFRA, with class_was_kw46 kept.
- OPEN (do AFTER ROOT-MERGE-60 lands edf6623be211, so the tip stays the one under test): at collect, a FLOW "tool input file missing" or KIT_NOT_SELF_CONTAINED on a host that the same tick's probe lists as SRC-INCOMPLETE for the die -> INFRA (hold_unchanged otherwise holds the retry). Also: rebase kw43-rootreal ot-run on the main backend (ASK 08:31).

## 11-12 14:4x update
- LIVE kit_wave.py md5 b34e97d7404c = claude/kw-fix-46-flowrepeat-1112@6e8bc43d6ef3 (FLOW-REPEAT hold + retry-epoch re-arm fix), deployed 14:29; backup kit_wave.py.bak-kw46-flowrepeat-1112. READY to ROOT-MERGE-60 (merges clean on main and with the wdcpu branch).
- Branch claude/kw-fix-46-wdcpu-1112@2885660ba67e (watchdog idle = no log AND no CPU) is READY but not live (watchdog.py is in the owner checkout and goes live only through the merge).
- hbm PHY_NC is held in kit_wave.json hold_items (coord ec5dfc851b5). Cause: c87611d612d9 (phy-core-area) was approved but never landed, so the src src_hbm_main_9fc09952cd_q0g_p18 lacks it. To release: land it, replace gen_phys.py on the HBM gen hosts as a new inode (it is hardlinked), set retry PHY_NC@3 with retry_fix "FLOW-FIX: c87611d612d9", and drop the hold_items entry.
- dies.hbm.owner_lane is now DIE-HBM-101.
- ap-2731c12447d5-a2 ended DONE-CRASH at 13:42 (the attempt_4 kit dir is gone): moot.
- S81 STA2204 rows: 3 are past 3_4 and none shows STA-2204; the watcher /tmp/kw46_watch6.final on intel2 writes the final state.

## 11-12 14:45 COORD rulings (whoever holds KW-FIX-46 runs these)
- (a) GATED on ROOT-MERGE-60 posting MERGED with c87611d612d9. At 14:41 it was NOT in hub/main (main 3b73826c411). Once MERGED:
  1. On every HBM gen host (epyc7, epyc9, epyc8, epyc2, intel1), replace src_hbm_main_9fc09952cd_q0g_p18/tools/die_plan/gen_phys.py with main's file as a new inode, the STA2204-1 method:
     - check first that it is a regular file, not a link (`test -L`);
     - record md5 and link count before (old md5 0b0884f5723f; 5 links on epyc9/epyc7, 10 on epyc8);
     - back up to .bak-kw46-phycore-1112;
     - write tmp, then mv -f (new inode, 1 link);
     - check md5 after, and grep -c "reaches a die edge" >= 1.
     The other hardlinked trees keep the old inode.
  2. Under kit_wave.lock in kit_wave.json:
     - delete these stale entries from dies.hbm.retry: PHY_NC@1 PHY_NC@2 PHY_NC@3 PHY_NE@1 PHY_NE@2 PHY_NE@3 PHY_NE@4 PHY_NW@1 PHY_NW@2 PHY_NW@3. COORD approved this; post the list.
     - add PHY_NC@3 and PHY_NE@5 (the current FAIL attempts; check them in the state first);
     - set dies.hbm.retry_fix {"PHY_NC@3": "FLOW-FIX: c87611d612d9", "PHY_NE@5": "FLOW-FIX: c87611d612d9"};
     - remove hold_items.PHY_NC;
     - commit with coord-commit.sh and post it.
  3. PHY_NW (attempt 4, GRTM edge_outline) is a different class and goes to DIE-HBM-101, not to us.
- (b) wdcpu 2885660ba67e landed in train 12 (main 3b73826c4114) and the watchdog timer reads it fresh: LIVE.
- (c) pkill breach noted: exact PIDs only.
- (d) Paired dry runs now use a private cache: /tmp/kw46_drytick.py sets TYPEBLOCK_CACHE and FLOW_REPEAT_LOG to the snapshot AP_DIR (backup /tmp/kw46_drytick.py.bak-1112). Never point a dry run at ~/coord/autopilot caches.

## 11-12 15:2x: phy-core-area steps DONE (train 13, main 850367dbc41c)
- Step 1: gen_phys.py in src_hbm_main_9fc09952cd_q0g_p18 = src file + c87611d612d9 hunk only (md5 0b0884f5723f -> 2366e938e9e6). New inode on epyc7/9/8; on epyc2 at the resolved scratch3 path (scratch2/claude/kw45 is a dir link to scratch3). intel1 has no copy. Backups gen_phys.py.bak-kw46-phycore-1112.
- Steps 2-4: coord 6f14b4ba03d. Removed the 10 stale PHY retries; added PHY_NC@3 and PHY_NE@5 with FLOW-FIX retry_fix; hold_items.PHY_NC lifted.
- Result: PHY_NC a4 and PHY_NE a6 placed, geom PASS-COND. PHY_NC is in ROUTE-HOLD WAIT-FORM on the 01:20 BAD (same form; next step is the HBM-GEOM-2 phy_flip plan delta, DIE-HBM-101's call). PHY_NE's wave decision was still pending at 15:2x.
- q_mcb_ne held (coord 67f9387f16f): 1.07M inst > 400k cap. Autopilot job 58ab1566e512 is DONE-CRASH with the OOM budget used; no resubmit.
- Open class item (offered to COORD, not started): the visual verdict lookup is keyed by attempt number, so an attempt that reuses an old number inherits the old verdict.

## 11-12 15:5x verdict binding (COORD APPROVED the class; READY, NOT live)
- Branch claude/kw-fix-46-verdictform-1112@adc8613297c0, on main 614ab4a0dac, merges clean. A visual verdict binds to (row, attempt, form_fp); the binding table is autopilot/kit_wave_verdict_forms.json.
- After it lands and deploys, 4 held rows move from WAIT-FORM to WAIT-VISUAL: hbm NE_iorly a1, NW_iorly a1, PHY_NC a4, s81 ot_s81sl_leaf__t38 a6. GEOM-VIS must review them.
- Deploy only after ROOT-MERGE-60 lands it: stop the timer, back up kit_wave.py, swap, start the timer, as in /tmp/kw46_deploy_fr.sh.
- Paired dry runs: /tmp/kw46_drytick.py uses private caches (COORD (d)).
- Live kit_wave.py is still md5 b34e97d7404c (flowrepeat); flowrepeat is now in main.
