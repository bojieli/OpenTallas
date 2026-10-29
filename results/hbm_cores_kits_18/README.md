# HBM-CORES-KITS-18 (2026-10-29): collect the KITS-17 places, rst_n far-pin anchor, hold-margin reruns

AUTO-GEOM = codex-hbm-k13-wave0830/tools/geom_check.sh (read-only; GRT probe 50 it). I viewed every render myself.
Numbers come from auto_geom.json / run logs (CHECKED).

## rst_n far-pin class (GEOM-58 xcal / GEOM-59 qw_dec)
`reset_anchor.tcl` is installed as the kit-local `/work/reset_tree.tcl`. That hook point already exists: face_flops.tcl
sources it after the face-flop pass. It places the reset entry flops FIRM in face_flops' own face-band slot grid
(ff_occ) next to rst_n. When release=1, the flops are appended to ot_face_flops.txt, so face_flops_release.tcl makes
them PLACED before DPL, exactly like face flops. The fix adds no buffer, no ECO and no new check.

| kit | variant | anchored | pin_reg_max | r2r | other | verdict |
|---|---|---|---|---|---|---|
| qw_dec 03c4f6c37aa2 | V1 | u_rst.sync_q[0:1] (release) | 218 -> 10.1 | 299.05 | all ok, GRT 0 | **PASS (pick)** |
| qw_dec | V2 | all 4 u_rst flops (release) | 10.27 | 327.02 | all ok | PASS (worse r2r) |
| xcal_rel_t 59bcf8ea762e _k12d16v | V1 | u_fcore.rst_q (release) | 200 -> 6.99 | 311.09 | col_v FAIL 1.386 (GEOM-58: projection class, GRT 0, not blocking) | **PASS-COND (pick)** |
| xcal | V2 | u_fcore.rst_q (kept FIRM through DPL) | 6.98 | 309.58 | same col_v | same |

KIT_PREFLIGHT --contract PASS (plan c25c_d16) on qwdec_v1 and xcal_v1. Kits are at epyc2:/srv/opentallas-scratch2/claude/hbm-cores-kits-18/rst/{qwdec,xcal}_v{1,2}.

## KITS-17 variant places (plan c25c_d16k vA/vB)
| kit | outline | verdict | main reasons |
|---|---|---|---|
| cxport_ij_q V1 (vA) | 345.6x250.56 | FAIL | fill .079, empty .77, r2r 447 (155), pin_reg rst_q_n 217 |
| cxport_ij_q V2 (vB) | 241.92x233.28 | FAIL | fill .118, empty .61, pin_reg rst_q_n 188 (r2r 376 ok) |
| sfustore_hw V2 (vA) | 345.6x354.24 | FAIL | GRT ov 13, r2r 523 (14), relay_collapse 7, fill .041 |
| qcore_r13 V2 (vA) | 267.84x250.56 | FAIL | GRT ov 6801, all of it over the 2 stacked SRAMs (macro pin ends + 8 um channel) |

## Hold reruns (OWNER 12.19 margin)
- bdring _k13: the GRT repair reached +10.001 at margin 10, and the pre-route FF hold estimate was -0.26 (measured loss 10.26 > 10). Rerun at margin 15 from the same 4_cts gave FF_PRE_ROUTE_HOLD +2.31 PASS. DRT then failed with DRT-0255 on mp_isl0_ck_i / mp_isl1_rst_i, because the island pins sit at the legacy cx+-2.16 (REBAL-2 root cause). The kit was regenerated as _k18: mk_c20 --ft-pin-dx-um 1.08 --gen-args "--hold-ff-margin 15", plan c25c_d16 6ba9f877d23f, preflight PASS. Finish is running on epyc2.
- RING keep A2: margin 0 -> 10 (loss 2.97). GRT was redone from the same 4_cts and the finish is running on epyc2. Its island pins are already at cx+-1.08.

## 2026-10-29 13:4x update (CHECKED from auto_geom.json / signoff.json / lec.json; renders viewed)

| item | result |
|---|---|
| hfd_ep_static MY re-place (epyc2 hbm-cores-kits-18/ep/ep_my, 4 SRAM R0->MY same x/y, rs[0] anchored at rst_n) | AUTO-GEOM FAIL: GRT 255,546 @50 it (R0: 349,116), col_v 2.03, r2r 539.9 / 59 (42 = u_fcore.p_tx_f -> u_tx.beat), pin_reg_max 7.71 (was 248.7) |
| ep_my 13 status bits (rx_block_ready/fault_cause, N pins kept) | all capture legs to u_bout q <= 368.4 (fault_cause[9]); one feed leg p_st[0] -> fault_cause[10] = 449.7 |
| qcore_r13 V1 (intel1) | AUTO-GEOM FAIL GRT 29,512 on the 2 stacked centre SRAMs; r2r 349.9 ok |
| bdring _k18 | AUTO-GEOM PASS (GRT 0); finish NOT SIGNED: setup TT -22.43 (10), drv slew TT 7496, TT insertion 297.1 vs 250+-40; hold FF +3.4 |
| RING keep A2 margin 10 | NOT SIGNED on drv slew only (TT 1477 / FF 1157); setup +47, hold +0.39, DRC 0 |
| LEC gq_issue x2 / serdes | NOT EQUIVALENT (1024 / 1024 / 3412+754 undecided) |
