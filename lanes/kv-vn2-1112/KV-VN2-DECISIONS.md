# KV vN2 hand floorplan, draft 1 (DIE-KV-98, 2026-11-12)

Base: vN package, plan_sha256 77533c398d4dfd61170f0e8029d6a2c5dbb11ba71a7910cadaf7c1e880ae9b5d (branch claude/kv-vn-event-1112@52a724781a52).
Figures: `kv_vn2_dataflow.png` (bits between column classes), `kv_vn2_map.png` (die to scale, 11,180 x 27,043 um, each cell = type and worst tap sink count, colour: green <=1,500, yellow <=2,250, orange <=3,750, red above, grey hard/not evaluated; axis in mm).
Data: epyc4:/srv/opentallas-scratch2/claude/dkv98/flow_vN/{parts,flows,taps}.json, render_vN/types.json.

## Structure
9 columns x 16 rows, mirrored: phy | pc | hg | hgi | pv | hgi | hg | pc | phy. Hub band (hub_Wo, Wi, C, Ei, Eo + 4 hroot) between the south and north arrays; io/sys row on top. 598,087 bits cross partitions; 528,723 (88%) are inside the five array classes (pv-pv 86,444; hg-hgi 85,728; hg-hg 68,068; pc-hg 67,776; pc-pc 58,744; pc-phy 41,984; phy-pc 36,992; hgi-hgi 41,755; hgi-pv 35,338). Every hub flow is under 4.3k bits. The 103.68 um strip east of the rows (2.70 mm2) is the SD-GROW growth, unclaimed (decap/fill).

## Channels (from the G0 cut lines, plan track capacity)
| cut | bits | track ratio | note |
|---|---|---|---|
| between columns, 8 cuts | 26,941 to 50,766 | 0.046 to 0.086 | busiest hg / hgi at x = 3,179 um |
| between rows, 18 cuts | 6,009 to 23,383 | 0.025 to 0.096 | south 14.0k to 17.4k per boundary, north 20.0k to 23.4k (+40%); busiest y = 18,403 |
| worst partition segment | 3,623 | 0.66 | hgi_EN_0 y = 25,500, limit 0.6 (vF 0.96) |
| worst face track use | | 0.567 | pv_N_5, pv_N_4, pv_S_4, pv_S_5 on M7 |
| worst ft budget | 7,217 H | 0.522 | hub_Ei, 13,822 reserved |
No new die channel is needed on these numbers.

## Decisions (COORD rulings 11-12 applied)
| item | numbers | decision | status |
|---|---|---|---|
| column order, hub band, io/sys row | 88% of bits inside the array classes | keep | decided |
| clock taps | cap is 1,200 sinks per tap (COORD 05:19). The plan has 5,674 grid taps and needs 3,130 at 1,200 (2,531 at 1,500); 46 of 54 types have a worst tap over 1,200, 30 over 1,500 (pv_v6n 4,786 / 161 taps; hgi_v8 6,046 / 16; pc_v1 2,811 / 12; hg_v1p6 2,256 / 16). Only hgi_v8 is short of taps: 16 against 32 needed at 1,200 | density-weighted re-site is a reach class: REACH-FIX-1's tool at compose, no hand-placed taps. hgi_v8 16 -> 39 taps is the input (39 meets 1,000) | COORD rulings 4 and 05:19 |
| station cells on pv macros | 70 G0 errors, all in 12 pv types (v6, v6n, v12 10 each; v7 6; v2, v2n, v3, v3n, v5, v5n 5 each; v4, v4n 2 each) | ft_nudge.py --no-snap class fix (S81 t65 fix, 43023cc3ca). Trial: 70 slots re-sited, max bit move 6.48 um, no slide, RC 0 | G0 on the nudged plan running (epyc4 g0_nudge) |
| dead forwarded-clock census | 31 census errors = 1,024 bits over 32 phy-pc pairs, by design | exemption line declared in the plan, no code change | to write |
| hroot aspect | 4 x 1,901 x 838 um, aspect 2.27 | stays stacked under an ASPECT EXCEPTION; the hub band stays intact. Not re-shaped (COORD reversed the re-shape ruling after GEOM-VIS-3's review, 05:19) | decided |
| sys_c aspect | 2,160 x 1,037, aspect 2.08 | aspect exception (strip height fixed by the io/sys row), unless COORD says re-shape | proposal |
| stations inside PHY cores | 21 on io_phy_WS, 14 on io_phy_WN, 5 on sys_c keepouts | move lane stations to the pc side of the phy / pc cut | to build |
| hgi west-face pin pockets | LAND-RING-2 baseline KV pilots: congestion in the W-face pin pockets (kv3_hgi_v1 ISSUES) | the pin-pocket fix applies to every hgi type in the event (11 hgi types, 32 instances) | COORD 05:19; fix design to do |
| hg start-skew | 25 of 147 tree ports fail at TT; worst L1068_0 in hg_WS_1 67.3-99.2 ps vs 78.1 | rides with the tap re-site (REACH-FIX-1) and sync_dist | rows from DIE-PROTO-1 |
| hgi_EN_0 cut y = 25,500 | 3,623 bits on 5,468 tracks = 0.66 > 0.6 | move about 350 bits (to 3,281) to the top io row, no M8 grant | COORD ruling 2 |
| SerDes bump rects | 2 pg_domain errors (sys_SW, sys_SE) | re-derive the domain rect from the grown sys_SD_v1 outline | to build |
| near-duplicate types | 21 types in 10 groups, saves 11 | merge each group into one type with orientation; signed types may move | COORD ruling 3 |
| hops over 405 um | 0 (worst 401.8 um) | none; watch the margin | checked |
| hub_C cells | 693,699 vs 517k run limit | hard core + opt-in collector reduction in flight (KV-HUBC-CORE-1) | in flight |

## Not in this draft (due in the final, 11-13 12:00)
Per-slot fill from the last kit gen cell areas, the clock trunk drawing, and the per-region geometry. The tap counts are plan inventory (a lower bound); the 29k-sink tap needs a placed netlist (plan: pv_v4n worst 1,431 on 199 taps).
