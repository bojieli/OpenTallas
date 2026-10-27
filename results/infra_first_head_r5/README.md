# INFRA-FIRST-HEAD-5: s81_head PG with real C4 bump pads, 150 um vs 75 um

This lane follows NUMBER-CHECK-HEADPG and the COORD ruling of 10-27 06:34. The gate is **VDD drop + VSS bounce <= 35 mV**. The OWNER rule makes 150-um bumps the basis.

Branch: `claude/infra-head5-1027`. It is based on R4 4b36bdd452, with the HEAD-CORE-R15 infra delta d07748a7fc (plan c218aebc) merged in.

**Plan delta:** die.pg.grid M9 width goes from 6.48 to **12.96 um**. Pitch (34.56) and offset (17.28) are unchanged. The plan sha is now 33029005. G0 PASS and G0C PASS, each with 0 errors and 6 warnings (g0.log, g0c.log, g0c_report.json).

All numbers below are own-tool results and are **UNCHECKED**.

## 1. Tool: real bump pads

`die_trial.bumps_tcl(..., pad_um=D)` models each C4 bump as a D x D pad-metal plate over M9, centred on the bump. Each plate has a V9 farm to **every** same-net M9 strap under it. In PDNSim this becomes one BTerm per bump, with one BPin per overlap between the pad and a strap.

* `pad_um=0`, the default, keeps the legacy point bump, so other callers see no change.
* Fallback count: 0 in every run.

Pad metal and V9 are treated as ideal. Their bound is below 1 mV:

* **V9:** 6.3 ohm per cut (setRC). A 12.96 x 75 overlap holds about 100k cuts at 0.097 um pitch, giving under 0.1 mOhm, i.e. microvolts at about 80 mA per bump.
* **Pad plate:** an ASSUMED thick Al pad at about 0.02 ohm/sq with about 80 mA gives under 1 mV.

`infra_pg.window_kit` has three new options:

* `pad_um`;
* `nets` (VDD+VSS);
* `loads` (a power map).

`head_pg_sweep.py psm` has new flags `--pad` (sweep), `--map cores`, `--vss` and `--tile`. Tests: `tools/s81_head/test_head_pg_pad.py` (3 PASS) and `test_die_infra.py` (PASS).

## 2. Power map (measured, the same for both pitches)

The map (`core_map`) uses the measured R4 activity: VCD, TB_PASS, OpenSTA.

* Each hd_tile hard core carries its own watts on its plan outline:
  * elemA: 0.1244 W, giving **1.2325 W/mm2**;
  * elemB: 0.1189 W on 277.652 um square, giving **1.542 W/mm2**. This is above the 1.462 W/mm2 on the kit area, so it is conservative.
* Glue is the tile upper bound minus the cores, giving 1.211 W/mm2 and 0.9238 W per tile.
* Other head types run at the tile upper bound of 1.2577 W/mm2 (ASSUMPTION, as in R4).

## 3. Windows

All windows use 43.2-um load blocks with M7 pins, and the plan grid M8 0.48@4.32 is unchanged.

* **int** window: 2.97 x 2.97 mm in the tile field at (3041, 5944). "Interior" means blocks at least 450 um from every open window edge. The worst point lands on the elemB hotspot row.
* **edgeW** window: x from 0 to 2074, i.e. the real die W edge (channel plus turn columns, where bumps stop at the die edge).
  * "die-edge band" means x < 450.
  * "inner" means x >= 450.
  * Both exclude 450 um next to the open y and x1 edges.

Metric: the effective supply loss at a block, i.e. VDD drop + VSS bounce **co-located** (the maximum of the sum at the same block). The separate worst values per net are in pg/sum_*.json.

## 4. Drop below M7

Slice solve on the elemB hotspot core (6_final.odb of head-core-r10/elemB_hold2):

* M1-M5 is the core's own signed PDN.
* M6 0.288@4.32 and M7 0.288@8.64 are ASSUMED tile straps, matching the window block's M7 pins.
* Sources are STRAPS at the top.
* PDNSim charged 0.137 W, about 20% above the measured 0.114 W, so this is conservative.

Result: VDD 2.10 / VSS 3.38 mV; **co-located 5.13 mV max** (p99.9 3.07 mV). This **5.13 mV** is the below-M7 margin added to every total below. Script: tools/s81_head/head_pg_below_m7.tcl; output in below_m7/.

## 5. Results: VDD+VSS co-located above M7, + 5.13 below M7, gate 35 mV

| bumps | grid M9 | pad | interior | die-edge band | edge inner | verdict |
|---|---|---|---|---|---|---|
| 150 | C3 6.48@34.56 | 50 | 64.48 + 5.13 = 69.6 | 48.77 + 5.13 = 53.9 | 64.20 + 5.13 = 69.3 | FAIL |
| 150 | C3 6.48@34.56 | 75 | 37.45 + 5.13 = 42.6 | 32.76 + 5.13 = 37.9 | 37.42 + 5.13 = 42.6 | FAIL |
| 150 | **12.96@34.56** | 50 | 36.43 + 5.13 = 41.6 | 30.11 + 5.13 = 35.2 | 35.56 + 5.13 = 40.7 | FAIL |
| **150** | **12.96@34.56** | **75** | **24.77 + 5.13 = 29.9** | **19.87 + 5.13 = 25.0** | **23.65 + 5.13 = 28.8** | **PASS (5.1 mV margin)** |
| 75 (model only) | C3 6.48@34.56 | 37.5 | 16.67 + 5.13 = 21.8 | 13.76 + 5.13 = 18.9 | 16.51 + 5.13 = 21.6 | PASS (13 mV margin) |

**150 um passes only with M9 12.96@34.56 and the nominal 75-um pad.** The pad size is the deciding package input: a 50-um pad fails by 6.6 mV.

Worst per net, not co-located, 150/G12/75 interior: VDD 15.11, VSS 15.07 mV.

Edge-artefact rows near the open window edges reach 46.6 mV in render/ir_colocated.png. They are excluded from these results, as in NUMBER-CHECK.

## 6. Side-by-side 150 vs 75 (COORD owner question)

Both pitches use the same power map and the same windows.

| | 150 um (adopted basis) | 75 um (model only, fallback) |
|---|---|---|
| (a) IR VDD+VSS, interior / die-edge band / edge inner (mV, incl. 5.13 below M7) | 29.9 / 25.0 / 28.8 | 21.8 / 18.9 / 21.6 |
| (b) M8 PG tracks | 29.4% (0.48@4.32), 70.6% free | 29.4%, 70.6% free |
| (b) M9 PG tracks | **85.7%** (12.96@34.56), **14.3% free** = two 4.32-um gaps per 34.56 um, each 2.32 um usable after 1.0-um wide spacing (about 29 tracks at 0.08) | **48.3%** (6.48@34.56), **51.7% free** = two 10.8-um gaps per 34.56 um (about 110 tracks each) |
| (b) Pad layer | 75-um pads: 25% of the Pad area, above M9, blocking no M8/M9 track | 37.5-um pads: 25% |
| (c) clock lanes | the 16W lane fits in every M9 half-gap (lane centre band 7.80-8.64 um from the VSS centre, 1.0 spacing), and so does 2x16W | 16W/2x16W fit (band 4.56-8.64) |
| (c) mesh m5 | 95 M9 straps; 32 move by <= **3.24 um** (snap_lanes on the new grid), 0 M8 moves | 0 moves (the current grid) |
| (c) M8 rows <= 144 um | M8 lanes every 4.32 um (gap 1.68, max jog 1.06), so any row pitch fits | same |
| (c) pads | pads sit on the Pad layer above M9 and V9 lands only on same-net PG straps, so **no detour, 0 um extra per leg** | same, 0 um |
| (d) core power bumps, die | 11,628 (5,814 VDD / 5,814 VSS) | 45,908 (22,954 / 22,954) |
| (d) per int window (8.83 mm2) / edgeW (6.16 mm2) | 380 / 247 | 1,600 / 1,040 |

## 7. M9 left over for die-top signals and clock lanes (task 3)

On the 12.96 grid, PG takes 85.7% of M9 and 14.3% stays free, i.e. about 1,680 M9 tracks per mm.

* **Die signal demand:** G2 die probe usage was M9 0.02% / M8 0.01% (S81-HEAD G2 report on an earlier plan; not re-probed, UNCHECKED). Free M9 is therefore about 700x the demand.
* **Clock:** the 95 M9 clock straps each take one 16W lane, and all of them fit. Render pg_tile_zoom.png shows them in the half-gaps.
* **Mesh owner:** the next mesh build (HEAD-CORE R17 owns head_mesh_r3) needs `--pg-lanes` on this plan, which moves 32 straps by <= 3.24 um.

## 8. Renders (viewed by the author)

* render/pg_tile_zoom.png: tile tW3b4 with its neighbours.
  * M9 VDD/VSS 12.96 straps;
  * 150-um checkerboard 75-um pads, each over about 2 same-net straps;
  * clock M9/M8 straps in the gaps;
  * hard cores, with elemB orange.
* render/ir_colocated.png: G12 p75 int map. Interior 10-25 mV; the hot rows are the open window edges.

## Evidence

Scratch data:

* intel1:/srv/opentallas-scratch2/claude/infra-head5-1027/pg/*_int
* epyc2:/srv/opentallas-scratch2/claude/infra-head5-1027/{pg/*_edgeW,pg75,below_m7}
* intel2:/srv/opentallas-scratch2/claude/infra-head5-1027/pg (kits)

Each kit holds run.log/psm.log and ir_VDD/VSS.csv. PDNSim used 13-25 GB and 13-27 min per kit.
