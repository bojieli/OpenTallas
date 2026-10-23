# FT-S81 recipe: feedthrough pushdown + layer budget on the S81 DeepSeek ROM die (cap24, 72-frame MU)

FT-S81, 2026-10-23. Inputs: cap24 plan `ep9:/srv/opentallas-scratch2/claude/stw-s81c-cap24-main/plan.json`,
case `ep5:/srv/opentallas-scratch/claude/coord-rep600-s81/case/case.json`, coordinator dump `coord-rep600-s81/dump/`.
Numbers come from the quick census in `tools/s81_dv/ft/` and are estimates until the FT-TOOL census and plan land.
Files: `census_direct_1500.json` (direct Manhattan paths), `stage_model_v0.json` (per-lane station counts),
`ft_s81_crossing.png`.

## 1. Starting point (measured)
- All 225 big-block instances on cap24 are stand-ins (`rv_*`, 24 masters). That covers 72 frames (`col_h9_l4_lp` x60,
  `col_h10_l4_lp` x12), 16 slices, svc_rs x14 and pvso x2, ot_pdie_serdes x10, idx_rg3 x8, bk_sel, gunit, eng_rr and
  seqhost. Each stand-in's abstract is `dv_rvcase.py` lines 925-931: one blanket full-footprint OBS on M1-M6, with pin
  windows cut on M4-M6. M7-M9 are open. The closed hard blocks on the die are small (bk_col, ctrl_rg3, eng_tap,
  idx_qf, relays, landings), and their OBS is real geometry.
  -> No big block has a closed view, so ft goes in at the block's first hardening. No closed view has to be re-hardened.
- The frame kit contract (`s81frame_col_h9_rf3rlfs1x`, cluster level 2) already matches the target:
  - signals RLAYERS M2-M7;
  - PG M5/M6/M7 corridors, plus M8 pin stripes (w 0.48, pitch 8.64, about 6% of M8) on the die grid;
  - M9 left to the die;
  - abstract exported exact-shape by `ref_tile.py`, never `-bloat_occupied_layers`, so the OBS is the real geometry.
- Lanes: 835 links, 329k bits, 19,609 half-cycle `dsfd_dvrlyh` stations, plus 19.6k `dsfd_rly_1_WN` reset stations.
  Bit-mm along the current channel paths is only 4% above Manhattan. The cost is congestion and station count, not detour.
- Frame arrays: 5 columns x 7 rows per side.
  - Row streets are 259 um and column streets 86 um.
  - A column is 25.1 mm tall on a 26 mm die, so the streets cannot grow.
  - A row street must carry up to 5 frames x 1,174 b = 5.9k H bits. Its capacity is about 3.9k bits (M6+M8 at 0.6).
  - So frames cannot be served by streets alone.
- The hottest GRT spot is the H street between s_0S and s_0N at (9.25k, 17.4k). It is the only path for W-frame lanes
  to the s_1..s_3 hubs. ft through s_0S/s_0N removes it.

### 1b. Stand-in master status (sub-agent sweep of lanes + main @3ef3208d9, 10-23 ~00:30)
| master (inst) | kit / contract | latest | ft impact |
|---|---|---|---|
| col_h9_l4_lp (60) / col_h10 (12) | s81frame_col_h9_vgsr/_vgcsr, h10_vgsr/_vgysr @d09a59d18; RLAYERS M2-M7, PG pins M8 stripes | never closed. All earlier gates FAIL at CTS (forwarded xk spread 125-143 ps, spine target) or GPL. vgsr family verdict pending. Children all closed except the q-elem stand-in view | add ft at first close; keep the corridor clocks separate from xk |
| slice c1x/c3x k8 cap5r_w (9+1) | k8c/k8d, k8e/k8f (branch claude/s81-slicep-k8c-1021); M2-M7, PG pins M8 | no parent gate; children partly closed | ft added to the parent wrapper |
| slice lepw/lepe mu_72 x4, iq, sukv_raw512 | assembly specs only / no kit | no parent gate | ft at kit creation |
| svc_rs (14) + pvso_entry (2) | successor pair72 x6 + entry (claude/s81-svcpair72-1021) | children failing (attw ROOT1, hgrp8r) | V ft (M9) in pair72 |
| ot_pdie_serdes_col (10) | s81lk_serdes_col_sp11a | **CLOSED 10-22 08:46**, never swapped into the die | the only closed big view: re-harden with ft (H 3.7-8.2k bits over a 518 um column) or route lanes around it |
| idx_rg3 (7) / _nq (1) | flat kits M2-M7 PG M7; rg3b band successors | flat kits all FAIL clock_rule; bands mixed | small ft (1-2 bundles) |
| bk_sel_vmtx, eng_rr, gunit, seqhost_mux | children gating (selcpn_i CLOSED, eng_rr b3m/b3f, l1fb, seq_host) | no parent closed | ft at the parent |
| svc_busland x5 masters, pv_local_land | no kit (busland) / d32c gate WARN | - | small, not crossed |

Layer-budget note: frame, slice and gunit kits put PG pins on M8 as stripes (0.48/8.64, ~6% of M8, aligned to the
die grid). The FT-PLAN target is PG at or below M7.
- Recommendation: keep the M8 stripes, because the ft corridors fit between them (M8 ft ratio at most 0.12-0.2).
- Moving the PG pins to M7 would change the contract of every cluster kit for about 6% of M8. Not worth it unless the
  plan.py ratio says otherwise.

## 2. Target layer budget (S81)
| element | signals | PG / straps | die over it |
|---|---|---|---|
| frames col_h9/h10 (existing kits) | M2-M7 (unchanged) | M5/M6/M7 + M8 pin stripes 0.48/8.64 (unchanged) | M8 between stripes: ft corridors only; M9 die |
| slices, svc_rs, lk serdes, irg, bk_sel, gunit, eng_rr, seqhost (kits still to write) | M2-M7 | <=M7 + M8 pin stripes on the die grid (cluster level 2, same as frames) | M8/M9 ft + die |
| hard children (q elem, bf_col: PG top M7) | inside parent | M7, strapped from parent M8 | none |
| ROM macros, relays, landings | M1-M5 | M5/M7 | route over |
| HBM PHY (hard IP, OBS M1-M4) | - | - | M8/M9 wires only, no repeaters possible -> lanes must not cross it (the row policy currently puts 5k bits over it: plan.py must forbid) |

Change required in the die flow:
- Stand-in abstracts keep M1-M6 blanket OBS only.
- Die GRT runs with `--signal-top-layer M9`.
- Die GRT must not credit M7 over a block that has a real view: real frames route M7 inside.

## 3. ft pushdown design (per crossed block)
- **Lane routing policy (plan input).** Frame<->hub lanes run row-aligned: the H leg is at the frame's own pin band,
  and the V leg is in the centre, at the hub face. Every frame in column position p (0 = outer, 4 = inner) then carries
  p bundles of 1,174 b (4x276 x inbound, 70 ret outbound, plus 5 forwarded-clock bits).
  - Measured loads: frames hold 0-4 bundles, at most 4.8k bits = 0.12 of M8.
  - Slices: s_0S 8.4k, s_0N 7.3k, c1x up to 6.0k.
  - svc_rs: up to 8.8k (0.2 of M9 V).
  - bk_sel: 10.4k.
  - Every block is far below the 0.6 bits/tracks rule.
- **Shifted corridors.** Own lanes leave the E face (W face for the MX/E array) at slot 0. The ft corridor entering at
  slot j leaves at slot j+1 inside the frame. Every position then uses the same corridor geometry, and the variants
  differ only in how many corridors are populated.
- **In-block content per corridor:**
  - 2 soft half-cycle stations (`ot_dvrly_st` W=276/70 HC=1, the dsfd_dvrlyh body): the entry station within about
    20 um of the W-face pin band, the exit station at the E face. Registered in and out, per the pin-register rule. The
    in-block hop is 1.44 mm, within the 1.5 mm reach.
  - BUFx12f repeaters at <=300 um on M8 between the stations (REACH-M89 best calibrated config).
  - Corridor clock = the lane's forwarded clock (ft port `ck` in, `ck_o` out), never the frame's regional root. Precedent
    for this: the frame spec's `forwarded_soft_clocks` (xk). Each corridor root has <=1,174 sinks per station pair.
  - Reset = the frame's landed `rst_n` (u_frl_rst), with no new die reset station.
- **ft ports:** M8 (H) on the W/E faces at fixed slot offsets, outside the frame's own pin band (y 91-603 um), aligned
  with the abutting neighbour across the 86 um street. Pins sit on M8 with face width >= bits x 0.08/0.5 (1,174 b ->
  188 um per slot). V ft (centre blocks only) uses M9 on the N/S faces.
- **ETM:** every ft path is flop->pin or pin->flop, and the forwarded-clock arc follows the dvrlyh view. The frame
  ETM stays clean.
- **Die side:** drop the channel stations of pushed-down lane stretches, connect through block ports, and keep die
  stations only where a gap is longer than 1.5 mm.
  - Keep relay pins on M3-M5: REACH-M89 modelled the via stack. Never put M8 pins on a 17-um relay (the M8 pin
    what-if gave 24.6M overflow).
  - Die repeaters: OT_DIE_REPAIR_MAX_WIRE=450.

## 4. Relay hop and static schedule
- Station model (`stage_model_v0.json`, 1.5 mm hop, 2 forced stations per crossed block):
  - 19,609 -> 5,714 stations;
  - bit-stations 4.96M -> 1.39M (-72%);
  - x_frame max 88 -> 28; ret max 295 -> 36 (the 295 includes schedule padding).
  - Registering in only would give 4,935 stations, but that breaks the pin-register rule and is not proposed.
- Open check for REACH/FT-TOOL: REACH-M89 measured a full-period (833 ps) hop. The S81 stations are HC=1 forwarded
  half-cycle stations. The forwarded clock cancels the wire delay to first order, but the 1.5 mm figure has to be
  confirmed per half-cycle station before plan.py adopts it.
- Static-schedule re-derivation inputs, per lane:
  - station count, in half cycles;
  - ft latency per crossed block, a fixed 2 half-cycles;
  - landing window E/D recomputed (`land.json`);
  - DATA_EQ same-source equalisation inside each lane group (x l0-l3 of a frame must keep equal station counts:
    fclk pairing).
  No functional change. Consumers: dv_plan / dv_layer_compile and the token-pass schedule (STEWARD-TOK).
- **Floorplan slot bug (fix in the same re-plan).** 4 frame x-chain pairs sit 26 mm apart, at the top vs the bottom
  of a column: f_0R02->0R03, f_2R12->2R13, f_5L02->5L03 and f_7L12->7L13. That is 16 lanes x 276 b at 74 stations.
  4 more pairs are 5 mm apart. Both frames of a pair are the same master, so swapping slots costs nothing in function,
  and it removes ~115 Gbit-um (7%).

## 5. Effort and options
Frame hardening cost, measured on the h9/h10 gates:
- about 7-12 h per attempt;
- route peak 192 GB (spec), and GPL alone 30 GB / 7 h;
- the frames have never closed yet (GPL non-convergence and clock-rule FAILs since 10-19).

| option | ft blocks | unique hardenings | notes |
|---|---|---|---|
| A. full pushdown, per-instance ft | 85 | ~75 (72 frames: 37+ distinct signatures) | infeasible: ~75 x 192 GB x 10-24 h |
| B. full pushdown, quantised (recommended) | all crossed | ~37 total vs the 24 stand-in masters that must be hardened anyway (+13). Frames: col_h9 levels 0-3 = 4, col_h10 levels 0-4 = 5. Centre: c1x 5, svc_rs 5, serdes 4, irg 3, plus 11 singletons (slices lepw/lepe/iq/kv512/c3x, bk_sel, gunit, eng_rr, pvso) | streets in the frame arrays freed; hub street hotspot gone |
| B'. as B, one ft master per frame base (all corridors present, outer-column ft inputs tied as spare) | all | frames 2 | needs a coordinator ruling: 4 spare corridor inputs per outer frame are tied (no-tie-off audit) |
| C. middle path: ft only in heavy blocks (>=4k bits: inner 2 frame columns, outer slices, bk_sel, lk_EN1), sized streets elsewhere | 23 | frames 4, centre ~10 | channel bit-mm 1,743k -> 1,189k (vs B 626k). Outer row streets still at 60-100% of capacity. s_1..s_6 column streets stay over capacity (cap31 GEN: 983 um needed vs 744 um free) |

**Recommendation: B.** Full pushdown, quantised by position, with shifted corridors.
- Frames: the variants are the same frame, with 1-4 extra corridor pairs of soft stations (about 0.2% of frame area).
- The marginal cost over hardening the stand-ins at all is about 13 extra runs. They run in parallel: one wave of
  ~9 frame runs is about 1.7 TB of route peak, so 2 waves on the fleet, about 1-2 days including a retry.
- Option C leaves the frame-array streets, which cannot be widened, at the capacity edge, and saves only about 5 runs.
- Ask the coordinator whether B' is allowed: it would cut frame variants from 9 to 2.
- First hardening: col_h9 position-4 variant (4 corridors), on the current fs1x recipe. It is the most loaded variant
  and proves the corridor mechanism.

## 6. COORD rulings 10-23 and what they change (FT-S81 addendum)
1. **Option B approved. No tie-offs.**
   - Without ties, frames would need a separate variant for every frame column position, i.e. 0-4 through-bundles.
     That is 4 ft variants each for col_h9 and col_h10.
   - Reduction to 4 frame variants (h9 ft1/ft2, h10 ft1/ft2): the lanes of the two OUTER frame columns ride their own
     row's street. That is 2 bundles = 2.35k bits against ~3.9k capacity (M6+M8 at 0.6); each street is assigned to one
     row, and the top row uses the die-edge margin. Column 2 then carries 0 bundles (base master), column 3 carries 1,
     column 4 (inner) carries 2.
   - Outliers f_3L01/f_4R01 (column 5, top): their lanes are routed around them via the top margin, so they stay base.
   - Every ft corridor carries a real lane. No spare corridors.
   - Centre (estimate, row policy): c1x 3 variants, svc_rs (pair72 successor) 4, serdes 3, irg 2. Singletons are
     unaffected.
2. **Half-cycle reach (REACH-M89 sweep data reanalysed at T/2 = 416.7 ps, same calibration 1.203, BUFx12f, <=450 um):**
   - dsfd_dvrlyh_276 on M8: 228 um; on M9: 234 um. Full cycle: 1,499 / 1,520 um.
   - dsfd_rly_266 does not reach 200 um at half cycle.
   - Stage model, in cycles (sum over 835 lanes):
     - today (19,609 HC=1 stations planned at 405 um): 9,805 cycles. Those 405 um half-cycle hops exceed the 228 um
       half-cycle reach.
     - HC=1 at 228 um: 29,567 stations = 14,784 cycles; x_frame max 64 cycles.
     - **HC=0 full-cycle stations at 1.5 mm: 5,715 cycles (-42% vs today); x_frame max 28.**
   - Decision: ft and die lane stations become FULL-cycle `ot_dvrly_st #(HC=0)` (the dsfd_dvrly_* body) at <=1.5 mm.
   - HC=1 existed only as the relay->relay hold fix for short forwarded hops (-120..-195 ps). At 1.0-1.5 mm hops the data
     leg dominates. Hold is re-checked per hop in FT-TOOL checks, with hold buffers where short.
   - Files: `stage_model_r228.json`, `stage_model_r1499.json`.
3. **Special-net M8 pre-route of ft nets:** approved. Implementation goes with FT-TOOL (pushdown).
4. **Slot swap of the 4 chain pairs that are 26 mm apart:** approved. It goes into the FT re-plan.
5. **(d):** col_h9 2-corridor variant (the most loaded under 1.) on the frame recipe that closes CTS. The 4 live
   STEWARD gates (h9/h10 vgsr, vgcsr, vgysr; spine-target basis fix @d09a59d18, gold1/gold2) still run at 00:40. Their
   verdict decides the base recipe. The structural CTS fix for the frame is owned in (d) if they fail.
