# S81.IR: IR over the SerDes windows with the VDDPHY supplies (OWNER decision 7), 2026-10-25

**Verdict.** The plan as written FAILS. The `--split` candidate in `physical/die_plan/s81/pg_domains.py`, measured
the same way, PASSES.

- **Plan as written** (s81-1024r@1e44e77664, head 59a2f733c1): the separate supply itself works. VDDPHY is 8-19 mV.
  Two problems remain:
  - Electrical: core VSS reaches 40.9 mV at the WS row's domain edge.
  - Structural: the domain rect covers core logic that has no core supply.
- **Split candidate**: every rail is 35 mV or less. Core VDD is 27.5-29.0 mV, core VSS 29.6-30.1 mV, VDDPHY
  14.5-14.9 mV and VSSPHY 11.5-13.3 mV.

## Method

The method matches TRIAL-S81 10-24 (claude/trial-s81-1024@c2713abad0 `die_trial.py irwin`), so the numbers compare.

- **Solver.** Window PDNSim (`analyze_power_grid`) at 0.7 V. Image `openroad/orfs:asap7lock` (sha256:16470cea1d34).
  The runs were diagnostic docker probes on epyc2 (8 threads, 32-80 GB each). Full-die PSM was not used: it
  segfaulted at 119 GB.
- **Core grid and load.** Die grid M8/M9 0.48/8.64. Partition PG is modelled as M7 stripe pins on abstract load tiles
  of 43.2 um or less. The core load is a uniform 0.15 W/mm2 (the trial value).
- **Core bumps.** Die C4 on a 150-um lattice, VDD/VSS by parity. The lattice leaves out channels, die IO windows and
  domain rects. Each source sits on the actual M9 metal of its own net.
- **Domain model.** Each `die.pg.domains` rect is an OpenROAD region voltage domain:
  - pdngen cuts the core grid out of the rect and lays the domain grid M8/M9 1.92/8.64 inside it.
  - The domain's own 45-um checkerboard C4 rows sit over `bumps.rect_um`.
  - The domain ground is modelled as its own net, VSSPHY, because on die it only joins the core VSS through the
    package. That is conservative.
- **PHY load on VDDPHY.**
  - 4.368 W per SerDes window = 6 lanes x 112 Gb/s x 6.5 pJ/bit (TRIAL-HBM `hbm_b2_power.py`, sourced
    `board_serdes_112g`).
  - Plan as written: spread over the whole io window (3.54 mm2), which gives 1.23 W/mm2.
  - Split candidate: spread over the PHY macro (2.39 mm2), which gives 1.81 W/mm2.
  - For comparison, the trial's 0.15 W/mm2 over the window would be 0.53 W. VDDPHY is linear in this load, so that
    value gives about 1/8 of the drops listed here.
- **Gate.** 5 % of 0.7 V = 35 mV per rail. This is the trial's interior reference (30 mV = 4.3 %) and the HBM B2m
  budget. The trial reported VDD only; here VDD, VSS, VDDPHY and VSSPHY are each held to 35 mV. The supply + ground
  sum is INFO.
- **Windows.**

  | Window | Die | Area (um) | SerDes windows covered |
  |---|---|---|---|
  | A | S81 south | 0-10368 x 0-2851 | WS2, WS1, WS0, WS3 (reserve) |
  | B | S81 north-east | 20131-31951 x 21894-24745 | EN2, EN0, EN1, EN3 (reserve) |
  | A | head south | 0-11837 x 0-2851 | WS1, WS0, HOST0, HOST1 (ES0 is clipped by the window and not judged) |

- **Tooling limit.** pdngen 26Q3 connects the macro loads only in the first region domain, and PSM traces one island
  per net. S81 window A has two domain-union boxes (the WS3 box is taller), so its VDDPHY/VSSPHY were solved once per
  box (`--phy-box 0/1`; the other box's domain is on a separate, unsolved net).

## Results (worst drop, mV)

| case | VDD core (near domain) | VSS core | VDDPHY | VSSPHY | verdict |
|---|---:|---:|---:|---:|---|
| S81 A base (no domains = trial) | **335** | **338** | - | - | FAIL (trial 235 on a smaller window) |
| S81 B base | **831** | **834** | - | - | FAIL (EN2-EN3 is an 11.5-mm run with no bumps) |
| head A base | **306** | **306** | - | - | FAIL (trial 270) |
| S81 A plan | 30.9 | **40.9** | 9.7 (WS2) / 14.4 (WS3) / 19.2* | 9.0 / 13.9* | FAIL (VSS) + structural |
| S81 B plan | 30.2 | 34.95 | 9.8 (EN3) | 8.8 | marginal + structural |
| head A plan | 28.4 | 30.9 | 9.8 (WS1) | 9.0 | electrical PASS, structural FAIL |
| S81 A split | 28.8 | 30.1 | 14.5 (WS2) / 14.8 (WS3) | 12.9 / 11.5 | PASS |
| S81 B split | 27.5 | 29.6 | 14.9 (EN3) | 13.3 | PASS |
| head A split | 29.0 | 29.9 | 14.5 (WS1) | 12.9 | PASS |

\* The plan's WS0 domain overlaps the WS3 domain by 127 um. The WS0 macro sliver in WS3's box is then fed from WS3's
grid only, which gives 19.2 mV. This is an artefact of the overlap; see S2.

The interior far from the windows is 25-31 mV in every case, the same as the trial's 30 mV.

Maps were checked by eye:
- `ir_map_<case>.png`: dashed red = domain region box, orange = domain bump rows, cyan = PHY load rect.
- Base cases show the trial hotspot over the bump-less windows.
- Plan cases show the VSS hotspot along the domain's top edge, at y 1394-1500 in the S81 WS row.
- `ir_map_s81_A_split2.png` is uniform up to the domain edges.

Case-to-file key: plan = `*_dom` (+ `s81_A_dom_b0/_b1` for VDDPHY); split VDD/VSS = `*_split2`; split
VDDPHY/VSSPHY = `s81_A_split_b0/_b1`, `s81_B_split`, `head_A_split`. The latter two used the split plan before edge-bump
relocation, which changes only core C4.

## Findings on the plan as written (s81-1024r@1e44e77664, s81-head-1024r@59a2f733c1)

- **S1 (structural).** The domain rect is the whole serdes partition plus a 63.64-um guard reaching into the
  neighbours. The partition holds the PHY plus "a strip beside it" with the boundary flops and the ft0/ft1 stations
  (the type note says this).
  - Over the whole rect, M8/M9 carry VDDPHY/VSS only. The core cells under it (that strip, plus a 63.64-um band of
    the fW0_* neighbours) therefore have no core M8/M9 VDD.
  - This is 1.58-1.64 mm2 of uncovered core area per window row in these windows.
  - In this model that logic is either on VDDPHY (the whole window carries the PHY load) or unsupplied.
- **S2 (structural).** Adjacent domains overlap by 127 um: WS2/WS1/WS0/WS3 on S81, and the whole south and north rows
  on the head. Two "separate" supplies would then share the same straps.
- **E1 (electrical).** The core lattice row at y 1347 falls inside the guard and is dropped. The core row above the
  domain then loses its nearest VSS bumps, which gives 40.9 mV VSS (S81 A) and 34.95 mV (S81 B). The same happens
  with VDD where the parity puts VDD bumps there.

## Candidate fix (written in `pg_domains.py --split`, measured above)

1. **PHY macro footprint.** The macro gets a published 7-nm 112G LR area: 0.40 mm2/lane x 6 = 2.4 mm2 (the HBM B2m
   README figure). It sits on the die-edge side of the window, inset 63.64 um from the partition's E/W edges and
   from its inner edge. For a 2885.76 x 1226.88 window this gives 2758.48 x 872.64 um; for WS3 it gives
   1315.6 x 1831.68 um.
2. **Domain rect.** The domain is the macro plus the guard, and it stays inside the serdes partition: it never enters a
   neighbour, and adjacent domains abut without overlap (fixes S2). The VDDPHY/VSS 45-um rows sit over the macro
   only.
3. **Core strip.** The rest of the window (290.6 um on the inner face of a 1227-um window, 558 um for WS3) is a core
   strip on the core grid with core C4. The boundary flops and the ft stations go there (fixes S1).
4. **`core_edge_bumps: relocate`.** A 150-um lattice C4 that falls inside a domain rect, within half a pitch of an
   edge facing core, moves 15 um outside that edge (fixes E1). Without it the WS3 domain's W edge measured
   38.8 mV VDD / 39.7 mV VSS.

Margin:
- VDDPHY at 14.9 mV leaves room for 2.3x the PHY power before it reaches 35 mV (about 10 W per 6-lane macro,
  15 pJ/bit).
- VDDPHY in the split is higher than in the plan because the same power sits in a 2.4 mm2 macro instead of
  3.54 mm2.

Follow-ups for the plan steward, LEAFPLAN and the head plan. These are not done here; they are the cost of adopting
the split:
- The serdes partition's ft0/ft1 slot windows (local y 119-228 and 570-680 um today) and its boundary-flop rows must
  move into `core_strip_um` (local y 936-1227 for the 1227-um windows).
- The u_phy slot shrinks to `phy_macro_um`.
- `die_io` rects stay unchanged (signal sites over the macro).
- The head plan takes the same `pg_domains.py --split`; its 12 domains were generated and measured with it.

## Files

- `tools/die_trial/s81_ir_domains.py`: the tool (generate / record / render).
- `physical/die_plan/s81/pg_domains.py`: adds `--split` (the candidate); the default output is unchanged.
- `summary.json`: per-case worst drops, loads, bump counts and uncovered area.
- `ir_map_*.png`: the maps.
- Run dir `epyc2:/srv/opentallas-scratch2/claude/s81-ir/<case>`: run.tcl, logs, `ir_*.csv`, result.json. Plan copies
  `plan_*{,_split}.json`.
