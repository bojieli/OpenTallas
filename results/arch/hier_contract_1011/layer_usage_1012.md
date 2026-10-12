# Tile layer usage vs the layer contract (2026-10-12)

Question (owner): tiles may route signals on M1–M6 (PG on M6), parent straps on M7, die top on M8/M9. Closed elements show few wires above M4. Is ≤M6 for tiles wasteful while die levels are congested?

Source: latest CLOSED job per block in `/home/ubuntu/closed_archive` (428 blocks: 356 logic tiles, 68 SRAM/ROM macro tiles, 4 parents with hard children), final `6_final.def`. Wire length = Manhattan length of NETS routes (signal + clock; SPECIALNETS/PG excluded); utilisation = WL / (block area / LEF preferred pitch), pitches from `asap7_tech_1x_201209.lef` (M1–M3 36 nm, M4–M5 48, M6–M7 64, M8–M9 80). Per-block numbers, via counts and DEF-track-based utilisation are in `layer_usage_1012.json`. Parser: one pass over each DEF on ot-epyc4.

## Signal utilisation per layer (424 tiles, parents excluded)

| Layer | median | p90 | max | area-weighted (sig+clk) |
|---|---|---|---|---|
| M1 | 0.0% | 32.5% | 68.4% | 9.5% |
| M2 | 5.6% | 19.9% | 33.1% | 5.4% |
| M3 | 5.8% | 26.2% | 38.2% | 5.5% |
| M4 | 1.9% | 13.8% | 40.5% | 2.6% |
| M5 | 0.6% | 7.3% | 36.2% | 1.3% |
| M6 | 0.6% | 6.1% | 31.1% | 1.7% |
| M7 | 0.3% | 4.1% | 24.6% | 1.1% |
| M8 | 0.0% | 0.0% | 0.7% | 0.0% |
| M9 | 0.0% | 0.0% | 0.2% | 0.0% |

- logic_tiles: M5 median 0.7% / p90 7.8% / max 36.2%; M6 median 0.7% / p90 6.6% / max 31.1%
- macro_tiles: M5 median 0.4% / p90 5.8% / max 16.7%; M6 median 0.5% / p90 4.1% / max 12.1%

The owner's observation holds: above M4 the tiles are close to empty. Median M5 and M6 signal use is under 1% of tracks, p90 is 6–7%, and area-weighted M6 is 1.7%.

## Highest-signal-layer histogram (all 428)

| top signal layer | M4 | M5 | M6 | M7 | M8 | M9 |
|---|---|---|---|---|---|---|
| blocks | 3 | 27 | 41 | 354 | 1 | 2 |

**Contract finding:** 357 of 428 closed blocks route signals on M7 or higher, which the current contract (tile signals ≤ M6) forbids. Most of them are short pieces of wire (p90 M7 use is 4%, area-weighted 1.1%), left by the flow's default max routing layer of M7. Three blocks reach M8/M9. These routes are not contract-clean whichever contract is chosen. The die top cannot use M7 over them, and they collide with the M7 parent straps.

## Top 10 tiles by M6 signal utilisation

| block (element) | kind | area mm² | M4 | M5 | M6 | M7 | M4/M5 util if capped at M5 |
|---|---|---|---|---|---|---|---|
| hfd_stn_r19 (hfd_stn_r19) | logic_tile | 0.0040 | 22% | 1% | 31% | 2% | 24% |
| hfd_stn_r34 (hfd_stn_r34) | logic_tile | 0.0030 | 14% | 1% | 31% | 4% | 22% |
| dsfd_l2r_vr_512x1__hq_SW (dsfd_l2r_vr_512x1__hq_SW) | logic_tile | 0.0042 | 22% | 21% | 22% | 24% | 41% |
| ot_qwen_stream4_cdc_pc_cdc_eco (ot_qwen_stream4_cdc_pc) | logic_tile | 0.0338 | 15% | 6% | 20% | 20% | 27% |
| dsfd_r2l_vr_512x1__hcol (dsfd_r2l_vr_512x1__hcol) | logic_tile | 0.0041 | 13% | 9% | 18% | 7% | 23% |
| dsfd_colt_mrg (dsfd_colt_mrg) | logic_tile | 0.0327 | 18% | 6% | 18% | 10% | 24% |
| dsfd_r2l_vr_512x1__hsel (dsfd_r2l_vr_512x1__hsel) | logic_tile | 0.0041 | 15% | 10% | 16% | 6% | 24% |
| dsfd_m2l_vr_68x10__hr_W0 (dsfd_m2l_vr_68x10__hr_W0) | logic_tile | 0.0225 | 14% | 2% | 15% | 5% | 17% |
| dsfd_l2r_vr_564x1__hx_E (dsfd_l2r_vr_564x1__hx_E) | logic_tile | 0.0050 | 15% | 11% | 14% | 14% | 26% |
| ot_hbm_index_global_order (ot_hbm_index_global_order) | logic_tile | 0.0172 | 12% | 7% | 14% | 13% | 21% |

None of the top 10 is a dense macro tile. All of them are small relay, station or pin-register logic tiles (0.003–0.034 mm²) with many pins packed into a short edge, and they use M6 for pin access and edge-to-edge spans. Their M5 is underused (0.7–21%). With all M4–M9 signal wire moved down to M4/M5, the worst of them, `dsfd_l2r_vr_512x1__hq_SW`, reaches 41% M4/M5 use, and the rest stay at or below 32%. No closed tile *genuinely* needs M6 for capacity; the need is pin access, which a pin plan on M4/M5 (longer edge, or pins on two faces) removes.

## Alternative contract: tiles ≤ M5 signals + PG on M5; die nets on M6/M7 over tiles; M8/M9 die power + global

Die-level signal track capacity over a tile, in tracks per mm of the preferred direction (= mm of track per mm²). Assumed die PG/strap share is 20% of a strap layer; the Qwen die-top GRT derate on M8/M9 was ~18%.

| | M6 | M7 | M8 | M9 | total |
|---|---|---|---|---|---|
| now (M7 = straps for tile M6 PG; die signals M8/M9) | 0 | 0 | 10000 | 10000 | 20000 |
| alt (M6 = straps for tile M5 PG, 80% free; M7 free) | 12500 | 15625 | 10000 | 10000 | 48125 |

Added die capacity over tiles: **+28125 tracks/mm² (2.41× today)**, made up of +12500 horizontal (M6) and +15625 vertical (M7). The cost to the tiles is 1.7% (M6) and 1.1% (M7) of their own tracks on an area-weighted basis.

**Re-route set under alt:** 398 of 428 closed blocks have signal wire on M6 or higher. Re-route difficulty is estimated by the projected M4+M5 use if all M4–M9 signal wire moves to M4/M5: {'easy(<30%)': 396, 'moderate(30-50%)': 2}. Under the *current* contract, 357 blocks must re-route anyway (M7+). The two most-loaded blocks are `dsfd_l2r_vr_512x1__hq_SW` (41%) and `hfd_mcast_r5` (32%). The full list is in the JSON (`alt_contract_reroute.blocks`).

## Recommendation

Move to ≤M5 for new routes now (ref_tile kit: `MAX_ROUTING_LAYER=M5`, PG stripes on M5, pins on M4/M5), and keep a per-tile ceiling of M6 as an exception the die lead grants. Candidates for that exception are pin-dense edge relays, where a pin replan is not wanted, and any SRAM/ROM tile whose macros block M1–M4 over most of its area; none of the closed set needs it for capacity today. Re-route closed tiles opportunistically, starting with the 357 that already break the current ≤M6 contract on M7 and those under the congested Qwen ROM and HBM die regions. Each re-route is almost certainly easy (projected M4/M5 ≤ 30% for 396 of 398). The die gains about 2.4× signal track capacity over tile footprints in the region where GRT overflows (M6–M9).

Caveats: utilisation is averaged over the whole tile footprint and does not resolve local hotspots near pins and macros. Clock wire is included in the area-weighted column only. The 20% PG share is an assumption. "Closed" means the newest archive job per block whose metrics record DRC 0 / setup ≥ 0 / hold ≥ 0; closed records on main that are not in the archive are not included.
