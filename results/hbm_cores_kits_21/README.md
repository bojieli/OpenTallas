# HBM-CORES-KITS-21 (2026-10-29 15:35-17:45 PDT)

All runs on epyc2 `/srv/opentallas-scratch2/claude/hbm-cores-kits-21/`. Numbers are CHECKED from the named logs unless marked UNCHECKED.

## RING (ot_hfd_coll_q2_hard_v8g__ring_ag): margin 30 rerun -> slew 1477 -> 88

`ring/ring_k21m30` = RING keep A2 kit (hbm-cores-kits-17/kits/ring_keep_eco, ra_* band ECO 3_place kept), rerun from CTS with
the main f0972bc4b DRV basis: `set_max_fanout 64` at PRE_GRT, SLEW/CAP_MARGIN 30. OT_HOLD_FF_MARGIN 10 unchanged.

| run | setup TT | hold FF | drv slew TT/FF | fanout | DRC/ant | clock | verdict |
|---|---|---|---|---|---|---|---|
| keep A2 (KITS-18) | +47 | +0.39 | 1477 / 1157 | - | 0/0 | PASS | NOT SIGNED |
| ring_k21m30 | +21.15 | -0.49 (1 ep) | **88 / 55** | 0 | 0/0 | PASS | NOT SIGNED |

GRT ov 0, FF_PRE_ROUTE_HOLD +5.9. Residual: 88/55 slew pins (shared post-route SPEF repair, FLOW-CLOCK-R6) and one hold endpoint -0.49 ps.
Parallel variant `ring/ring_k21m30_pad` (same + OT_IO_HOLD_PAD=1, OT_IO_HOLD_PAD_STAGE=grt, main tools/orfs_hold_mm.tcl) is live.

## bdring: re-kit from main, not built

`intel1 hbm-cores-kits-21/bd/kits/ot_hgi_sm_xload_cl2_bdring_0c99d1c898e0-_k21` (mk_c20 from main f0972bc4b, plan c25c_d16 6ba9f877d23f,
`--ft-pin-dx-um 1.08 --gen-args "--hold-ff-margin 15 --slew-margin 30"`), KIT_PREFLIGHT --contract PASS 0. Its config.mk differs from
_k18 only by PRE_RESIZE_TCL max_fanout.tcl + SLEW/CAP_MARGIN 30 (+ core_grt_pre sources max_fanout.tcl) = the KITS-20 k20vb build
(setup +11.07, hold +6.04, slew 1538/1230, clock TT insertion ~295 FAIL). Not rebuilt: same inputs give the same result. Build it after the
shared SPEF repair lands. The TT pin-flop insertion (~297 vs 250+-40) is a clock/plan item.

## xcal (ot_hbm_svc_sm_xcal_rel_t): GEOM-62 move clears GRT; FF hold stops at GRT on late face-flop clock

`xcal/xcal_k21m5` = xcal_v1 (KITS-18 rst anchor) with u_tab_lo x 15.12 -> 20.16 (+5.04 um E; W channel 10.8 -> 15.84, centre gap 22 -> 17),
main DRV basis (fanout 64, margin 20), GLOBAL_ROUTE_ARGS `-congestion_iterations 50` (clock included). Floorplan -> GRT.
- GRT 50 iterations incl clock: overflow **0** (M2-M5 all 0; was 157 at 30 it). No extra clock-street measure was needed.
- Post-CTS hold gate PASS (rr -49.04 / 244). GRT stopped OT_HOLD_STRUCTURAL: FF hold -155.58, 526 endpoints (limit -100).
- Probe on 4_cts (probe/xcal_hold_cts.txt): in->reg 329 eps, wns -132.34 (rst_n -> u_fcore.rst_q RESETN removal), the rest about -98
  (tgt[*], cfg_data[*] -> u_bin_* face flops). The worst face-flop capture clock is 249 ps at FF against vclk 202.5. On that path the
  leaf `clkbuf_leaf_87` stage is 108.8 ps (level-4 net 63 fF, 12 leaves).
- TT insertion at flops (probe/xcal_ins_tt.txt, placement RC): face 505: p10/p50/p90/max 223.5/264.8/294.8/304.3, 75 outside 250+-40;
  core 2637: 205.4/226.1/268.9/323.4. Root cause: the CTS tree insertion/balance on face flops (same class as the bdring ~297 TT). This
  is not a congestion problem. The IO pad cannot pad rst_n (it skips async pins), and -132 is past the -100 structural limit.

## gq_land density26 (GEOM-64 PASS-COND)

Place GRT 50 (clocks excluded, probe grt50_place.log): overflow 0/0 on both 4ff7e1 and 859e54. CTS + GRT 50 incl clock: ov 0 both.
| kit | post-CTS hold gate | GRT hold repair | FF_PRE_ROUTE_HOLD | result |
|---|---|---|---|---|
| gql_4ff7e1 (reviewed 3_place) | PASS rr -24.83/65, io -63.21/1636 | +10.01 | -6.36 | stop (loss 16.4 > margin 10) |
| gql_859e54 | PASS rr -16.09/107, io -58.75/1637 | +10.00 | -12.61 | stop (loss 22.6) |
859e54 was placed again by make, so its 3_place is NOT the reviewed one (30968/52083 instances moved vs Codex density26; same recipe).
Live variants `gql_*_pad`: from 4_cts, OT_IO_HOLD_PAD=1 at grt (main orfs_hold_mm.tcl) + OT_HOLD_FF_MARGIN 15 (OWNER 12.19).

## hcol_h0 _k17 LEC NEQ 102 -> RTL fix READY claude/hbm-cores-kits-21-hcol-1029@f162cd082 (see that branch)
