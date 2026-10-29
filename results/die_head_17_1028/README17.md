# DIE-HEAD-17 (2026-10-28): hd_tile spine sized from ROUTED arrivals (T=525 TT), HEAD die CA/STA re-run at the new tile insertion, reg_spine generator option

Labels: CHECKED = my own tool runs on the named files (not NUMBER-CHECKed). UNCHECKED = estimate.
Runs: intel1:/srv/opentallas-scratch2/claude/die-head-17/kits/{hd_tile,hd_tile_gen}; intel2:/srv/opentallas-scratch2/claude/die-head-17.
Basis: COORD ruling 18:33 (DIE-HEAD-16 ASK default (a)): register target from the routed spine floor, core taps
re-targeted, flow core-tap balance off, then HEAD die CA plan + die STA with the new insertion.

## 1. hd_tile: one CTS + GRT pass with pads from ROUTED arrivals (CHECKED, DIAGNOSTIC outside run_kit)
- Kit: DIE-HEAD-16 p4 kit copy (3_place.odb of DIE-HEAD-14 reused; same v3 trunk, 34 k-means taps, radius 100).
- Pads: `kit/pad17.py` on the DIE-HEAD-16 GRT-RC tap means: pad = max(0, pad_p4 + round((525 - routed mean)/22)),
  276 BUFx4 (p4: 273); routed BUFx4 stage = 22.3 ps (meas16g trunk.txt). Plan: `kit/h17_plan.tcl`.
- Core branches: eA 6 x BUFx4, eB 4 x BUFx4 (P = T - L: eA 525-255 ~ 270, eB 525-231 ~ 294 TT routed, from the
  DIE-HEAD-16 routed natural branch eA 127-146 / eB ~210 (estimate)).
- Flow tap_balance: OT_TAP_REPORT_ONLY=1 (no core re-hang), OT_TAP_TARGET_PS=525, OT_VCLK 525/420.
- Run: `make cts` + `make grt` (SKIP_INCREMENTAL_REPAIR=1, 50 congestion it), POST_GLOBAL_ROUTE hook
  `kit/h17_grtmeas.tcl` writes the GRT-RC SPEF; FF/TT measurement on 5_1_grt.odb + that SPEF (`kit/meas17.tcl`,
  `kit/ps17_regonly.tcl`, pair_skew.tcl unchanged).

Results (routed GRT RC):
| item | TT | FF |
|---|---|---|
| GRT overflow M2-M7 | 0 (extra it 1/50, WL 1.519 m) | |
| register insertion min / p50 / p99 / max | 458.6 / 523.6 / 537.4 / 545.3 | 370.4 / 411.1 / 432.5 / 445.7 |
| tap means (34 taps) | 511.7 .. 533.0 (21.3 spread) | 397.9 .. 433.0 |
| reg<->reg related pairs, CPPR (setup-side / hold-side worst) | 71.3 / 39.2 | 53.9 / 36.9 |
| max clock-pin slew | 131 ps (no clock-net slew/cap violator; MPW 0) | 130 ps |
| core pins eA0..3 / eB | 248-262 / 282 | 197-211 / 227 |
| core effective (pin + signed internal) eA / eB | 503.5-516.9 / 512.9 | 405-419 / 416 (FF internal 208.3/189.3) |
Placement RC at CTS (log): regs 513..648, cores 313-351 (placement RC is 20-25 % slower on the long trunk nets).
- Balance: tap means within 21 ps; in-tap spread 3-25 ps except tap 17 (HR2, 70 ps: a few sinks at 459.6 on a short
  TritonCTS branch; local-tree residual, recorded, not padded).
- All-pair pair_skew (TT 291.8 / FF 231.3) is reg -> core pin: pair_skew.tcl does not add the core internal latency.
  With it the worst core offset is eA0 503.5 vs reg p50 523.6 (-20 TT), FF eA0 405 vs 411.
- Data-net slew violators (RESETN/A/D: 255 TT / 195 FF pins) are pre-repair data nets (SKIP_INCREMENTAL_REPAIR), not clock.
- Render `routed/spine_p5.png` (VIEWED): trunk in the x 354 channel / y 368 cross row / y 726 strip and express chains
  to the upper hubs; trunk cells within 13.1 um of their plan points after DPL; tap drivers outside the hard cores.

## 2. HEAD die CA plan + die STA with the new hd_tile insertion (CHECKED, tools = main 8e38d8187f)
`die_ca/run_ca17.sh` = DIE-HEAD-15 run_ca15.sh with ONE change: the partition-internal latency (plan
clock.common_latency_ps copy, --sta-core-latency-ff / --core-latency-ff, landed_phase_ocv --core-lat,
count_align_plan --corner key). Shared model unchanged (clock_variation=table, inv2, spice cal, shared droop, CPPR LCA).
The uniform latency is applied to every partition (264/326 are hd_tile; conservative OCV for the other types).
| run | lat TT/FF | start tree | CA plan min | MC 2000 | die STA TT / FF | start-skew |
|---|---|---|---|---|---|---|
| base250 (repro of DIE-HEAD-15) | 250 / 202.5 | 170 stages | 161.5 | 0 viol | 161.3 / 182.9 PASS | 0/495 |
| p50, old 170-stage set | 523.6 / 411.1 | plan 296 nodes | 138.4 | 0 viol | 138.2 / 166.6 PASS | 0/621 |
| max, old 170-stage set | 545.3 / 445.7 | plan 358 nodes | 136.8 | 0 viol | 136.6 / 163.9 PASS | 0/683 |
| **max, re-emitted 358 stages, pass 2 (GATE)** | 545.3 / 445.7 | 358 stages, 1432 flops | 136.1 | 0 viol | **136.0 / 163.8 PASS** | **0/683** |
- Gate run = max register insertion (conservative): start stages re-emitted from the 545.3 bind (`iter17.sh`), swapped
  into the DIE-HEAD-14 die combo, die combo GRT incl. clock TT+FF overflow 0 (`combo_grt_max_2.txt`), CA chain;
  427 crossings all D4, 0 FAIL, 0 below 100 ps, OCV table max 200.1 TT / 170.0 FF. Pass 2 re-emit is IDENTICAL
  to pass 1 (`converge.txt`, 358 stages, 0 diffs).
- Cost of the deeper tile clock: the reset start tree grows from 15 to 191 retime nodes (170 -> 358 stages, 654 -> 1432
  start flops) because the larger unshared tile latency widens each start interval; CA min margin drops 25 ps TT / 19 ps FF.
- SS x1.27 INFO: worst lo 73.8, 8 fails (INFO, never gates).

## 3. reg_spine generator option (branch claude/die-head-17-regspine-1028, ROOT-MERGE needed: shared tool)
`partition_types.<t>.reg_spine` (opt-in; spec = `kit/reg_spine_hd_tile.json`). gen_phys copies reg_spine.json/.py/.tcl,
appends `source /work/reg_spine.tcl` to pre_cts.tcl and sets OT_TAP_REPORT_ONLY=1; absent = kit byte-identical (test).
On the hd_tile kit (hd_tile_gen) the generated form reproduces the DIE-HEAD-17 diagnostic CTS exactly
(same 34 taps / 276 pads / assignment, OT_TAP_RC 513..648 and core pins 313-351 identical). Tests: 24 PASS
(test_gen_phys_reg_spine 5 + pg_island_cut, clock_landing, core_pg_connect, bump_ports).

## Open
- Pads are derived from a routed pass of the same plan (COORD (a)); all 34 taps carry them -> ASK whether this is
  plan data (12.8 d1, calibrated) or a residual (12.8 d2, would not be sparse). Default: plan data, recorded in the spec.
- hd_tile still needs the run_kit gate run (hold gate) after FLOW-GEN-2's CTS-0114 + fclk_out_o relay fix (not READY yet).
- h14-grt (intel1 die-head-14) still in post-GRT repair (WNS -472, it 1080+); 5_1_grt.odb not written; render pending.
