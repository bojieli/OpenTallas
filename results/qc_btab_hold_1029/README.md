# QC BTAB turntree d2837604267e: root cause of hold -27.50 / pair 84.4 / slew 31 (DIE-QC-28, 2026-10-29)

Diagnostic only (no build, no kit change). Failed run: intel1
`codex-qc-btab-0251/kits_route_compat/qfd_dv_s8x_btab_turntree` (src codex/qc-btab-compat-0320@e1abe5d04, M5 DRT,
NOT SIGNED: FF hold -27.50/1060, TT pair 84.42 (FF 78.39), slew 31/19, cap 3/3, DRC 6).
Probes: the kit's own signoff FF session (`grt_measured_session.tcl`) re-run on `5_1_grt.odb` with the kit's
GRT parasitics (setRC_rcx + OT_RC_CAL M6/M7 0.014/0.105, `estimate_parasitics -global_routing`), docker 12 GB cap.

## 1. Hold: wrong IO frame at GRT repair (CHECKED)
| frame | FF boundary pin-flop mean (1318 regs) | FF hold WNS / viol |
|---|---|---|
| GRT repair (kit vclk_ff.sdc, declared) | bound 202.5 | +12.10 / 0 (5_1_grt.log) |
| GRT RC, measured mean (this probe) | **175.39** | **-15.99 / 1060** |
| routed RCX sign-off, measured mean | 191.22 | -27.50 / 1060 |
GRT repair timed the IO launch 27.1 ps late (202.5 vs its own 175.39 mean) and so saw none of the 1060 input-hold
violators. Fix = the existing shared opt-in `kit_modes.py stage --measured-hold` (OT_MM_MEASURED_HOLD, rebind kits;
this kit is ff_vclk=rebind) so repair binds the GRT-RC mean. Residual after the frame (per-register GRT->RCX
deviation, -27.50 vs -15.99 after the common offset) = ~11.5 ps here -> hold repair margin must be >= ~15 ps
(OT_HOLD_FF_MARGIN 5 today) -- ESTIMATE, UNCHECKED: FF hold ~ +3 ps after both.

## 2. Pair skew / slew / cap: clock does not follow data at the btcap capture column (CHECKED)
GRT RC: pair max 41.08 / slew 0 / cap 0. Routed: 84.42 / 31 / 3. All the degradation is routed-only.
Leaf stage delays routed vs GRT (`leaf_table.txt`): 9 macro-capture leaves mp_ck_Tpqp{y,z,a,w,x,b} / Tpqs{x,w,a}
(fanout 1-3, BUFx8..x12f) grow +10..+40 ps (Tpqpy 46.0 -> 85.6). Geometry (`geo.tcl`, 6_final.odb):
the plan sites these leaves at x 44-83 um (core_infra_plan.json), but their 1-3 btcap sinks were placed at x 111-112
(e.g. Tpqpy at (77.3, 86.1) -> btcap[591]/[588] at (111.1, 85.5)), a 30-68 um single-sink leaf wire that routes
through the congested centre-street region (GEOM-52/53 channel hotspot). Same column: btcap D slew 330-410 ps from
g_btb[*].u_m rd_out (cap 49.9 > 46.1).
Structural fix (12.13 clock follows data; plan-computed per-tap siting allowed): re-site/merge the macro-capture
leaves at the placed btcap column (one leaf per btcap cluster within ~10 um, like Tpqrv fo30 = 29-37 ps), and pin
the btcap capture flops pin-adjacent to the SRAM rd_out column (anchors) so rd_out drives a short wire.
ESTIMATE, UNCHECKED: removes the +25-40 ps routed tail -> pair ~50 ps, slew/cap 0.

## 3. DRC 6 (not diagnosed further)
6 M4 shorts at g_btb[3].u_m W pin column x 253.3-254.6, y 91.4-96.7 (bt_rd[772/788/828], net5202, VDD):
macro pin-access vs PG edge; needs the SRAM pin-column keep-off strip to cover this column.

## Next (BTAB owner)
ONE successor M5 kit = measured-hold + FF hold margin 15 + re-sited btcap leaves/anchors + pin-column keep-off,
GEOM render, then GRT>=50 + DRT. No M6 (no explicit BTAB obs_max budget). Not launched: per 12.14 estimate-before-build
the as-is kit with measured-hold alone still fails pair/slew/DRC.
