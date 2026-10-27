# INFRA-FIRST-QC-R19: QC d43b clock -- variation ledger, spine solve, M8 Min-Step fix, seam-hold form review

Lane INFRA-FIRST-QC-R19 (2026-10-27). Base: claude/qc-mesh-r18-1027@a9ef417d20. Inputs read-only: epyc2 R17 pkg + R17 build
(`/srv/opentallas-scratch2/claude/qc-mesh-r17/pkg/build/tree`, still in DRC). Runs: epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r19/.
Labels: CHECKED = recomputed independently (arithmetic or a control run); UNCHECKED = one tool output.

## Tool changes
- `qc_clk_mesh3.pair_u`: per-pair `var_model` ledger. The MC netlist ends at the fine-mesh tap node; AOCV prices only the
  stages below it (tap buffer + tap->entry stub + 10 core stages). Guard assert if a future MC absorbs the stub.
- `qc_clk_mesh3.mesh(jog_um)` + `solve --spine-jog-um`: a column tap / spine driver off the spine straps joins the nearest
  strap by one perpendicular jog (stub RC). Default 0 = old rule. Fixes "point (2177.28, 1339.2) not on a strap".
- `clock_routed._emit_steps(m8_end_ext)`: vertical (M9-trunk) nets, load drop: the M8 end before the VIA78 gets an
  explicit end extension = 0.08 um (flush with the 0.16 um junction pad). Nothing else in the geometry changes.
- Tests: test_qc_clk_r19.py (new, 2) + 23 existing clock_routed / qc_clk_mesh3 tests pass.

## Numbers
| # | item | value | label |
|---|---|---|---|
| 1 | variation overlap between mesh MC and AOCV, by segment | 0 stages / 0.00 ps. MC = die input -> fine-mesh tap node (mesh() taps = r2 taps[].tap); AOCV = tap buffer + stub (stub median 17.3, max 1849 um) + core 10 stages. R18 double-count suspicion does not hold: same kind of variation, different segments | CHECKED (code read: mesh() netlist, pair_u stage count) |
| 2 | seam hold / kit-window after item 1 | unchanged from R18 f64 by construction: FF zero-logic -85.17, kit W40 core views -1.89 (sl_W2_su_c->sl_W2_su_l1) | UNCHECKED (R18 numbers, no code-path change) |
| 3 | spine solve (drop --no-spine, jog 60 um), TT nominal, model (no RCX fold) | runs. Tap skew 64.20 vs no-spine 25.64; spine tap slew 237-390 ps; insertion 6758.7-6822.9 | UNCHECKED |
| 4 | => spine as planned (2x16w straps on gap rows, 3-column stride) makes nominal WORSE (slew-loaded); not adopted; MC not run | - | UNCHECKED |
| 5 | RCX re-balance of the top tree | NOT DONE in R19 (see Open) | - |
| 6 | R17 DRC Min Step @ M8: cause | all 192 markers (102 boxes so far, 51 nets) = load end of VIA78 on vertical nets: VIA78 M8 enclosure (+-0.027) 5 nm beyond the 0.64-um M8 wire end (x = riser - 0.027) | CHECKED (marker x vs mesh.json riser, all 192) |
| 7 | DRC replay on routed.odb, 102 boxes, OLD encoder (control) / NEW encoder | 198 (192 Min Step, 4 Metal Spacing, 2 Short) / 6 (0 Min Step, 4 Metal Spacing, 2 Short) | UNCHECKED (one tool run; control reproduces R17 class) |
| 8 | remaining 6 markers (3 locations x 2 boxes) | pre-existing (in control too): clock M7 stair vs partition M7 pin at the centre row y 13132.6-13132.8: ckm_w_ckt_20160_0 vs sl_E2_sc/x_ctl_su_c_i[384], ckm_w_ckt_1198_0 vs sl_W0_sc/x_ctl_su_c_i[384] (spacing), ckm_w_ckt_20123_0 vs sl_W3_fe/x_su_l0_ctl_o[284] (short) | UNCHECKED |
| 9 | (a) HB4 residual (R18 f64) | 1,295,752 HB4xp67 x 0.10206 = 0.1322 mm2; adds 0 clock sinks | CHECKED (arith) on UNCHECKED count |
| 10 | (b) lockup latch, 1 per zero-logic seam bit | 1,277,200 DLLx1 x 0.2187 = 0.2793 mm2 (2.1x (a)); adds 1,277,200 clock sinks to the partition local trees | CHECKED (arith) on UNCHECKED bit count |
| 11 | (b) as worded (RECEIVE-side, negative-level) | gives NO hold margin: clocked by the receiver clock it closes on the same rising edge the capture flop holds on, so the hold check just moves to the latch. Half-cycle margin needs the latch on the LAUNCH clock (standard lockup latch: transparent-low on the sender local clock, data released at the sender falling edge) | CHECKED (timing argument) |

## Open (next lane)
- RCX re-balance: the RCX fold is clock-only extraction with empty M7 (R18 #6: k 0.57-0.77 per edge = environment).
  Balancing the merge points to it balances to the wrong environment. Re-extract with the signal environment (combo GRT
  wires or a filled M7 plane) first, then balance merges with the calibrated stage table (plan_d43 PLAN-DELTA).
- 6 M7 clock-stair vs partition-pin markers at the centre row: plan pin-access fix (stair x off the pin column).
- R17 build: collect intel2:~/r17_build.otrun.log R17_BUILD_DONE + build/{drccls.txt,report.out} (DRC 5754/20857 at 02:37, ETA ~04:45).
