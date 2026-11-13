# KIT-OPS-1 handoff (kit-wave operations lane; COORD is the coordinator) -- 2026-11-12 18:21 PST

## Tasks
1. KV re-kit on vN2: DONE + RESULT posted. coord 9fa10c7b844: event kvN2_66e6607, src kw45/src_kv_main_66e6607e3f, bind epyc8 kit-ops-1/kvbind_vN2i/out (also mirrored to epyc9/epyc2/intel1/epyc7). 33 KV LAUNCH lines 18:17:57-18:18:04. Revert = dies.qwen_kvsys.prev_kitops1_kvn2 / backup autopilot/kit_wave.json.bak-kitops1-kvn2-1112.
   OPEN: epyc7 copy of src_kv_main_66e6607e3f still running (epyc8 stage_src1.out, then stage2.sh pass 2 resyncs epyc7; STAGE2_DONE in kit-ops-1/stage2.out). Until it finishes the wave flags epyc7 KV SRC-INCOMPLETE and skips epyc7 (as designed).
   OPEN: kv3_hg*, kv3_hgi*, kv3_hg_v1p* holds wait on GEOM-VIS-7's verdict on the vN2 drawing. Lift them in one edit under the lock.
2. HEAD re-kit on rp18: NOT STARTED. Train 21 (7bf527a804) is NOT in hub main as of 2026-11-12 18:21 (main = 66e6607e3f). Re-kit list: lep0N window-only re-sign; full builds for the w/e shim tx/rx and turn_a/b reset-column types; new reset trees for hd_spn, hd_spn_end, hd_tile and hd_turn_a. Same recipe as KV: archive main -> kw45 src_head_main_<sha>, stage, switch dies.s81_head under the lock.
3. QC epyc7 SRC-INCOMPLETE: RESTORE chosen. Copy epyc9 -> epyc7 of kw45/qcs28in is done (RC 0). The src_qc_s28_88018018ef copy is running (epyc9 kit-ops-1/stage_qc_src.out). Reference manifests: epyc9 vs intel1 are identical except __pycache__ and archive-marker ARCHIVED.json files that exist only on intel1. qcs28in: files 493, sha eade5729b52eb6c9 on both. To finish: run manifest.sh on epyc7, compare with epyc9 (man_qc/*.list), confirm the next tick has no "SRC-INCOMPLETE epyc7 qwen_compute", then post a RESULT.
4/5. Branch claude/kit-ops-1-1112@f35e1e8835 pushed; READY posted (not live). Contents: PLAN-CORE-NOT-IN-ONLY, ISSUES=reject + queue drop, and the kit_preflight plan_pins_source check. Risk sweep: 0 mismatches on every die (intel2 /tmp/kitops1_pps_res.txt).

## Work dirs
- epyc8 /srv/opentallas-scratch2/claude/kit-ops-1 (repo clone, wt worktree, scripts, kvbind_vN2i).
- Helpers: /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/kitops (post.sh, handoff.sh, stage_src.sh, manifest.sh, kv_vn2_switch.py, pps_sweep.py).

## Rules
- kit_wave.json edits only on intel2 under autopilot/kit_wave.lock, with a backup, committed with coord-commit.sh, verified on origin.
- Never delete. Never sync into a link or overlay tree. Real dirs only. git -C only on my own clone.
