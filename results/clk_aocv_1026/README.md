# CLK-AOCV: depth- and distance-based clock OCV table (DRAFT for owner review)

Lane CLK-AOCV, 2026-10-26, branch `claude/clk-aocv-1026`. METHODOLOGY 12.4a b1 (owner 10-26 17:4x), with the
droop correction (owner 10-26 17:5x). **Nothing in this directory gates anything yet.** The table is opt-in
(`die_sta_related.py --clock-ocv table`). Default outputs of die_ci / die_sta_related are byte-unchanged.
**Every number below is UNCHECKED until NUMBER-CHECK confirms it.**

## 1. What it replaces

`tools/die_plan/die_ci_margins.json` `ocv` uses a flat clock derate: cell 1.05/0.95 and net 1.03/0.97, plus IR +5.1 %
late. The die-CI lane picked these values on 10-24 from a textbook range for ~10-stage trees. They were never
measured. The draft below replaces the **clock cell** derate only:

- Data paths keep their flat derates.
- Clock nets keep the flat ±3 % net derate. They are not tabled (see open item 3).
- IR droop follows the shared-droop rule (section 4).

## 2. Does ASAP7 carry variation statistics? No.

- `asap7_pdk_r1p7/models/hspice/7nm_{TT,SS,FF}.pm`: 8 BSIM-CMG (level 72) cards per corner, no mismatch or
  Monte Carlo blocks. A grep for `mismatch|monte|agauss|sigma` finds nothing.
- The ORFS `asap7` platform liberty is NLDM only: no LVF (`ocv_sigma*`) and no AOCV tables.
- The ASAP7 authors say so directly: "Variation modeling is not directly supported by the ASAP7 PDK". They add
  mismatch in SPICE from an assumed A_VT = 1.2 mV·µm, based on Intel 14 nm 1.07 (n) / 1.23 (p).
  - Clark, Vashishtha, Harris, Dietrich, Wang, "Design Flows and Collateral for the ASAP7 7nm FinFET Predictive
    Process Design Kit", IEEE MSE 2017.
  - Their reference: M. D. Giles et al., "High sigma measurement of random threshold voltage variation in 14nm Logic
    FinFET technology", VLSI Tech. 2015, pp. 150-151.

**Hence the table rests on an ASSUMED mismatch sigma, propagated through the real ASAP7 device models.** We follow the
ASAP7 authors' own method: Monte Carlo on the ASAP7 BSIM-CMG cells, with the cited Pelgrom coefficient injected per
transistor.

## 3. Method

### Monte Carlo (depth axis)

`tools/die_plan/clk_aocv_mc.py` set up the runs; decks are in `mc_decks/` and the driver is `run_mc.sh`.

**Setup**
- Simulator: ngspice-42 + OpenVAF BSIM-CMG 111 OSDI (image `ot-ngspice:r3`, the same one INFRA-FIRST-R3 validated
  against the liberty at ±1.2 %).
- Netlists: ASAP7 r1p7 xAct3D-extracted cell netlists (full parasitics).
- Host: epyc1, one container per deck, 1 GB / 1 CPU each.

**Mismatch**
- Every transistor of every MC buffer gets an independent instance `DELVTRAND ~ N(0, σVt)`.
- σVt = A_VT / sqrt(nfin · W_fin · L), with W_fin = 2·HFIN + TFIN = 70.5 nm (card) and L = 20 nm.
- Result: σVt = 22.6 mV (2-fin), 18.5 mV (3-fin).
- Vt mismatch only. No β/mobility mismatch (U0MULT = 1); see open item 2.

**Chains** (the cells the die trees actually use)

| class | represents | stage |
|---|---|---|
| A | die H-tree / mesh stage (die_clock_mesh: all die clock cells BUFx24; 450 µm repeater pitch) | BUFx24 → 450 µm NDR M8/M9 wire (10 π segments, 4.45 Ω/µm, 0.11 fF/µm) → BUFx24 |
| B | core / partition CTS stage | BUFx8 → 40 µm M5 (setRC 19 Ω/µm, 0.164 fF/µm) → BUFx8 + 3 sibling BUFx8 loads (fanout 4) |

- **Minimum component** (AGENTS.md): each deck is a 6-stage chain with 2 nominal pre-drivers. Stages 2-6 are used;
  stage 1 sees the ideal pre-driver slew.
- 400 samples per class × corner, so 1600 decks. Sample 0 is nominal.
- Corners: TT 0.70 V / 25 °C (setup) and FF 0.77 V / 0 °C (hold).
- Measure: rising 50 % crossings, rise to rise (the buffers do not invert).

**Fit** (`clk_aocv_fit.py`)
- s = per-stage delay σ / nominal **cell** delay. The wire delay carries no variation in the MC, so all of it
  belongs to the cell derate.
- ρ = lag-1/2 stage correlations (slew coupling).
- Path check: σ_N² = a·N + b·N² on N = 1..5.

| class/corner | µ cell | µ stage | σ stage | s = σ/µcell | ρ1, ρ2 measured | b (non-averaging) |
|---|---|---|---|---|---|---|
| A TT | 53.39 ps | 100.24 ps | 2.074 ps | 3.89 % | -0.041, -0.046 | 0.081 ps² (≈ 0) |
| A FF | 39.31 | 85.75 | 1.569 | 3.99 % | -0.057, -0.025 | -0.047 (≈ 0) |
| B TT | 31.78 | 36.15 | 1.260 | 3.96 % | +0.007, +0.019 | -0.001 |
| B FF | 23.00 | 27.55 | 0.820 | 3.57 % | +0.007, +0.041 | +0.021 |

- With 400 samples the variance estimate carries about ±7 % sampling error. Every b·N² at N ≤ 5 lies inside it.
  **Mismatch averages as 1/sqrt(N); there is no measurable non-averaging part inside one chain.**
- Negative ρ is clamped to 0. This is conservative: no credit is taken for slew anti-correlation.
- Stage skewness is 0.07-0.2. The tables use the Gaussian 3σ.

### Systematic / distance axis

**Source**
- Cheng, Gupta, Spanos, Qian, He, "Physically Justifiable Die-Level Modeling of Spatial Variation in View of
  Systematic Across Wafer Variability", IEEE TCAD 30(3), 2011. Silicon data: 65 nm RO, 348 wafers. Their ref. [15] is
  Friedberg, Cheung, Spanos, SPIE 2006.
- They show that the within-die "spatial correlation vs distance" seen in measurements comes from the deterministic
  across-wafer trend. The purely random spatial part is not significant.

**Our model**
- So we do not use an exponential correlation length. The distance term is a deterministic gradient.
- Pair differential = g·d, with d = the bounding-box diagonal of all clock cells of both branches (the standard AOCV
  distance). g·d/2 is charged to each side.

**Deriving g**
- ngspice, ASAP7 SS / TT / FF process cards, all at TT supply and temperature (process only). Decks in
  `mc_decks/g_*.sp`; values in `glob.json`.
  - BUFx24: TT 72.83 / SS 85.74 / FF 63.00 ps.
  - BUFx8: TT 43.34 / SS 50.61 / FF 37.69 ps.
- spread = (SS - FF) / TT = 31.2 % (BUFx24).
- Bound: assume the whole spread is a radial across-wafer parabola, and the die sits at the wafer edge.
  The maximum slope is 2·spread / r_wafer, which gives **g = 0.42 %/mm**.
- **This is an UPPER BOUND and an ASSUMPTION.** The SS/FF cards also contain lot-to-lot and wafer-to-wafer spread,
  and most dies are not at the edge. The QC numbers below also show g/2 and g = 0.

### Derate per clock branch below the last common point

```
late  = 1 + 3·σ_r(N)/µ_cell + g·d/2        early = 1 - 3·σ_r(N)/µ_cell - g·d/2      (cells only)
σ_r²  = Σ_k µ_k² s_k² (N_k + 2 Σ_l (N_k - l) ρ_k,l)      (branch made of class-A and class-B stages)
```

- Random and systematic parts are added linearly. This is conservative: the gradient is a bound, not a sigma.
- Clock nets: flat 1.03 / 0.97.

## 4. Supply droop (owner 10-26 17:5x, METHODOLOGY 12.4a b1)

- Data path: +5.1 % late (stated 5 % drop), unchanged.
- Clock: only the **differential** droop between the two branches is charged.
  - 0 when both branches sit in the same mesh / PDN region.
  - The full one-sided +5.1 % late across regions, until a PDNSim or region-droop result gives the real
    differential.
- In code: `clk_aocv.droop_late()`, and `die_sta_related.py --clock-droop shared|stated`. Shared is the default
  with the table.

## 5. The table

Late cell derate, class A at TT. Columns are d = bounding-box diagonal in mm. Early = 2 - late.

| depth N | 0 | 0.5 | 1 | 2 | 4 | 8 | 16 | 24 |
|---|---|---|---|---|---|---|---|---|
| 1 | 1.1165 | 1.1176 | 1.1186 | 1.1207 | 1.1249 | 1.1332 | 1.1499 | 1.1665 |
| 2 | 1.0824 | 1.0835 | 1.0845 | 1.0866 | 1.0907 | 1.0991 | 1.1157 | 1.1324 |
| 4 | 1.0583 | 1.0593 | 1.0604 | 1.0624 | 1.0666 | 1.0749 | 1.0916 | 1.1082 |
| 8 | 1.0412 | 1.0422 | 1.0433 | 1.0454 | 1.0495 | 1.0579 | 1.0745 | 1.0912 |
| 16 | 1.0291 | 1.0302 | 1.0312 | 1.0333 | 1.0375 | 1.0458 | 1.0624 | 1.0791 |
| 32 | 1.0206 | 1.0216 | 1.0227 | 1.0248 | 1.0289 | 1.0373 | 1.0539 | 1.0706 |
| 64 | 1.0146 | 1.0156 | 1.0167 | 1.0187 | 1.0229 | 1.0312 | 1.0479 | 1.0645 |
| 80 | 1.0130 | 1.0141 | 1.0151 | 1.0172 | 1.0214 | 1.0297 | 1.0463 | 1.0630 |

- All four grids (A/B × TT/FF, 13 depths) and all fit parameters: `tools/die_plan/clk_aocv_table.json`, schema
  `opentallas.clk_aocv.v1-draft`, `status` DRAFT.
- A/B and TT/FF differ by ≤ 0.013 from this grid.
- For comparison, the flat derate is 1.05 at every depth and distance.
- The table is lower than flat for N ≥ 6 at short distance. It is higher than flat for N ≤ 4, and at long distance
  under the g bound.

## 6. QC seam pessimism: flat vs table (`qc_pessimism.json/.txt`, `clk_aocv_qc.py`)

**Input**
- QC-MP-REGION `claude/qc-mp-region-1026@c0ee907c63`, gates_r1:
  - `region_plan.json` sha f456edaa18fc0fc8…
  - `die_tree_plan.json` 243eaf6233085081…
- The same 773 seam pairs and the same non-common delays (reproduced exactly, e.g. 6297.3 TT).

**Per side**
- Branch = lattice edges (n = ceil(L/450)) + region legs (n_seg) + core 250 TT / 202.5 FF.
- Core counted as class-B stages: 7 TT / 7 FF, cell share 0.88 / 0.83.
- Worst of the two launch/capture orders.

Columns are the max ps per class:
- lane = QC-MP-REGION number (reproduction check).
- flat = flat derates on the exact cell/net split (core is more cell-heavy than the lane's fc).
- +shared = the droop change alone.
- table = table with stated droop (the table alone).
- table+shared = the proposed b1 form.
- g/2 and g=0 = sensitivity of the distance bound.

| class (pairs, same region?) | corner | lane | flat | flat+shared | table | **table+shared** | table+shared g/2 | table+shared g=0 |
|---|---|---|---|---|---|---|---|---|
| die root (14, no), d 19.0 mm, N_A 79 | TT setup | 759.3 | 777.2 | 777.2 | 796.1 | **796.1** | 623.0 | 449.9 |
| | FF hold | 587.4 | 603.7 | 603.7 | 619.5 | **619.5** | 492.5 | 365.6 |
| lattice node (129, no), d ≤ 15.7 mm, N_A 38-63 | TT | 598.7 | 619.4 | 619.4 | 593.2 | **593.2** | 479.4 | 367.2 |
| | FF | 462.3 | 480.1 | 480.1 | 463.0 | **463.0** | 379.5 | 296.7 |
| region root (60, yes), d 8.2 mm, N_A 32-34 | TT | 316.4 | 338.6 | 235.8 | 278.3 | **180.8** | 148.1 | 115.4 |
| | FF | 242.8 | 260.8 | 185.2 | 218.4 | **146.7** | 122.7 | 98.6 |
| intra-region node (570, yes), d ≤ 6.0 mm, N_A 1-21 | TT | 219.2 | 229.9 | 162.1 | 190.4 | **122.6** | 105.9 | 89.3 |
| | FF | 168.4 | 178.3 | 128.2 | 149.8 | **99.8** | 87.5 | 75.2 |

The QC insertion of about 6341 ps TT (die input to entry) is unchanged; derates do not change delay.

**Reading (UNCHECKED)**
1. **The droop change acts only on same-region pairs.** It removes 75-103 ps at the region root and 50-68 ps inside a
   region. Cross-region seams keep the full one-sided 5.1 %.
2. **Depth averaging cuts the random part strongly.** At N_A = 79 the random derate is ~1.3 %, against 5 % flat.
   - With no distance term, die-root pessimism falls 777 → 450 TT / 604 → 366 FF.
   - Under the upper-bound gradient g = 0.42 %/mm, the 19 mm die-root bounding box adds 7.9 % of the branch and
     cancels that gain.
   - So whether the table helps deep cross-die seams depends on the owner's choice of g.
3. **The structural conclusion of QC-MP-REGION stands under every variant.** Hold pessimism on lattice-boundary seams
   stays at or above ~297 ps FF, more than the ~240 ps a zero-logic pair can absorb, so these seams are not closable as plain
   related pairs.
4. **Inside one region the proposed form (table + shared droop) gives 100-147 ps FF hold** (75-99 ps at g = 0),
   against 168-243 ps for the lane's flat numbers.

## 7. Code (opt-in, default unchanged)

- `tools/die_plan/clk_aocv.py`: model, API (`cell_derate`, `branch_pessimism`, `flat_pessimism`, `droop_late`,
  `table`).
- `tools/die_plan/clk_aocv_table.json`: the draft table, a sibling of die_ci_margins.json. die_ci_margins.json itself
  is not edited.
- `tools/die_plan/die_sta_related.py --clock-ocv {none,flat,table} [--clock-droop stated|shared]`:
  - Applies OCV per related pair on the branches below the last common node: `stages_from_root` difference,
    bounding box of the taps plus the common node, and the declared core latency as class-B stages.
  - Default `none` = byte-identical behaviour. Existing tests pass.
  - **Needs fields the fold export does not carry yet:** per-tap `stages_from_root` and `xy_um`, and per-node
    `node_stages` and `node_xy_um` (the node arrivals come from `spine_late`/`spine_early`). It refuses without them.
    This is an ask to the die_clock_mesh.py owner (CLOCK-128).
- `clk_aocv_mc.py`, `clk_aocv_fit.py`, `clk_aocv_qc.py`: reproduce sections 3 and 6.
- `test_clk_aocv.py` (7 tests) + `test_die_sta_related.py` (3 tests): 10 PASS.

## 8. Assumptions and open items for the owner

1. **A_VT = 1.2 mV·µm** (Intel 14 nm, via the ASAP7 authors). This is assumed, not ASAP7-native. The random derate
   scales about linearly with A_VT.
2. **Vt mismatch only, no β mismatch.** FinFET literature reports β mismatch can be comparable, e.g. IEDM 2008,
   "First observation of FinFET specific mismatch behavior...". Adding an equal β term would raise s by ~√2.
3. **Clock nets stay flat ±3 %.** Wire variation is mostly systematic (thickness/width). A wire distance table needs
   metal-variation data, which ASAP7 does not provide.
4. **g = 0.42 %/mm is an upper bound.** The whole process-corner spread is treated as an edge-die across-wafer slope.
   **This choice dominates the cross-region numbers; it is the owner decision.** The candidates are:
   - the bound;
   - g/2;
   - 0, i.e. random-only, as in Cheng et al.'s "ignore spatial variation" regime;
   - a value calibrated later.
5. **3σ, Gaussian, random and systematic added linearly.** Stage skew is small (0.07-0.2).
6. **Per-side derating** (late on one branch, early on the other) is the standard AOCV form. It bounds the
   differential sigma from above.
7. **Shared droop.** Same-region means the same lattice region (QC 16 regions). For die_sta_related it means the same
   `cppr_node` ≠ 'h'. Cross-region keeps +5.1 % until PDNSim.
