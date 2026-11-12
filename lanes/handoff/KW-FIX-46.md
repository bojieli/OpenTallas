# KW-FIX-46 lane handoff (refreshed 2026-11-12 07:36 PST)

## 1 Scope
Owner of the kit-wave autopilot code: hub runtime kit_wave.py, ot-run admission, autoclean/reaper keep lists. Fix FAIL classes once per class, hold and retry rows in ~/coord/autopilot/kit_wave.json. The sidecar-coverage preflight now belongs to GEN-CLASS-1 (COORD 11-12), not this lane.

## 2 Worktrees (all on intel2)
- /srv/opentallas-scratch2/claude/wt/kw-fix-46, branch claude/kw-fix-46-live-kitwave-1112, HEAD 3ed2a56b106 (pushed, clean; + src import-closure probe, test_kit_wave_import_probe.py). Holds the live runtime hunks merged onto main, plus: stale place-service set-aside, held_stop_reason (stopped held rows go to WAIT-FORM), sidecar_preflight, and VISUAL-QUEUE stale filter (visual_gate_since). New tests: test_kit_wave_held_stop.py, test_kit_wave_sidecar_preflight.py, test_kit_wave_visual_stale.py; test_kit_wave_flow_tag.py was fixed.
- /srv/opentallas-scratch2/claude/wt/kw-fix-46-rac, branch claude/kw-fix-46-read-at-commit-1112, HEAD f4224a7f4900 (pushed, clean). gen_core_kit_hbm.fetch() reads REPO/.kw_at_commit/<commit>/<file> when git show fails (a wave src is a plain copy). Test: physical/die_plan/hbm_arch_cores/test_fetch_at_commit_store.py.
- Base for test comparison: /srv/opentallas-scratch2/claude/wt/kw-fix-46-base (origin/main).
- LIVE runtime: /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot/kit_wave.py, md5 83925c990434. It is patched in place. Backups are kit_wave.py.bak-kw46-{stalesvc,heldstop,sidecar,vq,imports}-1112. The runtime lags main: it lacks FAILFAST-1 stop_cancelled_rows, type_overlay, bind_preflight and plan_sha_mismatch. Do NOT deploy main's tools/autopilot without COORD approval.

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
