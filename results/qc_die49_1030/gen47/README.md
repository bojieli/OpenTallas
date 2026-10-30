# DIE-QC-49/gen47: QC freeze-gate chain on the plan_qc47 die clock tree (2026-10-30)

Tree: gen47 `tree.json` sha 4bad7469 (48,296 CKINVDCx16, 7,889 taps), built on plan_qc47 01087c6f. Die target: plan_qc49
9deec4c7 (= plan_qc47 + type-internal group_rects / stm landing bands; no die clock change). All numbers are this
lane's own, UNCHECKED by NUMBER-CHECK unless marked as exact counts.

## Verdict
NOT FROZEN yet. GRT0 incl clock passes and clock geometry passes. Related-pair TT setup passes only when the clock wires
carry the planned NDR RC. It fails on GRT's default 1x-width RC. The authoritative arrival is the drawn NDR clock (fixed
prebuild + RCX), and this chain does not have it yet. The provider and PG access are also not in this source.

## (0) Kit abstract GRT (early indicator only)
`grt/kit_abstract_grt.log`: total overflow 0, max H/V 0/0, 485,898 nets, WL 598.30 m. The log says "Found 0 clock
nets". The kit GRT routes die signals only, with the clock tracks reserved as obstructions. It is not GRT0 incl clock.

## (1) Source rebuilt from the kit ctree.v
- main `tools/clk/native_clock_source.py` on a plan_qc49 native target (`scripts/run_target49.sh`; abstracts with
  landing and reset infra; placement identical to the gen47 kit).
- Result: CONNECTED_UNROUTED. 48,296 cells, all on actual R0 row/sites (0 legalization moves needed). 7,889 taps are
  single M7 rects at exactly the planned xy, including the 4 moved PHY taps. Root at 17007.84, 12463.2.
- No old clock ids or provider bindings are carried. The old 2249 source binds 3,266 start-provider clock ports by
  old node id (t_st_bN__clk -> ck_bN). In gen47, 317 of those nodes are gone and the rest moved (p90 1.86 mm,
  max 32 mm), so those bindings are invalid on the new tree.

## (2) Die GRT including the clock (`scripts/grt_src.tcl`, 50 iterations)
Signal M4-M9, clock M8-M9, adjustments as in the kit. The 79,025 kit clock-reservation obstructions were removed
(the clock now routes there). The 13,304 full-span PG stripes were kept. The 313 pinless provider ports were dropped.

| item | result |
|---|---|
| total overflow | 0 |
| max H/V | 0/0 |
| nets routed | 540,737, incl. 48,297 clock nets |
| wire length | 604.25 m |
| usage | 2.96% |

The TT and FF runs are identical.

## (3) Related-pair die STA
Shared main `die_sta_related.py`, DIE-QC-45 args: `--cppr-lca --clock-ocv table --clock-droop shared
--clock-cal spice_edge`, droop regions = the 313 region trees. Arrivals come from a both-edge readout on
`estimate_parasitics -global_routing`. Polarity: 0 odd taps, 0 ambiguous.

| arrivals | TT intra setup | TT seam setup | FF intra / seam setup | skew diag intra / seam (TT) |
|---|---|---|---|---|
| 1x GRT RC (`sta_1x`) | **-73.93 ps (2,609 neg)** | +18.25 | +47.96 / +124.17 | 273 / 254 |
| planned NDR RC on M8/M9 (`sta_ndr`) | **+38.74 ps (0 neg)** | +160.73 | +160.21 / +268.47 | 195 / 204 |

- Worst pair: c_E1_bn_11 clk_t12 -> clk_c0 (early core tap, 16 stages shorter, raw damage 689 ps). Every worst region
  is a c_*_{bf,bn,tf,tn}_1x region.
- Cause:
  - The tree was priced with NDR M8/M9 wire (meta wire_r 0.00434 kOhm/um). GRT's 1x M8/M9 wire is 8.4-8.9 Ohm/um,
    about 2x R.
  - Even with NDR RC, the routed arrivals are a median +1.6 ns above the kit placement-RC estimate (via stacks and
    pin access).
  - The declared early-tap offsets therefore mismatch the routed stage delay.
- Hold: BLOCKED(kits). There are 0 measured pairs because QC has no signed views, so hold is UNMEASURED under 12.19,
  not a failure.
- Landed: the +-T/2 window says FAIL, but QC has no count_align_bind file, so this stays UNMEASURED, as in DIE-QC-45.
- Slew: max tap 70.4 ps (1x) / 51.6 ps (NDR) at TT; max clock cell 112 / 99 ps.
- Skew vs 80 ps is a target only (12.4a).

## (4) Clock geometry
`geom47.json` + `render47.png` (viewed):
- 0 cells inside the 5 PHY body keep-outs
- 0 legs over 405 um (max 398.142)
- 0 off-lattice
- 5 cells in the planned 8.2-um SerDes gap row

## What remains for the freeze gate (proposed, no plan change)
1. Re-emit the start/reset provider on the gen47 tree (`start_stage_emit.py emit` with the gen47 ctree + proof, then
   synth / import / leaf drivers). The old provider bindings are invalid.
2. Fixed NDR clock prebuild (`tools/clk/fixed_tree_provider.py` / die_clock_128 backbone) on this source, then the PG
   access plan + apply, then the 50-iteration GRT with the clock fixed, then RCX clock SPEF and the readout. This is
   the 2249 chain with new inputs.
3. If drawn NDR arrivals still give TT intra setup below 0: refit the early-tap offsets of the c_*_1x regions on the
   routed stage delay (ot_clk refit --placed-stages), as DIE-QC-45 already proposed for the c_*_11 regions.
