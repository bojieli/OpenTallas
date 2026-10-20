# S81 mu5 GRT overflow class table (S81-DIE10, 10-20)

Sources: ot-epyc7 /srv/opentallas-scratch/claude/s81-mu5/case_mu5k, case_mu5r (out/grt.odb, read-only); analysis die10_ana/{dump_guides.py,grt_class.py}. Signal layers M2-M7 only (`set_routing_layers -signal M2-M7`); macros block M2-M7, so all die signals route in the ~23% of the die not covered by macros; M8/M9 (2.08e9 track-gcells) carry 74 guides. post-GRT guides of each run grt.odb (OpenROAD read-only dump, 26.6M/28.3M guides) rasterised on the 9.6 um GRT gcell grid; capacity per gcell/layer = tracks (GRT track pitch) x (1 - layer adjustment) x (1 - macro OBS cover); M7 blocked over macro footprints like M6 (GRT-0053 M7 resources == M6). The guide model over-counts (pin/via guides), so every class number is also given CALIBRATED = model x (GRT layer overflow / model layer overflow).

## mu5k: GRT total 854,368 (max H 353 / V 357), PHY = REAL ot_hbm3e_phy_v41x_aw30_e8p5_k LEF (--macro-views), 01:26:22 GRT, 55.7 GB

Per layer (GRT): M2 31,574, M3 81,322, M4 332,457, M5 227,272, M6 155,182, M7 26,561

| region (nearest big block) | view | calibrated overflow | share | M2 | M3 | M4 | M5 | M6 | M7 | over block | open channel | over relays/landings |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| frame | standin | 416,186 | 48.7% | 25,176 | 63,272 | 176,030 | 113,927 | 28,367 | 9,414 | 4% | 83% | 13% |
| slice_col | standin | 138,272 | 16.2% | 1,988 | 5,689 | 42,962 | 43,122 | 36,811 | 7,700 | 13% | 51% | 36% |
| svc_rs | standin | 115,458 | 13.5% | 2,191 | 6,017 | 43,123 | 35,658 | 21,249 | 7,220 | 15% | 64% | 22% |
| CTRL | standin | 85,364 | 10.0% | 489 | 1,982 | 43,730 | 25,030 | 12,673 | 1,459 | 79% | 13% | 8% |
| PHY | closed | 70,241 | 8.2% | 459 | 805 | 16,853 | 397 | 51,727 | 0 | 100% | 0% | 0% |
| seq_host | standin | 11,419 | 1.3% | 559 | 1,556 | 3,876 | 3,983 | 1,333 | 113 | 1% | 80% | 20% |
| gunit | standin | 6,711 | 0.8% | 431 | 1,233 | 1,912 | 2,761 | 277 | 98 | 0% | 85% | 15% |
| bk_topk | standin | 3,831 | 0.4% | 251 | 684 | 1,482 | 1,262 | 105 | 46 | 2% | 85% | 13% |
| serdes_lk | standin | 6,882 | 0.8% | 30 | 85 | 2,488 | 1,131 | 2,639 | 510 | 18% | 22% | 60% |

Zones (calibrated): PHY_face_400um 165,206, ctrl_seam_200um_channel 13,489, rest_of_die 684,170. Model overflow by view status: channel 73%, over_closed_view 18%, over_standin 9%

Net classes of guides through overflowed gcells (guide count): net# 12,232,089, w_x 989,086, r_x 734,439, r_xrE 309,719, r_xrW 298,685, r_mu 236,693, w_xrE 187,605, r_hf 185,672, w_xrW 183,921, r_jw 145,946, a_phy 143,442, w_hrq 130,872

| hot 1 mm tile x,y (mm) | calibrated | worst layers | dominant regions | nets |
|---|---:|---|---|---|
| 17-18, 1-2 | 27,148 | M4 10,247, M6 8,757, M5 6,206 | channel, svc_rs, CTRL | net#, w_hrq, a_phy, r_hrq |
| 18-19, 1-2 | 26,199 | M6 9,813, M4 9,575, M5 5,439 | CTRL, channel, svc_rs | net#, w_hrq, a_phy, w_hrd |
| 15-16, 1-2 | 22,478 | M6 9,641, M4 8,764, M5 3,127 | CTRL, PHY, channel | net#, a_phy, w_hrq, w_hrd |
| 13-14, 1-2 | 21,726 | M4 9,217, M6 8,617, M5 2,896 | CTRL, channel, PHY | net#, a_phy, w_hrq, r_hrd |
| 14-15, 1-2 | 24,127 | M6 9,860, M4 9,853, M5 3,501 | CTRL, PHY, channel | net#, a_phy, w_hrq, w_hrd |
| 17-18, 10-11 | 11,125 | M5 4,444, M4 3,304, M6 1,754 | channel, frame, bk_topk | net#, w_x, r_jw, r_jd |
| 12-13, 1-2 | 22,847 | M4 9,818, M6 9,358, M5 2,854 | CTRL, PHY, channel | net#, a_phy, w_hrq, w_hrd |
| 16-17, 1-2 | 17,661 | M4 7,759, M6 5,385, M5 3,677 | CTRL, PHY, channel | net#, a_phy, w_hrq, w_hrd |

PHY north-face cut rows (vertical layers, demand/capacity along the 8.5 mm face; row k = k x 9.6 um above the PHY; blocked = fraction of the row under a macro, ctrl = under a CTRL):

| row | y um | M3 | M5 | M7 | blocked | ctrl |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1200 | 15.305 | 2.229 | 0.008 | 1.0 | 1.0 |
| 2 | 1210 | 13.245 | 1.83 | 0.008 | 1.0 | 1.0 |
| 3 | 1219 | 12.15 | 1.55 | 0.008 | 1.0 | 0.999 |
| 4 | 1229 | 12.424 | 1.488 | 0.008 | 1.0 | 0.999 |
| 5 | 1238 | 12.708 | 1.477 | 0.008 | 1.0 | 0.999 |
| 6 | 1248 | 13.12 | 1.471 | 0.008 | 1.0 | 1.0 |
| 7 | 1258 | 15.004 | 1.453 | 0.008 | 1.0 | 1.0 |
| 8 | 1267 | 16.912 | 1.422 | 0.008 | 1.0 | 1.0 |
| 9 | 1277 | 20.87 | 1.373 | 0.014 | 1.0 | 1.0 |
| 10 | 1286 | 27.668 | 1.3 | 0.021 | 1.0 | 1.0 |

## mu5r: GRT total 4,090,822 (max H 435 / V 624), PHY = stand-in rv_phy_hbm (pin-only), 4h43m GRT

Per layer (GRT): M2 1,038,688, M3 554,430, M4 1,242,834, M5 553,686, M6 502,034, M7 199,150

| region (nearest big block) | view | calibrated overflow | share | M2 | M3 | M4 | M5 | M6 | M7 | over block | open channel | over relays/landings |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| frame | standin | 1,727,431 | 42.2% | 635,554 | 380,274 | 425,546 | 210,280 | 42,244 | 33,533 | 4% | 83% | 13% |
| CTRL | standin | 796,925 | 19.5% | 101,772 | 40,895 | 289,369 | 113,211 | 186,140 | 65,538 | 73% | 18% | 9% |
| PHY | standin | 659,659 | 16.1% | 158,640 | 40,392 | 248,482 | 60,802 | 110,311 | 41,031 | 100% | 0% | 0% |
| svc_rs | standin | 453,779 | 11.1% | 60,459 | 37,290 | 151,933 | 72,976 | 102,269 | 28,851 | 19% | 60% | 21% |
| slice_col | standin | 349,894 | 8.6% | 50,187 | 34,194 | 103,897 | 79,553 | 54,603 | 27,461 | 13% | 51% | 36% |
| seq_host | standin | 42,579 | 1.0% | 14,114 | 9,351 | 9,384 | 7,349 | 1,979 | 402 | 1% | 80% | 20% |
| gunit | standin | 28,759 | 0.7% | 10,868 | 7,412 | 4,622 | 5,097 | 411 | 348 | 0% | 85% | 15% |
| bk_topk | standin | 16,681 | 0.4% | 6,336 | 4,112 | 3,585 | 2,329 | 157 | 162 | 2% | 85% | 13% |
| serdes_lk | standin | 15,105 | 0.4% | 757 | 508 | 6,014 | 2,087 | 3,918 | 1,820 | 18% | 22% | 60% |

Zones (calibrated): PHY_face_400um 1,527,004, ctrl_seam_200um_channel 199,497, rest_of_die 2,517,507. Model overflow by view status: channel 59%, over_closed_view 13%, over_standin 28%

Net classes of guides through overflowed gcells (guide count): net# 13,319,271, w_x 989,448, r_x 734,439, a_phy 342,608, r_xrE 309,719, r_xrW 298,682, r_mu 239,477, w_xrE 187,535, r_hf 185,672, w_xrW 183,920, w_hrq 162,622, r_jw 145,953

| hot 1 mm tile x,y (mm) | calibrated | worst layers | dominant regions | nets |
|---|---:|---|---|---|
| 15-16, 1-2 | 329,244 | M4 121,471, M6 74,615, M5 52,788 | CTRL, PHY, channel | net#, a_phy, w_hrq, w_hrd |
| 16-17, 1-2 | 286,420 | M4 118,033, M6 60,284, M5 57,808 | PHY, CTRL, svc_rs | net#, a_phy, w_hrq, w_hrd |
| 17-18, 1-2 | 180,863 | M4 71,762, M6 47,546, M2 22,941 | CTRL, channel, svc_rs | net#, a_phy, w_hrq, r_hrd |
| 14-15, 1-2 | 178,902 | M4 66,567, M6 56,852, M2 29,793 | CTRL, PHY, channel | net#, a_phy, w_hrq, w_hrd |
| 13-14, 1-2 | 135,198 | M4 49,604, M6 34,370, M2 27,779 | CTRL, PHY, channel | net#, a_phy, w_hrq, r_hrd |
| 18-19, 1-2 | 137,803 | M4 51,500, M6 33,426, M2 20,801 | CTRL, channel, PHY | net#, w_hrq, a_phy, w_hrd |
| 15-16, 0-1 | 82,826 | M2 31,646, M4 28,861, M3 10,929 | PHY | a_phy, net#, rs, rst_sync |
| 12-13, 1-2 | 103,891 | M4 38,866, M6 22,755, M2 20,913 | CTRL, channel, PHY | net#, a_phy, w_hrq, w_hrd |

PHY north-face cut rows (vertical layers, demand/capacity along the 8.5 mm face; row k = k x 9.6 um above the PHY; blocked = fraction of the row under a macro, ctrl = under a CTRL):

| row | y um | M3 | M5 | M7 | blocked | ctrl |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1200 | 5.802 | 1.494 | 1.231 | 1.0 | 1.0 |
| 2 | 1210 | 5.22 | 1.252 | 0.978 | 1.0 | 1.0 |
| 3 | 1219 | 6.728 | 1.24 | 0.898 | 1.0 | 0.999 |
| 4 | 1229 | 7.955 | 1.246 | 0.843 | 1.0 | 0.999 |
| 5 | 1238 | 8.691 | 1.232 | 0.788 | 1.0 | 0.999 |
| 6 | 1248 | 9.214 | 1.248 | 0.746 | 1.0 | 1.0 |
| 7 | 1258 | 9.915 | 1.235 | 0.705 | 1.0 | 1.0 |
| 8 | 1267 | 10.248 | 1.214 | 0.677 | 1.0 | 1.0 |
| 9 | 1277 | 10.847 | 1.25 | 0.66 | 1.0 | 1.0 |
| 10 | 1286 | 12.749 | 1.303 | 0.623 | 1.0 | 1.0 |

## PHY face cut vs track (inputs: Codex codex/s81-mu6-realctrl-1020@2c1992f60)

- Real PHY face: 1,244 bits per controller pair over a 531.25 um pair window (16 pairs, 19,904 bits). Stand-in CTRL E-face funnel: max 631 um, 9,952 bits > 405 um.
- n32s CTRL registered south-face pin order: per-pair horizontal cut 1,244 -> 476 wires; PHY escape max 149 um, 0 bits > 405.
- M6 escape band 86.4 um: native raw 1,350 / 55% = 742 count-only PASS (alternating 675/371 FAIL); 129.6 um envelope 1,012/556 count-only; north guard 250.96; full-U upper leg 408.4 > 405 (FAIL by 3.4 um).
- M7 two-leg 2,488 per pair vs native 4,565 (count-only), alternating 2,282 FAIL. Actual M3/M5 pin via 4/2 cuts, native PG + track assignment and electrical proof still owed.
- Measured here (mu5k, real PHY): the ring rows directly north of the PHY are mostly under CTRL stand-ins / relays (see blocked/ctrl columns): the PHY bits must pass through gaps in the CTRL row -> this is the CTRL seam, not a lack of tracks over the 8.5 mm face (M7 at row 1 is almost unused).

## Structural fix per class (no reruns)

- **PHY**: PHY ESCAPE BAND: registered n32s CTRL south-face pin order (max 149 um, 0 > 405) + 86.4 um M6/M7 escape band over the PHY body (Codex 7991d0177: M6 band count-only PASS 742 at 55%); full-U upper leg 408.4 > 405 needs one landed hop or a 4 um shorter U
- **CTRL**: RE-PLACE: real n32s CTRL body 388.8x324 centred in the 1062.5 um pair pitch, array +86.4 um north (mu6 plan) -> opens a CTRL<->PHY seam channel; per-pair cut 1244 -> 476 wires (n32s pinplan)
- **svc_rs**: WIDER CHANNELS + PIN REBALANCE: svc_rs face 6.7-8.2 pins/um > 6/um -> two-layer (M4+M6) face pins / face rebalance in the svc_rs kit (S81.BIND.SM.1); re-derive Codex --placefix (+70 um) jointly with the +86.4 CTRL shift (74 relay overlaps)
- **frame**: MORE LANDED LANES: frame-row lane channels carry the 276-bit xring/jw lanes on M4/M5 only; split each long lane into landed regions with M6/M7 forwarded half-cycle hops and spread the lane bundle over two channel rows (no single 9.6 um gcell column >55% tracks)
- **slice_col**: WIDER CHANNELS: slice-column side channels -> widen by one 43.2 um lattice pitch where the column pair carries >2 lanes, or move lane relays onto the column face band
- **serdes_lk**: none needed (overflow negligible)
- **gunit**: none needed (negligible)
- **seq_host**: none needed (small); keep the seqhost lane on its landed relay chain
- **bk_topk**: TOPK slot growth 324x540 -> 518.4x648 (06:29 decision) is area, not congestion; fold into mu7 repack
- **relay lanes (relay_h / relay_1b / landings in channels)**: overflow sits over or next to the 3,113 dvrlyh + 5,137 rly_1 stations in 1-gcell-wide channels -> LANE CHANNEL WIDTH = ceil(bits x 1.82 / tracks per um) (55% rule) per channel, stations staggered (no two 276-bit stations in the same gcell column), and long lanes moved to M6/M7 between landed regions.
- **all classes**: signal layers capped at M7 while macros block M2-M7 and M8/M9 stay empty: open M8 (and M9) as a die-level signal layer for the long landed lanes (repeater/hop cells already in channels); this is the largest track supply left (2.08e9 track-gcells vs 0.55e9 M6+M7).


## mu7 die plan (structural, folds the class fixes + owed items)

1. CTRL/PHY seam (mu5 hot tiles x 12-19 mm, y 1-2 mm; PHY north rows are 100% under the 16 CTRL stand-ins, 531 um each = the whole 8.5 mm face): keep mu6's real n32s CTRL 388.8x324 centred per pair (142 um seam channels between CTRLs), array +86.4 um north, registered south-face pin order (1,244 -> 476 wires/pair). Add the 86.4 um M6/M7 PHY escape band and fix the full-U upper leg (408.4 > 405) with one landed hop. Measure on mu6n first (live chain) before any further CTRL move.
2. Frame-row lane channels (largest class, 49% mu5k / 42% mu5r; 83% in open channels; nets xring w_x/r_x/xrE/xrW, r_mu, r_hf, r_jw on M4/M5): size each lane channel from bits (55% of M4-M7 tracks), stagger 276-bit stations, landed regions with M6/M7 forwarded half-cycle hops for long lanes, and open M8 as a signal layer for the landed long lanes (M8/M9 hold 2.08e9 unused track-gcells).
3. svc_rs (13.5% / 11.1%): owed face density 6.7 (p4l) - 8.2 (idx3) pins/um > 6/um + 74 lane-band relay overlaps -> two-layer face pins / face rebalance in the svc_rs kit (S81.BIND.SM.1) and Codex --placefix (+70 um, codex/s81-dieplace-1019 6e3559855) re-derived jointly with the +86.4 CTRL shift.
4. Slice columns (16.2% / 8.6%): widen the side channel by one 43.2 pitch where a column pair carries > 2 lanes, relays onto the column face band.
5. idx3 readers (L20RD): mu7 reserves the idx3 plan (fae604329: 8 paired 2-region readers 1036.8 x 1036.8, ROM 1130 -> 1070, cut 0.566) but binds it only when dsdv_idx_rg2 reader RTL + 2-region bench PASS (Claude L20RD2 terminal exit 1 07:47, gather P3 FAIL 921/1015) -- otherwise idxrd 0 (1,084 undriven bits = reader outputs otherwise).
6. TOPK quarter slot 324x540 -> 518.4x648 (06:29 lead decision, hard-child hk1/hk1l): the rigid 43.2-lattice shift needs 29.36 mm die height > 25 mm (Codex c4045d687 preserve122 model, REFUSED) -> coherent repack of the TOPK/SVC rows (no rigid shift), priced with the svc_rs slot change in the same plan.
7. Clock: all 14 relay families + CTRL now carry NATIVE forwarded-clock views (claude/s81-die10-1020 12c132d60); the die STA consumes them through the native guard (no SELF relabel).
