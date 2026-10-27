# INFRA-FIRST-QC-R20: plan_d43 adoption, die GRT signals + clock, per-endpoint HB4, solver-set MC stub flag

Lane INFRA-FIRST-QC-R20 (2026-10-27). Base: claude/qc-mesh-r19-1027@547ff4cad4. Runs: epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r20/.
Labels: CHECKED = recomputed independently (arithmetic, a control run or an independent reference); UNCHECKED = one tool output.

## Tool changes
- `results/qc_clk_mesh3/r17/scripts/r11_hb_count.py` (NUMBER-CHECK-QC-R19 floor bug): `tport` now starts at -inf, not 0.0.
  Before this fix, every bus with zero residual still padded 12.28 ps and got 1 cell per bit. `ncell()` returns 0 when the pad is <= 0.
  New `--per-endpoint`: each capture instance bus is sized for its own demand (the KV NUMBER-CHECK-KV-R18 form).
  The output now reports `bits_needing_fix` and `sizing`.
- `qc_clk_mesh3.py`: the solver writes `mc_includes_stub=False` and `mc_segment` into every solve JSON. `collect` requires
  the flag and rejects solves that disagree. `pairs` / `sta-export` set `pair_u.mc_includes_stub` from the solve docs
  (`_set_mc_stub_flag`), so the R19 guard now fires if a future solve absorbs the tap stub.
- `die_clock_128.TrackRouter.place(keep=, dry=)` + `_fixed_wires_stack` channel keep-in, and `die_clock_mesh.build_explicit`
  spec key `channel_keep`. All of this is OPT-IN (default off): the default output is unchanged (control build `tree_nk` = R17 d43b geometry).
- Tests: test_qc_clk_r20.py (new, 2) + die_clock_mesh / clock_routed* / qc_clk_r19 / qc_clk_mesh3: all pass.

## Numbers
| # | item | value | label |
|---|---|---|---|
| 1 | plan adopted for the QC infra event | plan_d43 sha256 f2c91d0338ee83f2..., origins = R16 G0-passed delta (r17_delta_inputs check) | CHECKED (sha recomputed; origins check R17) |
| 2 | die GRT signals + fixed clock (combo on basekit = kit ft signals + reset, 4646 fixed clock nets), limit 50 congestion iterations | routed 485,898 nets (= 485,897 ft bits + 1 reset); overflow 0 / 0 / 0 on every layer; no congestion iteration needed | net count CHECKED (= kit ft_bits + reset); overflow UNCHECKED (one GRT run) |
| 3 | GRT usage M4/M5/M6/M7/M8/M9, total | 3.38 / 6.08 / 3.80 / 7.29 / 0.58 / 1.06 %, total 2.89 %; wirelength 598.27 m; 1,237,389 vias | UNCHECKED |
| 4 | R17 combo, for comparison | clock-alone kit: routed 0 signal nets (so R17 "GRT" was clock only) | CHECKED (ODB census: 4648 nets, 4646 clock) |
| 5 | HB4, fixed floor, type-port sizing | 947,116 cells / 0.0967 mm2 (928,564 bits padded) | UNCHECKED |
| 6 | **HB4, per endpoint (gate form)** | **631,684 cells / 0.0645 mm2; 630,140 of 1,277,200 seam bits need a fix (628,596 x 1 cell, 1,544 x 2 cells)** | CHECKED (= NUMBER-CHECK-QC-R19 reference 631,684 / 0.0645 / 630,140) |
| 7 | R18/R19 1,295,752 cells / 0.132 mm2 | WITHDRAWN (0.0 floor bug) | CHECKED (cause) |
| 8 | (b) launch-side lockup latch cost, 1 per bit that needs a fix | 630,140 DLLx1 x 0.2187 = 0.1378 mm2 + 630,140 new clock sinks (2.1x the HB4 area) | CHECKED (arith) on a CHECKED bit count |
| 9 | HB4 TT setup cost, worst endpoint (2 cells) | 165.99 ps vs the R18 TT seam setup +565.40 | UNCHECKED (R18 STA) |
| 10 | 6 centre-row M7 markers: root cause | 5 pin stacks, on 3 nets (ckm_w_ckt_1198_0 drv + 2 loads, ckm_w_ckt_20160_0, ckm_w_ckt_20123_0), all on channel lane 0 (pin y 13132.935, 0.135 above the channel edge 13132.8). The router put their M8 trunk on 13131.56, outside the channel, so the 1.375 M7 riser crosses the partition face at the partition M7 pin rows. 0 other channel stacks leave the channel (of 266 counted) | CHECKED (stack census on mesh.json vs channel rect) |
| 11 | keep-in fix trial (trunk forced inside the channel) | FAILS: nearest legal in-channel M8 track is 6.115 um away (> STACK_RISER_MAX 2.5) and cascades: 72 plan errors (no_pin_stack 45, reserve_overflow 19, no_clock_track 8). Kept opt-in/off | CHECKED (control build without keep = 0 errors) |

## Open (next lane)
- Plan fix for item 10: move channel lane 0 up by one row pitch, so the lane-0 lower unit's trunk track lands inside the channel.
  Or (R19 option) move the 3 drivers along x so their riser misses the partition pin columns.
  Either way the change goes into the plan event with the merge rebalance.
- Clock RCX with the signal environment: the GRT guides (sig/route_TT.guide) give per-gcell signal demand next to each
  clock segment. They feed a filled-M7/M6 environment for RCX, or a detailed route of the clock + ft nets. Then rebalance
  the top-tree merges on those delays (plan-computed) and run the related-pair die STA with per-endpoint HB4. The seam hold,
  kit window and coverage numbers are owed by that run, and both hold-form builds start after it.
- QC-KITS-1 plan-event needs (COORD 03:0x): island lists for the 66 types from the FINAL tree (after the rebalance),
  the master-plan marker + slices (12.7c), and a repo-relative 88-type bind manifest (QC-KITS-1 recipe bind_d43_recipe.sh).
- R17 build: DRC ~10.3k/20.9k boxes at 03:27; collect intel2:~/r17_build.otrun.log R17_BUILD_DONE + epyc2 .../qc-mesh-r17/pkg/build/{drccls.txt,report.out}.

Renders (viewed): grt/r20_grt.png (M4-M5 / M6-M7 / M8-M9 guide density, partitions, clock wires: regular per-column
pattern, densest in the core rows y 10.5-15 mm, M8/M9 signal use small, no hot spot); grt/r20_grt_chan.png (centre
channel: the x-tree stays inside the 43.2 band, signal guides cross only at the column lanes).
