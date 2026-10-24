# B2r2 die IR drop with estimated power (TRIAL-HBM steps 2 + 4b), 2026-10-24

Tool: OpenROAD PDNSim (`analyze_power_grid`, openroad/orfs:asap7lock, OpenROAD 26Q3). Plan:
`physical/die_plan/hbm_arch/B2r2/die_plan.json`. Budget: 35 mV rail sum (VDD drop + VSS rise), which is also 5% of 0.7 V.

## Verdict

| Case (exact plan grid unless noted) | VDD drop mV | VSS rise mV | rail sum mV | interior* sum | vs 35 mV | worst node (die um) |
|---|---:|---:|---:|---:|---|---|
| PHY_N + corridor below it (8346-16848 x 11750-18317) | 12.97 | 16.67 | **29.63** | 29.63 | PASS | VDD at (8532, 15401) and VSS at (8878, 13457): both in NW_sm1 at the window's W edge, not in the PHY |
| PHY_N + corridor, no bumps over the PHY macro band (sensitivity) | 4573 | 4440 | **9013** | | FAIL (no physical meaning: shows the grid has no lateral reach) | (12593, 18295), PHY band at the die edge |
| one hub, NW_hub | 5.71 | 6.95 | **12.66** | 12.66 | PASS | VDD (3564, 9482); VSS (4860, 9828) |
| one SM, NW_sm0 | 12.51 | 34.48 | **46.99** | 31.68 | FAIL (interior PASS) | VSS (21.8, 13457): die W edge |
| SerDes io, NW_io (u_lk_N0 SerDes + host UCIe) | 60.00 | 85.87 | **145.87** | 145.87 | FAIL | inside SerDes u_lk_N0: VDD (713, 6372), VSS (411, 6329) |
| S-edge SerDes, NW_spb0 (u_lk_S0) | 61.96 | 140.95 | **202.91** | 146.61 | FAIL | inside u_lk_S0: VSS (5508, 21.6), at the die edge |
| full die, exact grid (`full_exact`) | | | | | **NOT COMPLETED** | pdngen was still inserting 247,616 load macros after 4 h 10 min (RSS 4.6 GB, single thread); stopped |
| full die, coarse grid x4 (`full_s4m`) | | | | | **NOT COMPLETED** (still running when this was written) | pdngen passed in 994 s. After that the run sat > 2 h in `check_power_grid VDD` (RSS 150-180 GB, 400 GB cap). A first try under a 120 GB cap (`full_s4`, epyc2) was killed by OOM after pdngen |

\* interior = load tiles at least one per-rail bump pitch (63.64 um) from the die edge. The assumed checkerboard bump
lattice puts VSS at k x 63.64 and VDD at 31.82 + k x 63.64. Its VSS row/column at x = 0 / y = 0 falls on the die edge
and is dropped, so the die-edge tiles have one-sided VSS bump support. The SM and spb0 VSS worst nodes are this
artefact, and so the edge numbers depend on a bump map the plan does not yet have.

PG connectivity: `check_power_grid` passes VDD and VSS in every case, PSM-0040 "all shapes connected", 0 failed vias.
In the integrated die top (../top) check_power_grid also passes on the real die PDN over the 88 mock partitions.

**Summary.**
- At the estimated a20 peak power, the plan's die grid (M8/M9 0.48 um at 8.64 um pitch per net, 5.6% coverage per net
  per layer) passes in the hub (12.7 mV) and in the PHY + corridor window (29.6 mV, worst point in the SM below).
- It is marginal in the SM: 31.7 mV interior, 47.0 mV at the die edge.
- It fails by 4-6x on every SerDes macro: 146-203 mV at the assumed 12.1 W/mm2.
- The HBM PHY itself is not the hot spot at the sourced estimate (10.5 W, 1.05 W/mm2). It sits under 29.6 mV only
  because power bumps sit directly over it. With the PHY macro band bump-free (all signal bumps), the grid cannot feed
  it at all.

## Power estimate (step 2): `power_map.json`

Point: peak in-phase a20 (0.2 activity on every non-clock net, clock every cycle), TT 0.70 V. Total **642.7 W** over
461.5 mm2 = 1.39 W/mm2.

| Class | Partitions | Area mm2 | W | W/mm2 | Source |
|---|---|---:|---:|---:|---|
| SM | q_sm0-3 x 2 | 181.4 | 395.1 | 2.179 | r25gp hfd_sm measured a20 (`results/physical/die_evidence_20261009/hbm_r25gp_power.json` masters.hfd_sm) |
| SU | q_su* | 58.5 | 65.9 | 1.127 | r25gp hfd_su (measured lanes + estimated envelope) |
| SFU core | q_b11* | 21.4 | 30.8 | 1.438 | r25gp hfd_sfu |
| HC bank | q_b0* | 19.6 | 13.7 | 0.700 | r25gp hfd_hc |
| IDX score | q_b10* | 9.7 | 10.2 | 1.05 | r25gp hfd_idx_score_native_grid (ASSUMED there) |
| hub, root | q_hub x 2, root | 50.2 | 47.1 | 0.938 | r25gp proposed_dens.hub (measured) |
| spine / ft / corners / PHY_N + io remainder | spt, spb, spu, vsN, mca, mcb, PHY_N, io | 120.7 | 46.6 (+IO below) | 0.424 | r25gp proposed_dens.spine (measured) |
| HBM3E PHY (u_phy_Q, 8500 x 1177 um macro at the die edge) | PHY_N | 10.0 | **10.48** | 1.05 | 1.2 TB/s (technology.json hbm3e published ceiling, Micron) x 0.8 pJ/bit (results/rtl/hbm_accel_qwen_die_power_20261006/README.md, O'Connor) + 2.8 W idle (technology.json memory_interface_idle_w_per_stack). ASSUMED |
| SerDes ot_pdie_serdes x 5 (600 x 600 um) | io, spb0, vsN0 | 1.80 | **21.84** (4.37 each) | **12.12** | 6 x 112 Gb/s (tools/die_plan/die_io.py) x 6.5 pJ/bit (results/uarch/hbrom/inputs/hbrom-power.json board_serdes_112g). ASSUMED rate |
| host UCIe (259 x 1555 um) | NW_io | 0.40 | 1.02 | 2.54 | 2 x 64 x 16 Gb/s (UCIe-A x64, 16G ASSUMED) x 0.5 pJ/bit (hbrom-power.json ucie_advanced) |

- Hottest by density: the 5 SerDes macros (12.1 W/mm2), then the UCIe (2.5), then the SMs (2.18).
- Hottest partitions by total power: the 8 SMs (49.4 W each). Next are the hubs (18.8 W each), PHY_N (13.7 W incl. the
  remainder band) and root (9.4 W).

Cross-check (`cross_check` in the JSON):
- Plan cell estimates (170.4M cells) x 0.33 uW/inst (median of the measured r25gp logic tiles) = **56 W**.
- That is 11x below the area estimate. The B2r2 SM slot holds 8.28M cells in 22.7 mm2 (0.37 Mcell/mm2), against
  7.8 Mcell/mm2 on the r25gp SM tile.
- So the area x density map used here is a conservative upper load, and the true SM density is open until the HNX-SM
  kits report power.
- IR is linear in current, so any rescaling of a class scales its drop proportionally.

## Method (step 4b): `tools/die_trial/hbm_b2_ir.py`

This is the ir_1012 tile-current method (`tools/hbm_die_ir_window.py`).

**Grid**
- Die grid = plan die.pg.grid: M8 H / M9 V, 0.48 um wide, 8.64 um pitch per net, VDD centre at 4.32 mod 8.64 and VSS
  at 0 mod 8.64 (die phase, checked with OT_STRIPE). M8-M9 vias at every same-net crossing.
- Partition PG is abstracted as the mock-LEF M7 stripes (VDD 4.128 / VSS 4.512 mod 8.64, 0.288 um), on load tiles of
  43.2 um in die phase, with M7-M8 vias.
- The partitions' internal M5/M6/M7 grids, their IR and their real via access are **not modelled**. The partition
  views are mock abstracts.

**Loads, bumps, solve**
- Each tile carries power-map current x its area. IO content rects replace the partition density inside them.
- C4 bumps: 45 um array, checkerboard per net (63.64 um per-rail pitch), 20 um, ideal 0.7 V, no package impedance
  (assumed, as ir_1012).
- Windows are solved with a two-bump-pitch guard (127.3 um); only nodes inside the inner window count.
- The voltage report is per load tile, so the resolution is 43.2 um.
- Layer resistance is the ASAP7 `setRC.tcl` value: M8 8.45e-3 and M9 8.90e-3 kOhm/um at the 0.04 um min width,
  i.e. about 0.34 / 0.36 Ohm/sq; V7 8.2, V8 6.3 Ohm. That is ASAP7's published RC. A production thick top metal is
  several times lower, so absolute mV are pessimistic in that sense.

**Coarse full die (full_s4m)**
- Width and pitch are both multiplied by 4 (1.92 um at 34.56 um). Per-layer conductance per um of die (width/pitch)
  is unchanged, so the grid sheet resistance is preserved.
- Load tiles are 172.8 um. Same bumps.
- It resolves die-scale gradients but not the sub-bump-cell spreading that dominates the exact windows, so it is not a
  substitute for them.

### Runs

| Case | Host:dir | Loads | Wall | Peak RSS | pdngen / IR VDD / IR VSS (s) |
|---|---|---:|---|---:|---|
| w_phy | intel2:/srv/opentallas-scratch/claude/trial-hbm/ir/w_phy | 31,465 | 1:04:48 | 22.6 GB | 2374 / 436 / 679 |
| w_phy_nobump | intel2:.../ir/w_phy_nobump | 31,465 | 1:04:38 | 22.4 GB | 2369 / 448 / 657 |
| w_hub | intel2:.../ir/w_hub | 12,138 | 11:38 | 8.3 GB | 311 / 118 / 145 |
| w_sm | intel2:.../ir/w_sm | 13,200 | 14:12 | 9.2 GB | 404 / 113 / 192 |
| w_io | intel2:.../ir/w_io | 2,550 | 0:56 | 1.7 GB | 10 / 13 / 14 |
| w_spb0 | intel2:.../ir/w_spb0 | 1,862 | 0:41 | 1.3 GB | 6 / 8 / 12 |
| full_exact | epyc3:.../ir/full_exact | 247,616 | stopped at 4:10:37 in pdngen | 4.6 GB | NOT COMPLETED |
| full_s4 (120 GB cap) | epyc2:.../ir/full_s4 | 15,476 | 32:20, killed (signal 9, OOM at the cap) | 125.6 GB | 848 / - / - |
| full_s4m (400 GB cap) | epyc3:.../ir/full_s4m (started 12:14 PDT) | 15,476 | > 2:10 when written, still running | 180 GB so far | 994 / - / - |

- The pdngen time is superlinear in the number of load macros: 12k loads 5 min, 31k loads 40 min, 247k loads > 4 h
  unfinished.
- An exact-grid full die needs the grid written directly as DEF special nets (no pdngen macro-grid insertion). That is
  NOT RUN in this trial.

Commands:
```
python3 tools/die_trial/hbm_b2_power.py physical/die_plan/hbm_arch/B2r2/die_plan.json --out results/die_trial_1024/hbm_b2/ir/power_map.json
python3 tools/die_trial/hbm_b2_ir.py generate --plan PLAN --power power_map.json --out DIR [--window X0 Y0 X1 Y1] [--scale 4 --tile 172.8] [--no-bumps ...]
ot-run --mem 48 --threads 8 --hosts intel2 --dir /srv/opentallas-scratch/claude/trial-hbm/ir -- ./ir_run.sh DIR 8 48   # tools/die_trial/ir_run.sh
python3 tools/die_trial/hbm_b2_ir.py record --out DIR      # -> DIR/result.json (copied to cases/*.json with runtime)
python3 tools/die_trial/hbm_b2_render.py power|ir ...       # PNGs
```

Files here:
- `power_map.json`: per partition, IO regions, 436 hard cores, sources.
- `cases/*.json`: result + runtime per case.
- PNGs: `power_density.png`, `ir_windows_VDD.png`, `ir_serdes_io_VSS.png`, `ir_serdes_spb0_VSS.png`.

Big outputs (ir_*.rpt, run.log, case.def) stay on the hosts listed; no pdn.odb is written. When full_s4m finishes, the lane owner records it with:
`rsync -a epyc3:/srv/opentallas-scratch/claude/trial-hbm/ir/full_s4m/ DIR/ && python3 tools/die_trial/hbm_b2_ir.py record --out DIR && python3 tools/die_trial/hbm_b2_render.py ir --power power_map.json --case DIR --case <windows...> --net VDD --out ir_fulldie_VDD.png`.
The full-die row then replaces NOT COMPLETED.

## Visual review: what looks wrong

These come from reading `power_density.png`, `ir_windows_VDD.png` and the two SerDes zooms.

1. **SerDes macros are the hot spots, by far.**
   - All 5 SerDes are 600 x 600 um squares at 12.1 W/mm2, 5.6x the SM density.
   - In both zooms the drop inside the SerDes has a checkerboard at the bump pitch: tiles next to a bump are about
     40 mV, tiles between bumps 85-140 mV.
   - So the drop is local spreading from each bump through the thin M8/M9 mesh, not a die-scale gradient. The plan grid
     cannot carry 12 W/mm2.
   - A SerDes needs its own supply / dense PG (about 5x the M8/M9 coverage, or M7+ local straps and bump-per-cell
     power), or the 6.5 pJ/bit x 672 Gb/s figure must be put on a separate analog rail.
   - It also does not match the plan: no SerDes has an own-supply rail declared.
2. **Die-edge SerDes are worse.**
   - The NW_spb0, NE_spb0 and vsN0 SerDes sit 8.64 um from the S die edge. Their VSS worst (141 mV) is on the edge
     row, where the assumed bump lattice has no VSS row.
   - The NW_io SerDes is 276 um in from the W edge, behind the UCIe, and violates io_edge_max 200. NE_io's SerDes is
     342 um in, on the inner side (top F4).
3. **The HBM PHY row is not a hot spot at the sourced estimate** (1.05 W/mm2 in the macro band, 0.42 in the rest of
   PHY_N). In the PHY window the PHY band is dark, and the window worst (13.0 / 16.7 mV) sits in NW_sm1 at the W edge
   of the window. But:
   - (a) 0.8 pJ/bit is the lean I/O-only figure. The repo's logic-die HBM path figure is 10.19 pJ/bit incl. the
     controller, and the controllers sit in the hub.
   - (b) The bump-free PHY sensitivity gives a nonsensical 4.5 V: the plan grid has essentially no lateral reach, about
     a bump cell.
   - So the PHY band must keep PG bumps interleaved with its ~1900 signal bumps (5698 sites, 33% used by signals).
     That has to be planned in the bump map, which the plan does not have yet.
4. **The SMs are marginal.**
   - 2.18 W/mm2 over 22.7 mm2 slots gives 12.5 mV VDD in the interior, and 31.7 mV interior rail sum (from the
     VSS-edge side). It is 47 mV with the die-edge bump artefact.
   - Any SM power above the estimate, or a real package/bump resistance, pushes it over 35 mV.
   - The SM density is the largest open number: the cell-count cross-check is 11x lower.
5. **The hub (0.94 W/mm2) and the spine / vsN corridors (0.42 W/mm2) are cool**: 12.7 mV, dark in the map.
6. **Grid weak spots seen in the maps.**
   - The die-edge rows and columns (one-sided bump support) show up as the bright first tile column in the SM window and
     as the worst row in spb0.
   - There is no weakness at partition abutments, because the die grid is continuous over them by construction.
   - Partition-internal M5-M7 grids are not modelled, so a weak spot inside a partition would not show here.
7. **Power-map oddities.**
   - vsN0 ranks as the hottest partition by average density (2.5 W/mm2) only because a SerDes sits in a small spine
     chunk.
   - The two PHY-row corner blocks mca/mcb (4 x 8.65 mm2) are charged spine density for logic they do not have yet.
     They are reserved for PLL / decap, which makes them an ideal place for decap and extra PG bumps.
