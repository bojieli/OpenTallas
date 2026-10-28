# opentools shared plan schema `opentools.plan/1`

One JSON file per die (or block) at planning time. Every opentools tool (clkplan, mesochronous crossings, top-metal
allocation, MSCTS, hierarchical flow) reads it and adds its own output section; no tool keeps a private copy of
these fields. Owner of the schema: OSS-CLKPLAN-1. Loader/validator: `plan.py` (`load`, `validate`, `save`,
`keepouts`, `clock_sinks`). LEF/DEF import helpers: `lefdef.py`.

Units: micrometres, picoseconds; origin at the die lower-left corner. Corners `TT` (setup) and `FF` (hold).

| field | type | meaning |
|---|---|---|
| `schema` | `"opentools.plan/1"` | required |
| `name` | str | plan name |
| `die` | `{w, h}` | die outline |
| `macros[]` | `{name, master?, rect[x0,y0,x1,y1], kind, clock_pins[], region?, islands?, island_rects[]?}` | hard cores, PHY macros, blockages. `kind`: `hard_core` (street-reach checked), `phy`, `blockage`. Clock cells may not sit inside any macro except in `island_rects` (pushdown islands built into the macro) |
| `macros[].clock_pins[]` | `{name, xy, insertion_ps{TT,FF}, sinks?, region?}` | the macro's clock pin and its OWN internal insertion delay (from its signed / real view) = sink attribute |
| `sinks[]` | `{name, xy, insertion_ps{TT,FF}?, region?, weight?}` | other clock taps (partition entries, std-cell region taps) |
| `regions[]` | `{name, rect, partition?}` | clock / PDN regions. Guidance: 1 clock region == 1 hierarchical partition. Two sinks in one region share supply droop |
| `regions[].clock` | `{root_xy?, local_insertion_ps{TT,FF}?, local_stages?}` | region clock root and (optional, measured) local tree insertion; region mode predicts it from the longest root->sink path when absent |
| `feeds[]` | `{name?, src, dst, len_um, kind forward/spine, tap root/leaf, stages?}` | region clock feed graph (METHODOLOGY 12.13b clock follows data): `src` = `root` or a region, `dst` = a region, one incoming feed per region (a tree). `forward` = neighbour-forwarded region clock, `spine` = tap off a shared spine along the links |
| `crossings[]` | `{name, a, b, kind, bits?, budget_ps?}` | related pairs between sinks (`a`, `b` = sink names or `macro/pin`). `kind`: `landed` (mesochronous, phase budget default P/2) or `sync` |
| `crossings[].derated_margin_ps{TT,FF}` | OUTPUT (clkplan) | derated phase margin: budget - max(\|d + p_up\|, \|d - p_dn\|) with AOCV + droop on the unshared clock |
| `crossings[].unshared_ps{TT,FF}` | OUTPUT (clkplan) | larger unshared die-tree delay of the pair (below the last common tree cell) |
| `crossings[].margin_pass` | OUTPUT (clkplan) | margin >= `clock.min_crossing_margin_ps` (landed pairs) |
| `pg[]` | `{layer, dir H/V, pitch_um, stripes[{net, offset_um, width_um}]}` | PG stripe pattern per layer, repeating every pitch |
| `pin_windows[]` | `{layer, rows{pitch_um, offset_um, half_um}}` or `{layer, positions_um[], half_um}` | pin-access bands (e.g. island slot rows) on a top layer: only the row's own cell may use tracks there |
| `layers[]` | `{name, dir, pitch_um, min_width_um, min_space_um}` | routing layers (informational for clkplan) |
| `channels[]` | `{rect, reason?}` | declared channels (optional; clkplan derives streets itself) |
| `streets_config` | `{raster_um, width_um?, reach_um?, demand{clock_cols, clock_col_um, hold_cols, hold_col_um, ft_bits, ft_bits_per_col, ft_col_um, fill}}` | street rule inputs |
| `clock` | `{name, period_ps, entry[x,y]?, layers{H,V}, ndr{width_um, space_um, shield none/drawn/pg_flank, shield_width_um?}, target_latency_ps?, skew_target_ps, min_crossing_margin_ps, flow_oriented_repeaters?, crossing_mode phase/count_aligned/ring_phase?, count_aligned{aperture_ps (scalar, default T/8)?, depths[4,8]?, wander_frac 0.05?, origin_cycles[X,Y]?}?, ring_phase{half_cycle?, aperture_ps{TT,FF}?}?}` | clock definition and constraints. `crossing_mode`: `phase` = one-period landing ring (budget P/2 - derated abs d); `count_aligned` = count-aligned ring read by count (COORD 20:35 + 21:10): K from the DERATED lag (one K for all corners), lag L inside [0.5T+ap, (DEPTH-0.5)T-ap], DEPTH 4 else 8, margins to the guard edges 0.5T / (DEPTH-0.5)T, gate >= min_crossing_margin_ps; `ring_phase` = the SUPERSEDED one-period setup+hold window +-(T-ap)/2 around a whole/half-cycle count (COORD 20:26, kept only for phase-placed samplers); `crossings[].mode` overrides per crossing, `crossings[].origin_cycles [X,Y]` = start-tree whole-cycle ambiguity of that crossing |
| `crossings[].count_aligned` | OUTPUT (clkplan, count_aligned) | `{K, depth, latency_cycles, aperture_ps, wander_ps, origin_cycles, L_lo_ps, L_hi_ps, margin_lo_ps, margin_hi_ps}`: K = lag in whole cycles (RTL K = K - nominal origin difference from the start tree), latency K+1 |
| `crossings[].ring_phase` | OUTPUT (clkplan, ring_phase) | `{K, step_ps, half_cycle}` |
| `region_clock_plan` | OUTPUT (clkplan --mode region) | per region: root arrival, local insertion, feed path/stages |
| `metal_alloc` | OUTPUT (opentools.metal) | per layer/row: slot census, assignment of clock wires to slots, conflicts |
| `mscts` | OUTPUT (opentools.mscts) | built region tree: cells, wires, per-sink arrival, verification numbers |
| `clock_plan` | OUTPUT (clkplan) | verdict, target latency, per-tap `tap_target_ps` / `tree_arrival_ps` / `balance_ps`, street + tree summaries |

Rules for tools: read with `plan.load()`, never drop fields you do not know, write your outputs under your own key
(or the OUTPUT fields above), keep the input fields byte-stable.

Region mode (12.13) and the locality tool: `tools/die_plan/locality.py` (LOCALITY-SCORE-1) should emit `regions[]`,
`feeds[]` and `crossings[]` in this schema (sinks = partition entries / macro clock pins with `region`); clkplan
`--mode region` then gives the unshared clock and derated margin per crossing. Region names = partition names
(1 clock region == 1 hierarchical partition). Mapping of the locality.py feed model (claude/locality-score-1027@53396c427a):
'fwd'/'spt' child c of p = feed {src p, dst c, tap leaf, len_um = |t - centre(c)|_1}; 'top' = feeds {src root, tap root}
with the I_max - I_r balance as regions[].clock.local_insertion_ps; region insertion I_r = regions[].clock.local_insertion_ps.

Arrival basis: clkplan crossing margins use SPICE-SCALED arrivals by default (COORD 21:10 after OSS-CLOCK-2: OpenSTA clock
arrivals read 4.2 % TT / 4.9 % FF early vs ngspice). STA-basis delays (declared sink/macro insertion_ps, declared
regions[].clock.local_insertion_ps, external crossing rows in clkplan.crossrows, and an STA-fitted stage model) are
multiplied by the model's spice_cal (opentools/mscts/data/asap7_bufx24_spice_cal.json: TT 1.0485, FF 1.0552); the built-in
ASAP7 stage model is already ngspice-based and is not scaled twice. `--no-spice-scale` gives the plain STA-basis numbers.
