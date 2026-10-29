# DIE-QC-35 PROG QC-020 ffh10e: FF-only post-route hold ECO on the ffh10 routed RC (margin 10)

Why: ffh10 routed signoff has ONE FAIL left, FF hold -4.12 / 7 internal reg->reg endpoints (TNS -13.53); everything else
PASS (TT +243.04, pair 78.41/70.86, slew 0, DRC 0, timing_modes PASS). Its GRT->routed hold loss is 10.44 ps, just over
the 10-ps margin, so the residual is repaired on the ROUTED parasitics (12.19 measured arrivals + 10 ps).
Form = the main KV `mk_eco.sh b<N>` with `OT_ECO_FROM=grt` (FLOW-SHARED-10): start from the ffh10 pre-DRT 5_1_grt.odb
(sha256 402d414ad355e48c..) as 4_cts.odb + the ffh10 routed 6_final.spef; ONE detailed route (no re-DRT of a routed DB).
The KV launcher itself is not reusable here (run_kit_kv.sh post), so this dir carries the same steps for the QC kit.

Kit intel2 `/srv/opentallas-scratch2/claude/die-qc-34-kits/prog/kit_ffh10e` (copy of kit_ffh10 files + `config_append.mk`):
- FF-only frame: OT_HOLD_MM 0, CORNERS bc, CORNER BC, OT_VCLK_CORNER=ff (main vclk_corner.tcl binds OT_VCLK_FF 381.14);
  `kit_modes.py check --step eco --session bc --vclk-corner ff --hold-repair` ok, and the hook sources main
  `kit_modes_eco.tcl` (fails closed on a wrong mode).
- PRE_GLOBAL_ROUTE `pre_eco.tcl` = vclk FF binding only. POST `eco_ffh10.tcl`: read routed SPEF, main clk_freeze
  (ot_clk_freeze / ot_clk_freeze_assert), `repair_timing -hold -hold_margin 10 -max_buffer_percent 100
  -allow_setup_violations` (FF frame; TT setup is judged by the routed signoff), DPL, incremental GRT, vclk back to TT,
  PG bind + 0-open. SKIP_INCREMENTAL_REPAIR 1. No clock ECO, no pads/trims.
- Launch: `ot-run --mem 32 --threads 16 --dir KIT -- bash KIT/run_ffh10e.sh KIT 16 32`, unit **oth-ubuntu-860171-1793299876**
  (intel2, started 11:52 PDT, client log intel2 `~/dqc35k/prog_ffh10e.otrun.log`).

Collect: `KIT/run_route.log` (ECO_FFH pre/post, RSZ hold buffers, OT_CLK_FREEZE assert, DRT violations), then
`KIT/signoff/signoff.json`. SIGNED -> then routed LEC + PG census on 6_final (not yet run).

## Results
(pending)
