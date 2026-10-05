> Historical source/run handoff for the retained gates below. Earlier RUNNING/QUEUED entries describe the original handoff, not the current fleet or combined-design readiness. Current gate results are listed in the final section.

# DS ROM system RTL stream -- STATUS (handed to Codex 2026-10-03, see /tmp/claude-review-20261003/HANDOVER_TO_CODEX_2.md)
Branch claude/dsrom-system-rtl-20261003 (head 8f6459462+). Worktree /home/ubuntu/dsrom-system-rtl-20261003 (main box).
Scratch here: src/ (rsync of the branch; src/SOURCE_COMMIT), run/<name>/ (gates), l0d/ (L0 diagnosis), job.sh, l0job.sh.
epyc lacks the golden's tokenizer: images are prepared on the main box
(`tools/dsrom_system_campaign.py --only CFG --scratch D --output x --prepare-only`), rsynced into run/<name>/,
then `./job.sh <name> <CFG> [GPARAMS] [TAG]` (Verilator 5.050) -> run/gate_<name>.json, <name>.rc, <name>.log.

## System end-to-end
- DONE sys_b2 PASS (committed aa02d73f8): 2 packages, CRC/replay board links w/ injected errors, host CQ,
  stage guards, stall export, KV in attached-HBM model; tokens 2815/3537/2047 @ pos 0/1/2 exact, logits/KV/VM exact, 1,304,979 cycles.
- FAIL sys_b5 r1 (committed log): split lm_head parts read unwritten ME-bank lines (bank image built from the
  single-core program). Fix committed 8f6459462 (bank = union of stage programs, MBAW_P=18).
- RUNNING: sys_b2_lrt0 (control, pinned link LINK_RT=0; compare cycles vs sys_b2), sys_d5, sys_d5_u2, sys_d5_p3g2
  (5 body dies in 3 packages: 2 UCIe + 3 board links; 2 users; positions 0..3).
- QUEUED by /tmp/claude-1000/dsys/ship_fix.sh on the main box: sys_b5_r2, sys_b5_u2_r2, sys_b5_p3g2_r2 (split-head fix).
Next: copy each run/gate_<name>.json + out log into results/rtl/dsrom_system_rtl_20261003/system_gate_<name>.*, commit.

## L0 stall diagnosis
l0job.sh: original w17 r4 L0 config (compiled models unchanged) + read-only -DL0DIAG observer, RT_THREADS=8,
stops at cycle 20,000. At handover: cycle ~8,000, pc 9 on all dies (original reached PC24 at 12,400). Twin on ot-pve1 /home/ubuntu/l0d/out (~7 s/cycle).
Next: after PC24 persists, `python3 tools/dsrom_l0_diag_record.py --run-dir l0d/out --orig-progress <r4 progress.log> --meta <launch_manifest.json> --out l0_diag.json`
(see results/rtl/dsrom_system_rtl_20261003/l0diag/REPLAY.md) and name the blocker from diag.log (CH/SN lines).

## Levers
- Refill tag (WINDOW_REFILL_CREDITS epoch>=512 alias): DONE, committed (ot_dsrom_window_kv_prefetch_lv EPOCH_SAFE, 600 refills, levers/window_refill_tag.json).
  Note: tag NOT widened (owner bits fixed by pinned muxes); epoch narrowed to 9 bits with safe wrap.
- Same-x phase merge: tools/dsrom_lever_phase_merge.py (emitter option + images + ab). Measurement in progress by a helper
  (scratch levers/ here, flat_l0 field build); no committed record yet. Full-layer runtime measurement NOT done.
- SU kr lint: successor copies rtl/dsrom_sys/levers/ot_hdc_core_v41x_kr_lv.sv, ot_hdc_v41x_me_adapt_lv.sv (uncommitted),
  tools/dsrom_lever_su_kr.py; lint/exactness record not yet produced.

## Unit-level done (committed): link_rt, host CQ/stall export/stage guard, idx scorer location (hub vs per-stack),
ckv AG_CREDIT, field FAULT_TIE + RET_CREDIT (issue gate never engaged on real phases), inventory.json.
Not built (owned elsewhere): Nash lease/SU guard, HBM controller domain, 0.9 GHz split, MTP RTL, power/reset sequencing.

## System gates 2026-10-03 (source 8f6459462, Verilator 5.050, ot-epyc1tb; collected 2026-10-04)
All five PASS, rc=0, 0 token/logit/state mismatches, out.txt sha256 == gate log_sha256:
sys_b5_r2 (config body=3 hp=2, 5 nodes in 3 pkgs, 1 user, p2g1) 870,176 cyc; sys_b5_u2_r2 (2 users) 1,025,811 cyc;
sys_d5 (body=5 hp=0, 3 pkgs, 1 user, p2g1) 867,693 cyc; sys_d5_u2 (2 users) 964,523 cyc; sys_d5_p3g2 (positions up to 3, 2 generated) 1,747,617 cyc.
sys_b5_p3g2_r2 was still running at collection (not recorded).

<!-- merged from claude/dsrom-system-rtl-20261003 -->
# DS ROM system RTL stream -- STATUS (handed to Codex 2026-10-03, see /tmp/claude-review-20261003/HANDOVER_TO_CODEX_2.md)
Branch claude/dsrom-system-rtl-20261003 (head 8f6459462+). Worktree /home/ubuntu/dsrom-system-rtl-20261003 (main box).
Scratch here: src/ (rsync of the branch; src/SOURCE_COMMIT), run/<name>/ (gates), l0d/ (L0 diagnosis), job.sh, l0job.sh.
epyc lacks the golden's tokenizer: images are prepared on the main box
(`tools/dsrom_system_campaign.py --only CFG --scratch D --output x --prepare-only`), rsynced into run/<name>/,
then `./job.sh <name> <CFG> [GPARAMS] [TAG]` (Verilator 5.050) -> run/gate_<name>.json, <name>.rc, <name>.log.

## System end-to-end
- DONE sys_b2 PASS (committed aa02d73f8): 2 packages, CRC/replay board links w/ injected errors, host CQ,
  stage guards, stall export, KV in attached-HBM model; tokens 2815/3537/2047 @ pos 0/1/2 exact, logits/KV/VM exact, 1,304,979 cycles.
- FAIL sys_b5 r1 (committed log): split lm_head parts read unwritten ME-bank lines (bank image built from the
  single-core program). Fix committed 8f6459462 (bank = union of stage programs, MBAW_P=18).
- RUNNING: sys_b2_lrt0 (control, pinned link LINK_RT=0; compare cycles vs sys_b2), sys_d5, sys_d5_u2, sys_d5_p3g2
  (5 body dies in 3 packages: 2 UCIe + 3 board links; 2 users; positions 0..3).
- QUEUED by /tmp/claude-1000/dsys/ship_fix.sh on the main box: sys_b5_r2, sys_b5_u2_r2, sys_b5_p3g2_r2 (split-head fix).
Next: copy each run/gate_<name>.json + out log into results/rtl/dsrom_system_rtl_20261003/system_gate_<name>.*, commit.

## L0 stall diagnosis
l0job.sh: original w17 r4 L0 config (compiled models unchanged) + read-only -DL0DIAG observer, RT_THREADS=8,
stops at cycle 20,000. At handover: cycle ~8,000, pc 9 on all dies (original reached PC24 at 12,400). Twin on ot-pve1 /home/ubuntu/l0d/out (~7 s/cycle).
Next: after PC24 persists, `python3 tools/dsrom_l0_diag_record.py --run-dir l0d/out --orig-progress <r4 progress.log> --meta <launch_manifest.json> --out l0_diag.json`
(see results/rtl/dsrom_system_rtl_20261003/l0diag/REPLAY.md) and name the blocker from diag.log (CH/SN lines).

## Levers
- Refill tag (WINDOW_REFILL_CREDITS epoch>=512 alias): DONE, committed (ot_dsrom_window_kv_prefetch_lv EPOCH_SAFE, 600 refills, levers/window_refill_tag.json).
  Note: tag NOT widened (owner bits fixed by pinned muxes); epoch narrowed to 9 bits with safe wrap.
- Same-x phase merge: tools/dsrom_lever_phase_merge.py (emitter option + images + ab). Measurement in progress by a helper
  (scratch levers/ here, flat_l0 field build); no committed record yet. Full-layer runtime measurement NOT done.
- SU kr lint: successor copies rtl/dsrom_sys/levers/ot_hdc_core_v41x_kr_lv.sv, ot_hdc_v41x_me_adapt_lv.sv (uncommitted),
  tools/dsrom_lever_su_kr.py; lint/exactness record not yet produced.

## Unit-level done (committed): link_rt, host CQ/stall export/stage guard, idx scorer location (hub vs per-stack),
ckv AG_CREDIT, field FAULT_TIE + RET_CREDIT (issue gate never engaged on real phases), inventory.json.
Not built (owned elsewhere): Nash lease/SU guard, HBM controller domain, 0.9 GHz split, MTP RTL, power/reset sequencing.

## System gates 2026-10-03 (source 8f6459462, Verilator 5.050, ot-epyc1tb; collected 2026-10-04)
All five PASS, rc=0, 0 token/logit/state mismatches, out.txt sha256 == gate log_sha256:
sys_b5_r2 (config body=3 hp=2, 5 nodes in 3 pkgs, 1 user, p2g1) 870,176 cyc; sys_b5_u2_r2 (2 users) 1,025,811 cyc;
sys_d5 (body=5 hp=0, 3 pkgs, 1 user, p2g1) 867,693 cyc; sys_d5_u2 (2 users) 964,523 cyc; sys_d5_p3g2 (positions up to 3, 2 generated) 1,747,617 cyc.
sys_b5_p3g2_r2 was still running at collection (not recorded).
