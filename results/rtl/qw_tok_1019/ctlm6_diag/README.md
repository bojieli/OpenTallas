# QW-CTLM6 10-20: qfd_tt_ctlm_dv safe5/safe5n/safe5c terminal FAIL -> safe6 structural plan

All numbers below were measured on the fleet. Sources: the safe5 gate run ot-agidock128:/srv/opentallas-scratch/claude/ref_gate/qfd_tt_ctlm_dv_safe5-20261019-215827
(4_1_cts.odb, 1_2_yosys.v). The scripts are in this directory.

## Gate verdicts (all three FAIL: 5 fail, 3 warn)
| kit | wire_reach | clock_rule ck_core TT/FF | clock_rule ck_hr TT/FF | GRT |
|-----|-----------|--------------------------|------------------------|-----|
| safe5 (regions) | u_hr/me_image_ready -> control_stores_ready, 592 um unregistered | 179.0 / 152.6 | 262.6 / 221.2 | 0 overflow |
| safe5n (no regions) | same | 179.0 / 152.6 | 262.6 / 221.2 | 0 |
| safe5c (ck_core/rst_n on S) | same | 157.0 / 137.0 | 263.4 / 222.3 | 0 |
Two of the warnings hide census violations, so under the PRE-GATE rule they count as FAILs: high_fanout u_lprc_u_gi 4,299 loads, and util_channel 0 um between stacked p192 SRAMs.

## Root cause 1: readiness path (fixed in 040dee75d)
control_stores_ready was u_go's combinational AND of the head's register-backed me_image_ready with c_ready, xpf_loader_ready and xpf_monitor_ready. Nothing registered it between u_hr and the N pin. It now leaves through the named registered landing
u_lpo_control_stores_ready (lp out_regs 2, hr region: stage 1 sits beside the caller AND, stage 2 is the pin flop). Its compiler record offset goes from 6 to 8, every other port is unchanged, and the audit PASSes.
The benches compare it at its own offset (LOFF_CSR, a30efff68).

## Root cause 2: pin-flop spread (safe5_pin_flop_map_tt.txt, per-flop TT arrival + placement from diag_ck.py)
* ck_hr: the soft registers are bimodal. The N/E/interior registers arrive at 459-500 ps (the N pin band alone is 23 ps wide). The S strip under h16c (y < 60, below the macros) arrives at 596-721 ps.
  The placer moved u_go's XPF loader/schedule into that strip. The gate judges the cluster per root child pair (u_hr vs all soft registers on ck_hr). u_hr's flops sit at pin 374.7 + its own boundary 271.5..346.6 = 646..721 ps,
  so the pair is 721 - 459 = 262 ps. **Moving the S strip off ck_hr does not fix the pair**: the soft registers still start at 459 while the child sits at 646-721.
  CTS (-delay_buffer_derate 0.75) balanced the h16c raw SRAM pins (ck_pm0/1 tapped to 677) but did not delay the soft tree by the child's insertion of about 300 ps.
* ck_core: the only boundary registers are the 1,088 tl flops plus the pw ring (S strip x98-519 under the SRAM columns) and the reset root flop (N face, 853 ps). Inside the S band alone the arrival spans 903-1032 ps, about 129 ps.
  The tree is about 1 ns deep (10,596 register sinks + 9 macros over 544 x 410 um), and its 20-um leaf groups land on plateaus about 120 ps apart.

## Root cause 3: PRE-GATE native census (safe5_native_census_violations.json): FAIL, 422 drivers > 32, max 4,299
| class | count | worst |
|-------|-------|-------|
| combinational select/decode nets (_N_/Y) | 101 | 737 |
| landing ring rq (u_lpl_*_w chunk rq) | 57 | 120 |
| calendar fifo sel / ws / valid (g_fifo*.g_sel*/g_wce*) | 192 | 34 |
| calendar mask copies (g_m*.g_wm*.g_copy*.u_mask) | 32 | 33 |
| fifo bypass | 16 | 64 |
| child reset u_lprc_u_gi / u_lprc_u_go / region leaves u_lpr_core_l, u_lpr_hr_l | 4 | 4,299 / 184 / 69 / 69 |
| tl_v2 (tl enable) | 1 | 1,088 |
| rdb_oh[0/1] | 2 | 611 |
| u_go.hr_lo[0] (hv) | 1 | 617 |
| ctx_q[128], cmd_user, ss_q, dh_q, op leaf anch/rd_c/bank, loc_seg, fire_q, lpl_r o, xpf active | 15 | 227 |

## safe6 structural plan (nothing gated: the binding PRE-GATE census blocks any first gate)
1. **Census repair** (RTL, lockstep + mutants on V5.050):
   * u_gi calendar (qfd_dv_cmd_cal_mu): kept same-edge copies for sel/ws/valid/mask/bypass (34 -> 2 x 17) and for the rdb_oh / tl_v / cmd_user / ctx_q / fire_q roots, with copy trees of at most 32 loads.
   * Registered one-hot selects replace the 101 wide combinational decodes.
   * Reset forest for every child reset (u_gi 4,299, u_go 184), using ot_rst_relay regional leaves with a 2-stage landing. lp.py landing_reset_forest is incompatible with landing_reset_lead today, so lp.py needs to support both.
   * Per-chunk ring rq copies in the ot_pl_land library (57 rings, at most 120 loads). This is a shared-library change and needs a Gate-Rule commit through ROOT.
   * u_go hv / hr_lo[0] split into a dedicated valid copy.
2. **Clock regions**:
   * (a) The S-face pin bands get their own landed regions with root ports ck_sw (tl + pw, x43-410) and ck_se (ag5/cmd/hr/ss5, x655-771), using wires-only band children in the flat parent. Each crossing adds 3 edges: tl 3->6, hr/cmd 6->9, pw/ss5/ag5 +3. The die GEN must re-slot.
     ck_core then keeps only rst_n on its boundary, and ck_hr keeps the N/E bands (the N band measured 23 ps).
   * (b) The u_hr child must stop sharing a CTS root with soft registers. It needs direct entry ports for ck_head/ck_pm0/ck_pm1, with the die delivering phi - R (the clock_entries.tcl wires-only standard; hybrid_entries).
     This needs an lp.py extension (entry_pins: hard-child clock pins on dedicated ports, unlanded inside the region) and a gate path for hybrid + landed clusters.
     The alternative is full CTS latency balancing for landed clusters with hard children (delay_buffer_derate 1.0), which is a flow change. **Coordinator/ROOT decision.**
3. **Floorplan**: block the 0-um channels between stacked p192 SRAMs (no rows), and keep u_go out of the S strip with a region fence beside u_hr.
4. TTC.4 F16WTN/PRIVATE_CALR is not "just params". CALR=1 needs two ot_rom_4096x266_m8 (121.8 x 62.9) slots, and F16WTN needs the closed wtn child bound in u_gi. Params stay at 0 in safe6.

## Readiness landing benches (Verilator 5.050, fleet ot-epyc6, source a30efff68; bench_v5050/)
* lp lockstep: AUDIT PASS, AUDIT-UNLAND FAIL (expected); MUT 0 PASS, MUT 1/2/4/5 FAIL.
* prog landed (hard head): L0 LANDED_LOCKSTEP PASS 18066/0 (CTLM_PROG PASS 84/84, csr@1042); LMUT 1 FAIL 1235, LMUT 2 FAIL 1174.
* opseg landed: l0 PASS (red_mu 845537/0, full_mu PASS), MU_OPSEG PASS; l1 FAIL 845537, l2 FAIL 9199; MU_OPSEG BENCHES PASS.
* Readiness-offset mutant (staged record with control_stores_ready forced 8 -> 6, prog_csrmut.out): LANDED_LOCKSTEP FAIL with
  2 mismatches at cycles 1048/1049, exactly the csr rising edge. The per-port compare is live, and the 2 added edges are real and accounted for.
