# HEAD-PLAN-PG: fold the HEAD-5 PG grid into the HEAD R20 plan (one HEAD plan event)

COORD 2026-10-27 12:35 PG-GRID-AUDIT ruling (1) (one-grid rule: plan die.pg.grid == IR-signoff grid == clock/GRT grid).
Branch claude/head-plan-pg-1027 = claude/head-r20-plan-1027@bde8765399 (COORD 13:0x: newest HEAD plan delta; its plan file is
byte-identical to c588bb0171) + this delta.

## Delta
- physical/die_plan/s81_head/die_plan.json: die.pg.grid M9 width_um 6.48 -> 12.96 (pitch 34.56, offset 17.28, VDD/VSS unchanged);
  M8 0.48@4.32 already in the plan. Nothing else changes (plan_vs_c588bb0171.diff = 1 line).
- die.pg of the result == die.pg of HEAD-5 plan 33029005 (checks/pg_equals_33029005.out: True).
- Plan sha256 20a6805a... (R20) -> a65ffa259c46f21dfdd20c1e30e89420e756d6a07e99056701851504ade0fc17.

## Gates (CHECKED, tool output)
- G0 PASS 0E/6W, G0C (--completeness) PASS 0E/6W, 16/16 types clean (g0/, g0c/, *.log). Reports identical to R20 apart from the plan path;
  same 6 WARNs.
- Tests: test_head_r20_island_riser.py + test_head_r19_pins.py + die_plan/test_schema.py: 25 PASS (python:3.12 docker).

## Die GRT on the folded plan (CHECKED, grt/grt_final.txt)
g2.py die probe generated from THIS plan (probe.tcl == GEOM-27 probe apart from the iteration budget; write_guides added as GEOM-27),
global_route -congestion_iterations 50 (owner rule: judge die GRT at >= 50): converged after 4 extra iterations, overflow 0 on all layers;
M9 resource 100,335,186 demand 72,676 (0.07%), M8 0.01%. Routed nets 2 (die-top clk spine + reset: the HEAD plan has no die-level M8/M9
signal lanes). M9 per-450-um window (checks/m9win.out): worst incl. 3 clock straps 0.7% of free M9 (gate 60%) PASS.
Run intel1:/srv/opentallas-scratch2/claude/head-plan-pg-1027/g2b/die.

## IR on the canonical deck (PDNSim, own run; checks/nc_ir.out)
Bump-survey deck: 150-um C4, 70-um pad plates (pad model from claude/infra-head5-1027@e5f4fb2cd tools), VDD drop + VSS bounce co-located per
43.2-um load block, uniform 1.258 W/mm2 tile basis, pg.domains dropped, 2972-um windows on the folded plan, +5.13 mV below-M7 (HEAD-5 slice).
| window | above M7 (co-located) | + below M7 | verdict (<=35 mV) |
|---|---|---|---|
| int (7292..10264)^2, interior | 23.16 (VDD 13.51 / VSS 13.68) | 28.29 | PASS |
| edgeW x 0..2972 (real die W edge), die-edge band x<450 | 22.93 | 28.06 | PASS |
| edgeW, inner x>=450 | 23.12 | 28.25 | PASS |
On the R20 plan grid (M9 6.48) the same deck gives 38.8 + 5.13 = 43.9 FAIL (PG-GRID-AUDIT).
NUMBER-CHECK: (a) checks/nc_ir.py is an own parser (no infra_pg / irsum import); it reproduces the audit summary 23.16 exactly;
(b) the int kit's pdn.tcl and ir_VDD/ir_VSS.csv are byte-identical to the independent PG-GRID-AUDIT G12_p70_int run -> plan grid == IR grid.
Runs epyc2:/srv/opentallas-scratch2/claude/head-plan-pg-1027/kits/G12_p70_{int,edgeW} (PDNSim 1229/1247 s, 40 GB cap).
Open-window-edge rows (up to 51.8 / 77.2 mV) are the known window artefact, excluded as in HEAD-5/NUMBER-CHECK.

## M9 strap re-probe (checks/strap_reprobe.py, own code, CHECKED)
R19 tree straps (claude/head-r19-tree-1027@6acfb0b663 straps.json) on the folded plan: 95 M9 straps, 0 SHORT, 0 spacing < 1.0, min gap
1.16 um (= GEOM-27 / HEAD-CORE-R20). Spine trunk lane 8769.6: 2.00 um to the nearest stripe (OK; the node 8760.96 sits on a VDD centre, which is
why the 8.64 riser exists). M8 grid unchanged (122 rows, 0 shorts, edge gap 0.66 um, same as R20).

## Renders (viewed)
render/pg_tile_zoom.png (one hd_tile: 12.96 stripes, 70-um pads each over ~2 same-net stripes, green M9 / purple M8 clock straps in the gaps,
max jog 0.00); render/pg_strap_zoom.png (a re-snapped strap 4707.96 in the VSS/VDD gap); render/pg_trunk_zoom.png (trunk lane 8769.6 in the
gap next to the VDD stripe at 8760.96); render/ir_colocated_int.png (interior 10-25 mV, hot rows only at the open window edges).
