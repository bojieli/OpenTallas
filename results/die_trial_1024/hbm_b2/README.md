# TRIAL-HBM: trial die-level run of the HBM accelerator B2r2 plan (2026-10-24)

Lane TRIAL-HBM. Branch claude/trial-hbm-1024 (now on codex/trial-hbm-1024 @0404dd4648 + this record).
The plan of record is `physical/die_plan/hbm_arch/B2r2/die_plan.json` @3277b5e78b. It was read only, never edited.

This is an industry-style early full-chip prototype:
- every partition is an abstract at its exact plan origin and orient;
- the die PDN and the die clock distribution are built;
- every inter-partition lane hop is globally routed at die scale;
- then die STA and IR.

None of this is a closure claim. No B2r2 partition is hardened: G3 none.

**Plan vs brief.** The brief speaks of "four clusters, one per HBM stack". B2r2 as committed is different:
- two MY-mirrored quad tiles (8 SM) under ONE HBM3E PHY (PHY_N, top centre);
- 25.19 x 18.32 mm = 461.5 mm2;
- 88 partitions, 49 types, 436 hard cores, 298 lanes, 614k port bits;
- 5 SerDes plus a host UCIe.

The "four clusters / one per stack" picture is the old r25gq monolithic die (4 PHYs). Its record is the 1,374,522-overflow GRT in `results/physical/die_iter_1012/r25gq/README.md`. The plan has since moved to B2l. Codex's B2l fabric successor is listed under "open" below.

## Results at a glance

| step | result | verdict |
|---|---|---|
| (1) die top: abstracts, keep-outs, PDN, IO | 88/88 mock-LEF partitions placed exactly (0 overlap, 0 outside the die); die PDN M8/M9 + 6.2M M7-M8 vias per net; check_power_grid PASS on VDD and VSS; die-net GRT overflow 394, all from taps under the PHY_N / UCIe keep-outs; DRT not run. Tool bug: gen.py writes origins with %g, which rounds every origin >= 10 mm, so 23 macros were refused (see top/README.md) | PASS with findings |
| (2) H-tree clock built in OpenROAD | 2045 taps; insertion SS/TT/FF 5.81 / 4.72 / 3.98 ns mean; seam skew without OCV 54.5 / 45.1 / 38.5 ps (68 / 56 / 48 % of 80); **with +/-5 % OCV after CPPR 594 / 483 / 407 ps** | **FAIL** (R4 seam <= 80 holds only without OCV) |
| (3) die global route of all lane hops | **0 overflow** on M4-M9 at every own-logic derate tried (M4-M7 keep 50 / 25 / 10 / 3 %) vs **1,374,522** on the old monolithic die. Local hot windows exceed the plan's M8/M9 ft budget of 0.6 | **PASS** (route) / **WARN** (ft budget) |
| (4a) die fabric STA, budget mode (flop -> flop per hop, GRT RC, ideal common clock) | unbuffered: TT -1045 ps, 2.85M slew violations. Window repair_design: SS -95.7 / TT +83.8 ps at +87 % cell area. Codex BUF12 every <= 200 um: TT +358.7 / FF +74.5 ps (40-path vehicle). Hold FF -2.07 ps on 1277 abutted hops **at zero skew** | **FAIL** as planned (needs repeaters + seam hold pads) |
| (4b) IR (PDNSim, estimated power 642.7 W = 1.39 W/mm2) | rail sum on exact-grid windows: hub 12.7 / PHY_N+corridor 29.6 PASS; SM 47.0 (31.7 interior); **SerDes io 146 / spb0 203 mV** vs 35 mV; full exact die NOT COMPLETED (pdngen > 4 h); coarse full die running | **FAIL** (SerDes at 12.1 W/mm2; SM edge) |

## (3) Die global route: the 0.55 / 1.70x question

**Case.** `tools/die_trial/fabric.py`:
- 1,360,342 registers: 409,730 boundary flops at the plan pins, plus 950,612 ft stations at the plan station sites (`g2.py part_probe` semantics stitched over all 88 partitions);
- 1,155,477 hop nets.

**Partition abstracts:**
- hard cores block M4 up to their top pin layer (at least M5);
- other leaf outlines block M4-M5;
- SerDes, UCIe and the HBM PHY are keep-outs on M4-M9;
- die PG M8/M9 stripes and the H-tree NDR tracks are obstructions;
- the partitions' own logic is modelled as a layer derate on M4-M7 (plan fill is 1.0).

**Run.** OpenROAD GRT on M4-M9, 9.6 um gcells.

| case (M4-M7 left to the fabric) | overflow | WL m | GRT time | peak RSS | max raw track usage per 250-um window, M8 / M9 (guide-based) |
|---|---|---|---|---|---|
| derate 0.50 (G2 convention), epyc2 `fab_full` | **0** | 676.3 | 2.7 min | 23.6 GB | 0.73 / 0.71 |
| derate 0.75, intel1 `fab_adj075` | **0** | 677.8 | 36 min | 26.3 GB | 0.75 / 0.86 |
| derate 0.90, intel2 `fab_adj09` | **0** | 680.8 | 46 min | 26.4 GB | 0.79 / 0.85 |
| derate 0.97 (fabric ~ M8/M9 only), epyc2 `fab_adj097` | **0** | 687.6 | 112 min | 26.6 GB | 0.86 / 0.86 (render) |

- **The 1.37M-overflow failure class is gone at die scale.** There is no gcell overflow even when the fabric is pushed onto M8/M9 alone.
- **The old failure was 77 % in one central window.** Here the busiest window is still central, at the bottom of `root` / the hc-ring bank row (x 12.25-12.75 mm, y 6.25 mm). It carries M8 0.73 raw at derate 0.5 and up to 0.86-0.99 when M4-M7 are taken away. That is the next thing that would break.
- **Measured cut crossings agree with the plan's G0 cut_lines.** At y = 10195.2 the route has 74,647 bits crossing against 74,638 in G0. The worst full-line ratio over the raw tracks of the three crossing layers is 0.06 (horizontal) and 0.078 (vertical, x = 8959.68).
  - **The "cut 0.55" claim:** I found no 0.55 in the B2r2 record. G0C gives worst full cut 0.133, worst partition segment 0.437 (NW_b011), and cut_lines 0.101 / 0.055. Measured, the full cuts are tiny. The binding quantity is the **local M8/M9 window**, not the full cut.
- **M8/M9 hot windows (`render/congestion*.png`) all exceed the plan's M8/M9 ft budget** (cut_avail 0.6):
  - the hc-ring bottom row M8 highway, y 6.25-6.5 mm, x 8.4-16.8;
  - the two PHY -> hub M9 corridors in the spt columns, x 5.5 / 19.5;
  - the seam M9/M5 column from PHY_N down to `root`, x 12.2;
  - the hub west-face M9 at NW_b112 / NW_b113 (x 2.75, y 8.75), 0.85;
  - the SU-row M8 crossings.

  Inside those windows the partitions' own M8/M9 use (PG, local clock, core straps) has < 15-30 % left.

## (4a) Fabric timing, budget mode

DIE-STA's ILM / flat modes need routed partitions, and B2r2 has none. The fabric STA times every hop flop -> flop on die GRT parasitics instead. Corners SS/TT setup and FF hold; 60/25 ps uncertainty; period 833.333 ps. The leaf -> face-flop paths are inside the partitions and are not timed here.

**Hop lengths:**
- median 671 um;
- 896,100 > 500 um;
- 498,885 > 700 um;
- 14,397 > 850 um (per-bit spread beyond G0's window-centre maximum of 849.6 um);
- 506 > 900 um, all in lane L19_2 / L19m_2 into b103, up to 957 um = 0.96 of reach.

The plan puts stations at about 0.85 of reach, so **43 % of all fabric bits run at 0.7-0.96 of reach.** Every one of them needs repeaters inside the crossed partition.

**Unbuffered** (full die, GRT RC): TT setup -1045 ps, SS -1430 ps, 848,622 violating endpoints, 2.85M slew violations.

**repair_design** (window x 3-9 / y 5.5-11 mm, 130,929 nets, setRC average wire RC):
- 288,362 buffers;
- +87 % cell area over the flops;
- SS -95.7 ps (worst hop NW_spu0 -> NW_hub L21, 5 x BUFx8 in about 850 um);
- TT +83.8 ps.

The full-die repair runs were stopped or demoted (legacy, SS-influenced):
- `fab_rep_avg` was killed at 12:15 as superseded;
- `fab_rep_m8` on epyc2 is a diagnostic only.

**Codex BUF12 recipe** (BUFx12 at <= 200 um, explicit sites, 0 added cycles): TT +358.72 / FF +74.46 ps against bare TT -51.29 ps, on the 40-path native vehicle, commit 3fd63666dc.

**Hold.** With GRT RC, FF hold on the 2-um abutted boundary-flop hops is -2.07 ps on 1277 endpoints **at zero clock skew**. The window margin was +3.8 ps. The die tree alone gives 38.5 ps FF seam skew, before partition spread and before OCV. So every abutted seam needs hold padding of 40-80 ps, as the kit seam-hold rule (min input delay -40) anticipates. Without it, G4 hold fails on most of the 614k seam bits.

## (2) Clock

Full detail is in `clock/README.md` (sub-run, `tools/die_trial/htree_clock.py`).

**Build:**
- 8 levels and 1392 tree buffers, NDR 2W2S;
- 256 leaf drivers;
- 2045 taps, against about 980 assumed;
- GRT on M8/M9 with 0 overflow.

**Insertion** is 4.0-5.8 ns. That is 5-7 periods, against the 250 ps common latency.

**Seam skew:**
- without OCV: 38.5-54.5 ps;
- with 5 % OCV after CPPR: 407-594 ps.

The worst pair, NE_b112 | NE_hub, diverges at the die root.

**Plan findings:**
- leaf -> tap distances reach 1328 um, against "<= 400 um";
- 67 of 256 leaves drive no tap. The uniform 16x16 leaf grid puts four leaves on each single-tap SM and on the empty corner partitions mca / mcb, while the hub and band take 1.3-mm local nets;
- the trunk splits inside partition rows, so 46 abutted pairs only share the tree down to level 0-1.

## Visual review (owner order 08:05: rendered, looked at, findings)

Renders:
- `render/floorplan.png`: partitions by role, hard cores, keep-outs, lane bundles, H-tree;
- `render/congestion.png` (derate 0.5) and `render/congestion_adj097.png` (M8/M9 only);
- `render/hops.png`: hops > 700 um;
- `clock/htree_built.png`, `clock/tap_latency_heatmap.png`;
- the IR maps in `ir/`.

What looks wrong:
1. **Data flow from the PHY.**
   - The 9.4 kbit/row PHY <-> hub traffic leaves PHY_N at its S-face corners. It runs W/E through the empty mcb corners on M4/M8 (`congestion_adj097`: M8 block at y 16.3-17.3 mm, x 5.5-8.5).
   - It then turns down the narrow spt columns (1.8 mm wide) for about 6 mm to the su row and the hub.
   - In the M8/M9-only case those columns sit at 0.7-0.86 of raw M9.
   - It is the longest wire class on the die (SM_HBM 25 cycles in the price) and is routed through the partitions built to hold it, so it is by design. It has no spare capacity for ECO or for widening the PHY interface.
2. **The central window.** The old die failed in one central window. B2r2 still concentrates its traffic at the die centre bottom:
   - `root`'s bottom-left corner and the hc-ring bottom bank row b000..b003 / b000'..b003' form a continuous M8 band across the seam at y 6.3 mm;
   - a hot M8/M9 spot sits at (12.5, 6.25) mm.

   This is the hc ring plus seam traffic. It is the first window to saturate if partition logic needs more M8, and it is the hold-and-skew-critical seam too (the trunk root is there).
3. **Long wires.**
   - `hops.png` shows the hop-length distribution is bimodal: about 2-um abutted hops plus a huge 700-960 um population everywhere in the ft corridors (spt, vsN, spu, su rows, b-slices).
   - Diagonal-looking long hops inside the hub and b103 (L19_2) are the per-bit spread of wide windows. The station site is shared by all bits, so the edge bits of a 1-2 mm window add up to ~100 um.
   - Fix: per-bit station sites (Codex 6c04a26209 added audited per-bit FT sites) or narrower windows.
4. **Seams.**
   - The hub's west face toward b112/b113 and io is M9-hot (0.85).
   - The NW_b112 | NW_hub pair is also the worst clock seam (it diverges at the root). One partition pair is therefore both route- and clock-critical.
5. **Clock tree shape.**
   - A uniform leaf grid ignores tap density: leaves are wasted on the SMs and the mc corners, and the hub / band gets 1.3-mm local nets.
   - The trunk runs along the seam column, so the seam pairs share the trunk. But the trunk splits mid-row, so vertical neighbours (su | hub, sm | su) diverge high in the tree. That is where OCV hurts.
6. **IR (`ir/ir_windows_VDD.png`).** The SerDes macros are the hot spots, not the HBM PHY. Each is 600 x 600 um at 12.1 W/mm2 on the plan's 5.6 %-coverage M8/M9 grid, giving 146-203 mV; they need a dense local grid / dedicated bumps. The PHY_N window passes only because bumps sit over the PHY; with a signal-only PHY bump field, the 8.6 mm wide band cannot be fed laterally. The SM die-edge VSS (47 mV) comes from the one-sided bump lattice at the edge.
7. **Empty corners.** mca/mcb (2 x 2 x 8.7 mm2) carry only clock leaves and the PHY escape. That is wasted area, as the spec already notes.

## What would break at G4 today (numbers)

1. **Seam hold.**
   - Abutted hops have +3.8 / -2.07 ps FF hold margin at zero skew.
   - The die tree adds up to 38.5 ps FF seam skew (no OCV) and 407 ps with 5 % OCV.
   - Without hold pads on 614k seam bits, G4 hold FAILS.
2. **Clock OCV.**
   - The 4-6 ns insertion with CPPR down to level 0-1 for 46 pairs means the R4 seam gate cannot pass under any realistic derate above 0.4 %.
   - Needed: a lower-insertion distribution (a mesh or spine-grid at the band, or partition-local PLL/DLL taps) or seam-tolerant capture (forwarded_landing) on the 46 high-divergence pairs.
3. **Ft repeaters.** 499k hops > 700 um need about 2-3 repeaters each: about 1-3M repeaters (Codex B2l: 3.04M buffers). They must sit in the crossed partitions' M8/M9 ft corridors, which are already at 0.73-0.86 raw in the hot windows. TT closes with BUF12 @ 200 um; SS does not with average RC.
4. **M8/M9 ft budget.** The hot windows (hc-ring row and central window, spt PHY corridors, hub west face) are over the plan's 0.6 cut_avail. The partitions there have < 30 % of M8/M9 for their own straps and clock.
5. **IR.** The SerDes macros are at 146-203 mV against the 35 mV budget, and the SM edge at 47 mV. The die grid needs local densification and a real bump map.
6. **Not a problem:** global congestion (0 overflow at every derate, 677-688 m WL, 24-27 GB, minutes to 2 h on one host). The old 1.37M-overflow class is solved by B2's partitioning.

## Open / not run

- B2r2 full-die repair with legal rows on M8 RC (`fab_rep_m8`, epyc2): legacy diagnostic.
- B2l successor `B2l_fabric_buf12_legal_r4` (Codex: 4.63M cells, 3.04M BUF12 at explicit legal sites, M8-M9, ideal clock) is GRT-ing on epyc3 `/srv/opentallas-scratch/claude/codex-hbm/`. Adopted by TRIAL-HBM; collect when done.
- The fabric STA with the H-tree tap latencies applied (`clock/tap_latency.json` -> `clock_latency.tcl`) is not run. Unbuffered STA makes it moot; do it on the buffered B2l case.
- No DRT. No detailed extraction (GRT / placement RC only). No SI.

## Files and runs

**Tools:** `tools/die_trial/`
- `fabric.py`: the case;
- `fabric_report.py`: windows, cuts, STA;
- `render.py`;
- `htree_clock.py`;
- `hbm_b2_top.py`, `hbm_b2_power.py`, `hbm_b2_ir.py`, `hbm_b2_render.py`.

**Data:** `grt/report_b1000.json`, `grt/report_b250.json` (derate 0.5), `grt/adj*_report_b250.json`.

**Run directories:**
- epyc2 `/srv/opentallas-scratch/claude/trial-hbm/{fab_full,fab_adj097,fab_rep_m8,clock/full}`;
- intel1 `.../fab_adj075`;
- intel2 `.../fab_adj09`;
- localhost `.../fab_win` (window smoke + repair).
