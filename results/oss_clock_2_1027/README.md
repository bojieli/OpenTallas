# OSS-CLOCK-2 (2026-10-27 20:31-21:xx PDT): spice recalibration, QC slice on the R35 tracks with legality, count-aligned margin mode

Branch claude/oss-clock-2-1027, from claude/oss-clock-1027@19f21e1d7. Run data:
- intel2:/srv/opentallas-scratch2/claude/oss-clock-2-1027 (inputs `in/`, E0 builds)
- intel1:/srv/opentallas-scratch2/claude/oss-clock-2-1027 (OpenSTA on the E0 builds)
- the predecessor's ngspice runs: intel1:/srv/opentallas-scratch2/claude/oss-clock-1027

Labels: OWN = my run, not independently checked. UNCHECKED = an estimate or an extrapolation. These are tool
results, not gate numbers. No gate or rule was changed.

## 1. Full-slice ngspice (predecessor jobs, collected)
The predecessor's 554-BUFx24 QC slice tree (late_split, synthetic pairs) was compared with `mscts.run compare`.

| corner | sinks | spice insertion | spice skew | STA skew | STA - spice (mean, spread) | model(STA fit) - spice |
|---|---|---|---|---|---|---|
| FF | 192 | 2719.8-2740.3 | 20.5 | 12.8 | -133.8 (-128.1..-137.6) = -4.9 % | -154.8 |
| TT | 192 | 3222.2-3239.5 | 17.3 | 15.0 | -136.5 (-132.1..-141.1) = -4.2 % | -171.0 |

- qcs_nn TT (the nearest-objective tree): spice skew 12.9, STA 11.5, STA - spice -134.7 (-130.3..-136.2) = -4.2 %, crossing d STA vs spice max 4.5 ps.
- Held-out check of the v1 pure-scale calibration (1.0727/1.0731 fitted on <= 1 ns trees): it over-predicts the 2.7-3.2 ns full slice by ~1.2-1.4 % -> replaced by the affine slope below.
- Files: qcs_ls_compare_{TT,FF}.json, qcs_nn_compare_TT.json.

## 2. Stage model recalibrated to ngspice (finding for COORD)
Pooled data: qcs_small (24 sinks), qcq_ls (48), qcq_nn (48, TT only) and the full slice qcs_ls (192) + qcs_nn
(192, TT only). That is 0.5-3.2 ns insertion on the same netlists in both tools. `python3 -m mscts.calib spice-scale compare_*.json`:

| corner | spice = s x STA (all sizes) | STA-fit model / STA (small, quarter, full) | spice = a x model + b (per-stage slope a) |
|---|---|---|---|
| FF | s = 1.0515, residual -5.4..+3.8 ps | 0.975, 0.981, 0.992 | a = 1.0552, b = 12.6 ps, residual -5.5..+4.7 |
| TT | s = 1.044, residual -5.3..+5.1 ps | 0.970, 0.976, 0.989 | a = 1.0485, b = 21.6 ps, residual -8.1..+9.2 |

- **OpenSTA reads a stable 4.2-4.7 % (TT) / 4.9-5.2 % (FF) early against transistor-level spice.** The offset
  is the same from 0.5 to 3.2 ns. The per-sink scatter around that scale is <= ~10 ps at 2.7 ns, about 0.35 % of insertion.
- **The planner (MSCTS STA-fit stage model) adds a size-dependent deficit on top.** It reads 2.5 % below STA on
  small trees and 0.8 % below at 2.7-3.5 ns (the E0 build below gives model/STA 0.989 TT / 0.994 FF).
  - Total: 6-7.5 % below spice. This is the "7 % optimistic" figure.
  - The new data file mscts/data/asap7_bufx24_spice_cal.json applies the affine slope a per stage
    (`spice_scale`). The constant b is a root offset only: it cancels in skew and in every crossing d.
- clkplan's default stage (ngspice MC, 100.24 TT / 85.75 FF ps per 450 um) is 2.9 % / 2.1 % below the
  spice-calibrated MSCTS stage at 450 um. Left unchanged.

What this means for the shared gate margins (landed_phase_ocv / die_sta_related, 100 ps). This is a model-bias
statement; no gate change is proposed.
- (a) **Current ring, balanced pairs (small |d|).** The derate p is computed on the STA unshared clock, so it
  under-reads by ~5 % of p. The non-uniform residual adds ~0.35 % of the unshared clock u.
  - QC slice<->slice (p 235 TT, u 5.7 ns): ~12 + ~20 = ~30 ps of the 100-ps margin.
  - HEAD-class (u 4-6 ns): similar, ~25-35 ps.
  - These are UNCHECKED extrapolations: the residual is measured only up to 2.7 ns.
- (b) **Count-aligned crossings.** K absorbs whole cycles at design time, but the lag L = K T + d uses the STA d,
  so d itself is ~5 % short in silicon terms.
  - The error is 0.05 x |d|: 37 ps for the QC HUB 752 ps, and >= 100 ps once |d| >= 2 ns.
  - Count-aligned margins from STA arrivals should carry +5 % |d|, or use spice-scaled arrivals, wherever large
    nominal offsets are left for the count to absorb. This is for MESO-COUNT-1 / MESO-INTEG-1 / die owners.
- (c) **Common core latency 250 / 202.5 +-20.** Both sides are OpenSTA, so the bias is common. Only early-tap
  deltas carry it, e.g. 0.05 x 231 ps = 12 ps on a QC SU tap.
- (d) **FF hold** reads 4.9-5.2 % early as well, so the same factors apply to the FF-hold side of the window.

## 3. MSCTS on the QC slice: R35 tracks, legality, real traffic (E0 = std_bg_0_0)
Input built by qc_slice_spec.py (adapter; the tools stay generic, the PDK and plan are data). It uses
claude/qc-sliceclk-1027@88bc183c7c plan + regions, main tools/die_plan (schema, die_trial.SiteMap, locality.py) and
claude/qc-infra-r35-1027@c2b1eb75be qc_slice_rows.json.
- **Sinks: 584.** The partitions' R4 tap grid (schema.tap_grid, common latency 250 / 202.5) plus the 8 merged early
  SU core taps (386-481 ps insertion; the tree balances latency = arrival + insertion).
- **Crossings: the REAL in-slice traffic.** The 78 partition pairs carry 100,596 bits: every plan port with both
  ends in the slice, the same port list as locality.load_plan. Each pair is mapped to the tap of each partition
  nearest the other partition.
  - Cross-slice traffic (W0 4,993 b, E1 5,507 b) is listed in the spec. It belongs to clkplan region mode, not to
    one region tree.
- **Legality.** Keepouts are die_trial.SiteMap.forb: 80 rects (A0 / SU cores + 2.16-um halo, PHY).
  - Merge buffers move to the nearest legal site on their L path and are re-balanced.
  - Repeaters slide out of keepouts. A post-slide bottom-up re-balance follows (mscts.legal).
- **Trunk = the R35 reservation as data (mscts.trunk).** The entry sits at the TOP tap (spine x 18,303.84, row 1520).
  Bisection nodes L1-L3 sit on the spine column. Leg rows sit at the 16 strip centres, with a 678-um leg to the strip
  centre. MSCTS local trees hang below each leg end, and leaves are balanced by a ledgered snake on the leaf entry leg.

| E0 build (spice-cal model) | buffers | wire mm | snake mm | model latency TT | model skew TT / FF | OpenSTA latency skew TT / FF | crossing d model vs STA (max) | worst crossing margin TT / FF (model, same-region droop) |
|---|---|---|---|---|---|---|---|---|
| late_split | 1607 | 374.2 | 59.0 (15.8 %) | 3949 | 0.5 / 32.6 | 30.6 / 26.6 | 6.0 / 3.0 | 228.6 / 243.6, 0 of 78 < 100 |
| nearest | 1614 | 380.4 | 62.7 (16.5 %) | 4114 | 0.5 / 27.3 | 24.7 / 18.6 | 18.9 / 7.6 | 222.2 / 239.4 |
| late_split, NO keepouts (reference) | 1455 | 329.7 | 14.1 (4.3 %) | - | 16.3 / 31.0 | - | - | 228.7 / 248.2 |

- Other numbers (OWN):
  - Late split cuts the mean unshared on the 78 real pairs from 529 to 419 ps TT (max 3.76 ns: pairs split at the
    slice root).
  - OpenSTA ran on the emitted Verilog + SPEF. Model/STA is 1.037 TT / 1.048 FF on the spice-cal model (measured spice/STA
    1.044 / 1.052, so within ~0.7 %), and 0.989 / 0.994 on the STA fit.
  - Files: E0_*_summary.json, E0_*_sta_check.json, qc_E0_spec.json.
- Legality result (OWN): 0 illegal merge or repeater buffers; the only illegal sinks are the 8 SU core clock pins,
  which are pins.
  - 92 merges were moved (max 285 um) and 135 repeaters slid.
  - **49 stages exceed 480 um (max 759.5 um):** local L-routes cross A0 rows where no repeater fits. This is the same
    effect as R35's 462-um leg stage, but larger, in the local trees.
- Render E0_late_split.png (viewed):
  - Taps sit in the inter-core streets and on the core edges.
  - Merges sit in the streets. The spine runs on the right-hand street column.
  - Wires cross cores on M8/M9; buffers never sit inside a grey keepout.
- **STRUCTURAL FINDING.** On the fixed R35 trunk, A0 legality raises the balancing meander from 4.3 % to
  15.8 % of wire, far over the v5.1 "sparse <= ~5 %" budget. The 49 over-long stages are a slew risk, not checked.
  - The trunk itself is fine: equal legs, and every buffer is on the legal column.
  - The cause is the local trees. They route x-first L paths across A0 rows, and both the merge points and the
    repeaters are pushed off the cores.
  - Fix (next, generic, in mscts): street-aware local routing. Route the local L/Z paths along the inter-core
    streets (the rendered street columns) and pick the merge points on street crossings, so balance does not need
    meander. Or allow in-core clock islands (12.2a1) where a core offers them.
- **Comparison with QC-SLICECLK-3** (claude/qc-sliceclk3-1027@e898bf05ab, die_trial on the same R35 rows):
  - Its in-slice spread is 176-177 ps TT / 149 FF (ctree STA, placement parasitics, stock bisection to 600-um
    leaves).
  - This build gives an OpenSTA latency skew of 30.6 / 26.6 ps on 584 grid + core taps. That is OpenSTA with an
    analytic SPEF (4.45 ohm/um, 0.11 fF/um), not a routed extraction, and it carries the 15.8 % meander above.
  - Both use the same trunk. The difference is the local trees: MSCTS zero-skew legal merges instead of stock
    bisection.
  - Crossings in the slice pass on this model (worst +228.6 / +243.6). Slice<->slice crossings are clkplan region
    mode's job (count-aligned mode below).

## 4. clkplan: count-aligned crossing margin mode
- `python3 -m clkplan.run PLAN --mode region --crossing-mode count_aligned` (or `clock.crossing_mode`, or per crossing
  `crossings[].mode`). `clock.count_aligned = {form, depth, half_cycle, aperture_ps{TT,FF}, origin_cycles[X,Y]}`.
- **form 'ring'** (default): the COORD 20:35 ruling on MESO-COUNT-1, which supersedes the brief's 20:26 text.
  - L = K T + d, with the derated low end min_c(K T + d_c - p_dn_c - X T) and the derated high end
    max_c(K T + d_c + p_up_c + Y T).
  - These must lie inside [(0.5 T + ap), (DEPTH - 0.5) T - ap].
  - ONE design-time K for all corners: the smallest K whose worst corner passes min_crossing_margin (least latency),
    else the max-min K.
- **form 'period'**: the COORD 20:26 text, withdrawn for the CA ring and kept for a one-period sampler with a
  design-time count. Window = +-(T - setup - hold)/2; the residual r_c = d_c - K step counts; ONE K for all corners;
  step = T, or T/2 with `half_cycle`.
- ap = the placement flop's setup + hold, as PDK data in the model (`capture_aperture_ps`): asap7 DFFHQNx1 26.49 TT /
  19.29 FF, the value used by NUMBER-CHECK LAND-HEAD-3.
- **Origin ambiguity of the start tree** (MESO-COUNT-1's X/Y whole cycles) is an input (`origin_cycles`, default 0).
  The start-wavefront model itself stays in tools/die_plan/count_align_plan.py.
- Tests:
  - Period whole vs half cycle: -133.6 vs +266.3 on d = -437 / -376, p = 100.
  - Ring smallest K = 2 and the window arithmetic; X = 1 moves K to 3; a too-wide spread fails.
  - The toy 3-mm forwarded hop: phase margin < 0, count-aligned PASS.

## Tests
- clkplan 16 (3 new)
- mscts 9 (4 new: legal merge move + rebalance, repeater slide + netlist follows, trunk compose with early tap,
  spice_scale file)
- metal 4
- Run: `cd opentools/<tool> && python3 -m pytest -q tests`

## Not done / next
- Street-aware local routing in mscts (the structural fix above), then E0 again and the other 11 slices.
- Spice on the E0 legal tree. 1,607 buffers is ~3x the full slice (about 70 min per corner on intel1 at the measured
  rate).
- Slew check of the 49 over-long stages.
- Slice<->slice crossings on these trees through clkplan --crossing-mode count_aligned, with the 5 % |d| bias term.
