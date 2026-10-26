# Native B2 ring corridor study, 2026-10-13

Reserve two 1,100-um horizontal service bands and use the wide attention/VM strips for vertical ring transport. The existing narrow SM gaps cannot carry even one full bidirectional ring edge. Actual leaf geometry supports a structural corridor allocation without treating all M7 PG as a solid wall, but native parent PDN/via exports and qualified transport endpoints are still missing. No GRT is launched or admitted by this study.

## Source and scope

[study.json](study.json) is reproduced by `python3 tools/hbm_native_ring_cut_1013.py`. It hashes the native v12 candidate, transport requirements, ring RTL, actual LEFs and pilot PG recipe. [routing_rules.json](routing_rules.json) records the actual pinned ORFS image, technology/track hashes, layer direction, pitch, and spacing. The study reads **5,748 actual child rectangles: 5,236 real LEF references and 512 open SM tile footprints**. All original children and dimensions remain present. PHY/service, native HC, VM8, glue, physical clocks/reset, seam transport and whole-die PDN remain open in the candidate.

Missing SM tile LEFs reserve their exact frozen footprint on M1–M7; this is an unknown-view reservation, not a claim that their final PG is a solid wall. Actual real-child OBS, PG and signal-pin rectangles are transformed through R0/MX/MY placement and expanded by conservative center-access spacing. For each corridor the transverse union of every protected shape along its full length yields tracks with no child obstruction anywhere on that straight lane. No wrong-way routing or timing exception is counted. Native parent PG/vias may consume additional tracks.

## Actual link demand and endpoint access

The ring RTL uses `CW: sid+1`, `CCW: sid-1`. A forward channel is **2,224 bits**, including valid and kind/VC; reverse credit is **two bits**, one per VC. Two opposing channels on one physical edge therefore carry **4,452 signals**. At the unchanged 0.55 occupancy limit this needs **8,095 usable tracks**, before clock/reset and other clients.

The actual `ot_vms_rstop` LEF has W-facing `l_in[2223:0]` on 1,267 M4 and 957 M6 pins; W `l_in_cr[1:0]` is M4. E-facing `l_out[2223:0]` uses 1,207 M4 and 1,017 M6 pins; E `l_out_cr[1:0]` is M6. A capacity-positive M7 spine still needs legal endpoint fanout, vias and registered stations from these exact pins; it cannot substitute a synthetic wide parent pin.

The candidate maps SW=0, SE=1, NW=2, NE=3. This produces edges SW–SE, SE–NW, NW–NE, NE–SW, including two diagonals. No SID remapping is assumed:

| Whole-die cut | Paired edges crossing | Signals | Usable tracks at 0.55 |
|---|---:|---:|---:|
| x=16,492.144 µm | 4 | 17,808 | 32,379 |
| y=12,990.264 µm | 2 | 8,904 | 16,190 |

An 8,095-track corridor serves one edge, not the full central cut. Endpoint D3 credits and measured endpoint throughput are separate transport gates: the ring owner measured only 0.5 flit/cycle on the existing ideal adjacent endpoint. Raw long flop chains cannot hide this.

## Actual directional supply

M6 is horizontal and M7 vertical, both at 0.064-um preferred pitch. M8 is horizontal and M9 vertical, both at 0.080 µm. Counts below already apply 0.55 to tracks remaining after actual child geometry. They exclude unexported native parent PDN/vias.

| Corridor | Lower-layer signal capacity | Upper-layer capacity with conditional pilot PG |
|---|---:|---:|
| SM vertical gap, 142.56 µm | M7: 1,223 | M9: 737 |
| SM horizontal gap, 36.72 µm | M6: 314 | M8: 189 |
| W full-height attention/VM strip, 3,600.264 µm | M7: 21,596 | M9: 18,610 |
| E full-height attention/VM strip, 3,600.264 µm | M7: 21,594 | M9: 18,607 |
| S service band, 1,000 µm | M6: 8,593 | M8: 5,171 |
| N service band, 1,000 µm | M6: 8,593 | M8: 5,169 |
| S service band, 1,100 µm | M6: 9,453 | M8: 5,687 |
| N service band, 1,100 µm | M6: 9,452 | M8: 5,685 |

The attention quad has 1,737 M7 OBS rectangles and 96 M7 PG rectangles; these are counted rather than replaced by an opaque bounding box. Most attention banks end at M6. The full-height W/E strips retain 39,267/39,263 continuous M7 tracks after every actual protected child shape. Applying the *conditional* pilot M7 overlay (.544-um straps, two nets at per-net pitch4.896) across each entire strip leaves 15,187/15,176 signal capacity. This is deliberately conservative with respect to where that pilot overlay is placed; it is not native PDN proof.

No selected real-child LEF exports M8/M9 OBS or PG. The 512 native SM tile PG exports remain open, with a source recipe targeting M7 (.288/10.8/offset1). Thus an upper signal window is possible in principle, but cannot be certified from absent SM exports. The pilot M8/M9 recipe preserves .48-um straps at4.896 per-net pitch and offset2.16. Technology width/spacing plus signal half-width exclude ±.30 µm around each strap center, consuming approximately24.51% before the 0.55 signal occupancy budget. No native whole-die strap/via rectangle export exists.

| Signals through one directional corridor | Empty M6/M7 minimum width | M8/M9 minimum with conditional pilot PG |
|---:|---:|---:|
| 4,452 | 518.051 µm | 857.812 µm |
| 8,904 | 1,036.102 µm | 1,715.623 µm |
| 13,356 | 1,554.153 µm | 2,573.435 µm |
| 17,808 | 2,072.204 µm | 3,431.246 µm |

These are signal-only sizing bounds. Clock/reset, station cells, endpoint access/via islands, other clients and IR/EM requirements require explicit reservations. Combining orthogonal M6 and M7 capacities to claim one directional bus fits is invalid.

## Concrete compatible floorplan alternatives

**Preferred: reserve service bands and attention-strip windows.** Reserve S band y=11,721.6..12,821.6 and N band y=24,703.2..25,803.2, x=21.6..32,962.688. Every existing child and the four unresolved HC reservations stays outside these bands. Reserve vertical W x=12,355.2..15,955.464 and E x=28,847.232..32,447.496 as explicit per-track M7 windows through actual protected geometry, rather than as blank bounding-box channels. They do not traverse unknown SM tile footprints.

Route SW–SE and SE–NW across the S band; route NW–NE and NE–SW across the N band. Carry the two diagonal edges between bands on the W attention/VM spine. Local endpoint approaches in W/E strips carry at most two paired edges. Each horizontal central crossing then carries8,904 signals, below M6 capacity9,452; the W vertical crossing carries8,904, below child-geometry M7 capacity21,596 and the conditional M7 overlay bound15,187. This preserves the current SID order and all child geometry; the script independently checks both bands against every child rectangle and each unresolved HC reservation, with zero collisions. It is a corridor allocation proposal, not a physical route: native parent PG/vias, competing native-unit nets and real relay station footprints must be bound before acceptance.

**Alternative: widen SM column corridors.** Increase each 142.56-um SM column gap to651.024 by moving second-column SM components +508.464 µm and attention/VM components +444.528 µm. The script verifies all5,748 retained child rectangles with **zero overlap and zero outside** on the same die. One empty M7 corridor carries5,594 signals, enough for one paired edge but insufficient for two. Current SID diagonals would need additional routing corridors; this is not independently a full ring solution. PHY/service/HC/VM8 fit and SM/attention/VM seam repricing remain open. Use this structural option if the native PG exports remove the attention-strip capacity needed by the preferred allocation.

**Upper-layer fallback: dedicated M8/M9 signal windows.** A single paired edge needs about858 µm transverse width with the pilot straps retained; two need1,716 µm. The existing SM gaps remain inadequate even using both same-direction layers. An upper window over real M7-capped tiles may become legal only after native LEF/PG/via exports prove access and all stations/launches satisfy actual track and clock gates. Do not remove PG stripes, lower the 0.55 reserve, ignore vias, or claim a nonexistent native IR result to admit it.

The proposed polyline planning lengths, calculated from every actual hard endpoint bit, are20.031–20.515 mm for horizontal neighbor links,29.358–29.803 mm for SE–NW, and33.012–33.496 mm for NE–SW. A500-um register-segment ceiling implies respectively41–42,59–60 and67 segments. These are geometric planning proxies, not physical routed paths or qualified clocks. The original direct-pin calculation used32–59 *relay stages* (one fewer than segments); the detours therefore add up to eight minimum segments. Price that latency and the elastic buffers in the native single-user calendar; do not preserve the old direct-hop price while implementing these detours.

The next concrete gate is to bind native parent PG/via geometry and missing unit/net reservations to the preferred corridors, obtain qualified endpoint and elastic-station views, then rerun exactness/credit/throughput and source-matched seam timing at the existing clock and uncertainty. GRT follows that cut and view audit.
