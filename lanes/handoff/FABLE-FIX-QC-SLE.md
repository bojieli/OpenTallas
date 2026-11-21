# FABLE-FIX-QC-SLE handoff (Fable, 2026-11-20 23:2x - 11-21 00:1x PST). Stood down on context; NO kit launched, nothing cancelled, nothing pushed.

## Result: sle_ctl flat GRT overflow = structural (plan geometry + a generator blind spot). No relaunch or GRT setting helps.
Evidence (read-only):
- epyc10 /srv/opentallas-scratch2/claude/ot-jobs/sle_ctl__cla4f6f12f-route-civil-redfish-276253-1795122318/work/run/reports/asap7/*/base/congestion-{10,15,20,5}.rpt
  (20,000-marker cap per report): it10 40.2k -> it20 39.0k, flat. H 20.6k / V 18.4k.
- placed dump epyc9 .../kit-wave/qwen_compute/s29q103S4Q9N46C/items/sle_ctl__cl372cea1c/geom/geom.tsv (same cores, same rows).
- Cores (block M1-M5; over them only M7 V cap 6/gcell vs 27 open, M6+M8 H 8 vs 26):
  u_u_tap qfd_dv_s8_tap_bounded 302.4x129.6 at (164.172,328.332): S face 2,634 M5 pins (hw 1,567 out, xt_d 1,024 in), E face 460 M4 (hr_q in).
  u_u_ctl qfd_dv_s5_ctl_repair4_leaf 345.6x259.2 at (475.212,336.972): S 2,102, N 1,156, W 928, E 712 pins.
Overflow map (20-um bins, it20):
1. ~50%: the 8.64-um slit x466.6-475.2 between tap E face and ctl W face. 879 pins face each other there (tap hr_q 453+7, ctl own_ch ~337,
   cc_o 50, stn_cfg 29, ag_own 10) against ~415 derated V tracks, and the slit is filled to ~100% by evicted cells (400-800 cells per 20 um).
2. ~35%: row y300-360 under the ctl S face, x540-700 (H cap 26 open-air overflow + V cap 6 over the core).
3. ~10%: tap N edge y420-460, x300-480.
Cause of 2, 3 and of the slit fill: istations.tcl sites per-bit station flops ON the cores. is_bits/ff_put_near know no core
blockage, DPL evicts the flops to the core edges. V0E/R4A4: b_hw_hc1_o_0 (1,574, row y=400 in tap) lands y~463 + 189 in the slit;
b_hw_hc2_o_0 (1,574, row y=400 in ctl) lands y320-335 on the ctl S pins; b_tw_data_st_a_o_0/1 (columns x659 / x328 through ctl / tap),
x_fw_o_0 (inside ctl). Three 1,574-bit banks on a core pin face; their wires then cross the cores on M7.
Why no check caught it: kit_istations.core_chain_geometry_errors / chain_macro_hits runs only on rows with a `core` key; these rows
(launch/capture u_tap / u_ctl, bit_route per_bit) have none. istation_clear.py tests the regs_um centroid points, while the kit sites
every bit on its own L route from leaf_um (is_knee_site). The plan check and the kit use two different site models.

## V1 (s29q103S4Q9N46R6V1) still has it: 6,548 per-bit sites inside cores, 4,124 bit routes crossing a core (evaluator below)
b_hw_hc1_o leaf still (440,400) = inside tap (1,574 + 952 sites in tap); b_hw_hc2_o row y328.4 = tap S edge / 8.6 um under the ctl S pins,
stage 3 (646 sites) inside ctl; b_tw_data_st_a_o 737 + 749 in ctl / tap; x_fw_o_0 632 on the ctl W edge (the slit); ft cws1 last
station (412,327) on the tap S edge, cws2 last (662,336) on the ctl S edge. The V1 kit (epyc7 dpkit-sle_ctl__cla4f6f12f-2431677, placed
~23:3x) will show the same GRT class: read its congestion before spending iterations on it.

## Tools (this lane, estimator only, not on main): lanes/handoff/FABLE-FIX-QC-SLE-ev.py, -census.py
- ev.py PLAN TYPE [OVERRIDES.json]: per chain, sites in core per stage, routes crossing which core, worst hop; overrides = leaf_um,
  leg_order, n, channel_um per bus + core_origin per core (try rows before a compose). Python port of is_knee_site (out chains).
- census.py PLAN [TYPE_RE]: all types. V1 result lanes/handoff/FABLE-FIX-QC-SLE-census-v1.tsv: 5 of 36 QC types with per-bit out chains
  put stations in hard cores: sle_ctl__cla4f6f12f 4,696; sle_su_c 4,359; slw_su_c__cl92142dac 4,830; slw_su_c__cl19bb38ef 3,978;
  slw_st_a_v2__cl9f076a5c 920 (x_st_b_o 460 x2 in u_r2). Same class, all unsigned. PLACE-PRECHECK-2330 / PRECHECK-1119: fold in.
Work dir epyc9 /srv/opentallas-scratch2/claude/fable-fix-qc-sle (ev.py, census.py, ov1.json, census_v1.tsv, ev_cache.pkl, lane clone
`clone` on branch claude/fable-fix-qc-sle at f453583d58, no commits).

## Rows for QC-PLAN-R8 V2 (lanes/handoff/FABLE-FIX-QC-SLE-rows.json)
A. Zero cycles, same station counts, checked ONLY with ev.py (not through compose / G0 / bind / GEN):
   - sle_ctl__cla4f6f12f bus:b_hw_hc1_o leaf_um [440,400] -> [265.0,318.0]: sites in tap 2,526 -> 0, worst kit hop 313 -> 260 um.
     950 bits then cross tap on M7 without a station (30% of the M7 over tap).
   - bus:b_hw_hc2_o leaf_um [307.521,328.4] -> [307.521,300.0]: 530 stage-0 sites leave the tap S edge, the row sits 37 um (was 8.6)
     under the ctl S pins. Stage 3 (646 sites) is still inside ctl.
   These two alone do NOT reach overflow 0: the slit and the ctl crossings stay.
B. Needed for overflow 0 (plan event work, not done here):
   1. Open the slit: move u_tap west on the 4.32 grid (origin x 164.172 -> 34.572 gives a 138-um channel; nothing else sits in
      x34-164 y328-458). Dependent rows: tap leaf_um of hc0/hc2/hc3 (-129.6), tap clock tap / reset sites, x_fw_p2_i last pad site
      (626,335) -> into the channel next to hr_q.
   2. b_hw_hc2_o stage 3 and b_tw_data_st_a_o: a single-knee L from a leaf under the cores cannot pass ctl / tap (ctl is 259.2 tall,
      the vertical hop is 260). Either +1 station with a two-knee route through the channel (needs a bus-chain path form; today
      leg_order is ignored for bus chains at kit_istations.py ~L2003 and `channel` is refused for non-core chains ~L1838), or a
      core-aware slide of an in-core site along its own leg to the core edge + 10 um (hop 306). +cycles are pre-approved.
   3. ft cws1 / cws2 last stations and u_lpad_x_fw_p2_i.q (626,335), x_su_l0/l1 pads: >= 30 um off a core pin face.
   4. Tool: run chain_macro_hits on every per_bit bus chain (report in PRECHECK, not a gate) so plan and kit share one site model.
C. Proof still owed: one private sle_ctl kit on A+B to GRT overflow 0, then DRC 0 / setup >= -42 / hold >= 0 / LEC, export. Out-bus
   station counts come from the plan at GEN (no RTL hack needed); recipe pattern epyc9 fable-fix-qc-cb/proof.sh.

## Not done
No private kit, no sign-off, no export. slw_hc3 land_slots bug and st_a rs_s1 / ft_spread were already fixed on main by QC-PLAN-R8's
helper (77440fa43c, 2bdea13bb1); not touched. epyc4 ssh host key changed (seen 23:2x); not touched.
