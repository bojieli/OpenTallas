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

## Results (unit oth-ubuntu-860171-1793299876 exit 1 = signoff verdict, route rc 0, 11:52-12:06 PDT; CHECKED run_route.log + signoff.json)
- ECO: routed-SPEF FF hold before repair -4.115 ps (= ffh10 signoff -4.12, the frame reproduces the sign-off);
  175 endpoints under the 10-ps margin, 196 hold buffers; post (GRT RC) +7.87; clock freeze assert OK (333 clock nets,
  332 clock cells LOCKED/dont_touch, but **0 clock nets had detailed wire** = GRT input DB); PG 0 open / 60,128; DRT 0.
- Routed signoff **NOT SIGNED**: TT setup +247.34, **FF hold +3.61 PASS**, slew/cap 0, DRC 0, antenna 0, timing_modes PASS,
  but **clock FAIL: TT hold-side related pair pcap[815] -> p_q[303] 84.09** (FF 75.23; max side u_hi_wd/q[164] -> u_hi
  79.66 TT / 71.04 FF).
- Reading: same clock cells, different clock DETAILED routes -> the pcap[815] -> p_q[303] pair moved 78.41 (ffh10) ->
  84.09; cand-2 had 85.55. Across three routes of the same tree this pair spans 78.4-85.6 ps, i.e. the tree leaves for
  this pair sit ~80 ps apart by construction and only route noise decides the gate. Structural item (12.8 principle
  first): re-balance the pcap / p_q leaf groups (and the u_hi_wd -> u_hi macro group, 76-80 ps) in the PROG CTS plan.
- Follow-up launched at once: **ffh10r** = the same hooks from the ROUTED ffh10 5_2_route.odb (sha256 ebe156c63c00bb28..;
  the KV mk_eco default OT_ECO_FROM=route form), so clk_freeze keeps the ffh10 clock detailed wires FIXED (pair 78.41 /
  70.86) while the 7 hold endpoints are repaired. Unit **oth-ubuntu-1139601-1793300807**, kit intel2
  `.../prog/kit_ffh10r`, client log `~/dqc35k/prog_ffh10r.otrun.log`. Risk: DRT-1231 on a re-DRT of a routed DB (KV 47ce).
