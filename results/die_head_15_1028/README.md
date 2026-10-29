# DIE-HEAD-15 (2026-10-28): start-stage re-emit on the inv2-calibrated plan, and an hd_tile early-core-tap diagnostic

Labels: CHECKED means my own tool runs on the named files (not NUMBER-CHECKed). ESTIMATE means a model claim.
Runs are on intel2 under /srv/opentallas-scratch2/claude/die-head-15 and on intel1 under /srv/opentallas-scratch2/claude/die-head-15/kits/hd_tile.

## 1. start_stage_emit on the DIE-HEAD-14 plan (CHECKED)
Inputs:
- The DIE-HEAD-14 bind is clk14/ca/bind.json (inv2 r200, 495 start edges).
- The base tree is die-head-11/inv/g5_r200/clk. Its tree.json md5 equals the clk14 tree.

Emitted stage set (`start_stages.json`):
- 170 stages, one per plan virtual node; 653 flops.
- Against the old 193-stage set: 155 kept, 15 added, 38 dropped.
- Max distance from node cell to stage is 4.86 um.

Measurement and gate:
- Stage taps were swapped into the DIE-HEAD-14 die combo (`swap_st.py`); the rest of combo.tcl is byte-identical.
- Die combo GRT incl. clock, 50 iterations: overflow 0 at TT and at FF.
- CA re-plan, bind and die STA on main b518deaf15 (`run_ca15.sh`): 427 D4, 0 FAIL, plan min 161.5, MC 2000 with 0 violations, 495/495 start edges clean.
- Die STA: TT PASS 161.3, FF PASS 182.9. Start-skew 0/495. SS-INFO start-skew went from 26/495 to 2/495.

Convergence:
- Re-emitting from the measured plan does not reproduce the set exactly.
- Each pass moves one stage by one node along the r9 repeater chain (r9_10 -> r9_11 -> r9_17) and flips up to 3 EDGE_FALL picks (b6/b9/b13), which are near-ties.
- The gate numbers stay the same across passes (TT 161.3, FF 182.9 PASS).

## 2. hd_tile early core taps (12.3 v5.0): estimate and CTS-only diagnostic (`h15_coretaps.tcl`, kit-local, DIAGNOSTIC)
See `ESTIMATE_hd_tile_clock.md`.

The prototype:
- The clk entry drives a root-split BUFx24 that feeds all register sinks; TritonCTS builds only that net (`-clk_nets`).
- Each core gets a dedicated branch: BUFx4 delay stages placed at the driver end, plus a BUFx24 leg driver.
- There is no macro tree and no CTS-0033 balancing.
- Run: CTS only, SKIP_CTS_REPAIR_TIMING, tap_balance report-only. Arrivals use placement RC.

Results (CHECKED):
- Core pins, TT: eA 299.0-334.2, eB 325.0.
- Core pins, FF: eA 252.8-280.0, eB 272.1.
- Pin slew: eB 163 ps. eA about 300 ps, because repair_clock_nets repeated the over-core leg down the channel.
- Every delay stage has input slew <= 61 ps, and no slew is over 320 ps. DIE-HEAD-14 had 1026 and 703 ps.

Measured branch delays:
- Entry: 35 ps.
- BUFx4: 22 ps per stage.
- eA leg after the driver: 117-153 ps.
- eB: 2 hops of 49+50 ps, then a leg of 51 ps.

The estimate under-counted the leg and the entry. With 0 delay stages the natural branch already lands near the target pin arrival (eA about 190-225 vs 194.8 TT; eB about 259 vs 219.3 TT). The plan therefore takes 0 delay stages for eA and eB. No padding is needed.

Register tree (TritonCTS, root split near the cross):
- 25,739 regs at 748-1119 ps TT (p50 793, p99 1095) and 642 ps FF median.
- Path depth 19-22, average sink wire 854 um.
- This is unchanged from DIE-HEAD-14 (735-1082). It is 1.75x the 450 ps budget, with 370 ps of spread inside the tree.
- The cores are no longer the worst pair; the register tree is.

Worst related pair:
- TT max -800.5: u_rst_in at 1083 -> u_rrl_4 at 290, crpr 0.
- 8 u_srl/u_rrl flops sit at 290 ps, on the entry / forwarded-clock (fclk_out_o) net, outside the tree.

DPL moved the root-split cell to y 516.5. The die-island row y 349.9-358.6 crosses the channel cross.

Next: the register tree as a plan-placed spine plus local trees (12.13b local form), T = 450 TT / 380 FF.
