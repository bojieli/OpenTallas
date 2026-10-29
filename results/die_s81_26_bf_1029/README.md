# DIE-S81-26 BF core (ot_v41_bf_col) TAG16 clock re-plan + ROM _gb reset64 LEC diagnosis, 2026-10-29

## (A) TAG16 core clock re-plan (t16a V1 ROM sites / t16b ROMs on S/N faces)
Sink delta of the TAG16+KEEP_XPOS netlist vs the d25 slice, re-checked with sinkcheck.py on the run's own 1_synth.v
(CHECKED): actual CLK pins 53968 (51180 DFFHQN + 2748 DFFASRHQN + 40 ICG); slice 53850 leaf flops + 40 original gates;
missing 182 (91 g_tag_local.u_prefix line, 88 g_group[].u_copy, 3 g_xpk.u_xpos), extra 104 (u_pt line[0..103]).
The "1252 gates" are the d25 plan's own planned ICG stages (40 RTL gates + 1212 clone_of copies, form C), not a fault.
The rename-only rebind (core_sink_census.py) cannot apply: 182 new flops need leaf membership -> full form C re-plan.
Path (chain.sh, one variant per call, epyc2):
1. census kit = variant kit minus master_slice.tcl / enable isolation, GOAL=place (own netlist; trial, not a build of record);
2. gated census geo (core_family_geo.tcl GATED=1, ENTRY = current kit clock pin 273.228,95.58) + floorplan sites;
3. form C planner = the code + family that made the d25 plan (intel1 codex-icg-tree-1028/src, codex/icg-tree-1028),
   only change fam26.json: bf_col entry 'centre' = the census PIN = the current pin (pin contract unchanged, fix-only delta);
4. converter (main) --band info --window-policy info (12.3a, as the d25 slice);
5. master_slice.kit_apply (main tools; dry run with the d25 slice reproduces master_core_infra.tcl / master_slice.json /
   core_infra_plan.json byte-identical, CHECKED); exact sink check (all CLK pins == leaf sinks + original gates, else FAIL);
6. enable isolation repacked with Codex's pack logic (pack26.py) on a sites dump after master_slice + face flops (pass1.tcl);
7. GOAL=place.
Plan numbers are PLAN MODEL, UNCHECKED until built.

## (B) ROM _gb reset64 LEC: NOT EQUIVALENT 277/76277 (intel1 ce10-lec/rom_gb/lec_rc64, lec.py e256f6799)
Every one of the 277 failing points has one of two gold-only registers in its unmatched cone (CHECKED from lec.json):
- 149 points (a_ctr, wA, wB, w_coh, w_cgt, w_cnt, w_sf, ...): ff:u_e.w_cgt[0]. w_cgt = qx_gt(one-hot) = mask k > c, so
  bit 0 is 0 on EVERY load (qx_gt()[0] = seen before k=0 = 0). w_cgt has no reset (loaded only at go_e / class step under
  rst_n), so the RTL value is the free power-up value until the first go; synthesis folded the bit to 0 (sound X refinement).
  The readers (a_ctr / w_ptr via issue / w_restart) all need w_run, which is reset 0 and set only at go_em (= go_e).
  Class = removed-by-synthesis constant of a non-reset register, NOT a reset-window problem, NOT a real bug.
  Fix (lec.py LEC-FPREG-5 form, proved by the same induction, not a waiver):
  ['gold','ff:u_dut.u_e.w_cgt[0]',['loaded',0,[[['ff:u_dut.u_e.w_run',1]]]]].
- 128 points (g_mac[1].g_l3.u_l1.q1_sh[*][*]): gold-only g_mac[1].u_l1.q0_wf[w][1+4j] (32 bits). u_l1 is tied fp4=1, so
  wc = e2m1(...) and wf bit1 == wf bit2 (E4 exponent 7/8/9/6/0: bits 1 and 2 always equal); synthesis merged bit1 into bit2
  in BOTH macs (gate keeps q0_wf[i][0,2,3] only). The LEC's own miner proposed this eq for g_mac[0] (32 hyps in hyp.json)
  but not for g_mac[1] -> same merged-register class as the BF c4.r[0]/r[28] case.
  Fix: 32 gold eq hints q0_wf[w][4j+1] == q0_wf[w][4j+2] for g_mac[1] (mirror of the miner's g_mac[0] hypotheses).
Hints in rom64/hints_add.json (33), appended to the kit's 177. Rerun intel1 die-s81-26/rom64 (run_lec.sh, docker
ds81-26-rom64, 64 GB, main f483150e0 lec.py as the BF lecx rerun); collect run.status + lec_x64/lec.json (~2.5 h).
