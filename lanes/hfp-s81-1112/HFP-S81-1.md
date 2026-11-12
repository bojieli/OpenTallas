# HFP-S81-1: S81 hand top-level floorplan (COORD, 11-12)

Owner rulings: "go at the human level"; "you need to design the manual floorplan right now"; re-floor over signed types allowed (batch re-sign).
Data: ready12f plan (398 partitions), S81-DIEREVIEW-1 family table and data flow. Drawing: hfp_s81_1.png (left before, right proposed).

## Decisions
| # | Decision | Why (data) |
|---|---|---|
| D1 | Split the die into 3 regions: FRAME W wing, CENTRE, FRAME E wing. Each region has its own row pitch. | The rigid lattice let svc's 2.85/2.75-mm rows stretch the wing rows (white gaps, +0.69 mm). Frame banks are the only truly regular family (216 tiles, 47-58% core fill). |
| D2 | Wings: 6 col x 18 row frame banks with col_h9/h10 types UNCHANGED, r0->r1->r2 chains kept vertical, 1227-um pitch, SerDes double tiles on the top/bottom wing edges (12 of 14). | The chains carry 70k b and 15k b per hop inside the wing columns, and these already close. |
| D3 | Remove station columns 6 and 15 (38 full tiles, 2.1% core fill, 0.07% cell fill). Each becomes a 300-um RELAY CHANNEL with the station flops as strips at the SAME register stage count. | Each frame<->centre crossing gets 1143 um shorter, the main lever on the 780 TT landed hops over 416.5 ps. Bits crossing each channel are ~16-32k over ~22 mm, about 1-1.5 b/um, which a 300-um channel carries easily on M8/M9 ft. |
| D4 | Fold the other 8 interior station tiles (top row x6, row 14291 x3, row 6929 x5, overlapping) into two 150-um horizontal relay channels between the leaf bands. | Same reason as D3. Leaves re-pack into the freed tiles. |
| D5 | CENTRE = 8 tile columns (11.54 mm). Stack bottom to top: PHY (edge) + 1 SerDes double; SVC lo rs row (2.85 mm, next to PHY); SVC hi + pvso row (2.75 mm); relay ch; LEAF band A (2 rows); SLICE C row A; LP + misc row (4 LP beside their C partners, iqf, eng, seqhost); LEAF 2 rows; relay ch; LEAF band B (2 rows); SLICE C row B (c1x/kv512); LEAF 3 rows; LEAF row; edge row (1 SerDes double, gunit, bk_sel, 1 leaf). | Leaf<->C-slice is the heaviest centre traffic (44k + 36k b, 6-8 cycles), so each slice row sits mid-band: every leaf is at most 2-3 tiles from its slice row. svc_lo<->phy is 9.5k b. |
| D6 | 80 leaf slots (75 leaf + 5 kv_leaf) out of 81. Core re-pack inside each leaf follows S81-LEAF-FLOOR-1 (vp cluster within 405 um of its driver and ports). | The die review found leaf cores at 34% fill with a bbox of 66% of the tile: the leaf fix is the re-pack, not the slot size. |
| D7 | Clock spine root moves to the new centre. The wings and the centre get separate regional trees off the spine. | The regions now have different row pitches. |
| D8 | Die: 29.66 x 24.74 mm = 734 mm2 (was 812.7, -9.7%). | Width: 2 x 8657 wing + 2 x 300 ch + 11543 centre + margins. Height: wing 18 rows + 2 SerDes edge rows. |

## Open checks (must pass before compose; owner: DIE-S81-87 + S81-DIEREVIEW-1)
1. Landed-hop estimate. Re-measure the 780 TT landed hops on HFP-S81-1 positions. Target: most frame<->centre hops under 416.5 ps. If the remaining hops fall in one family, give it +1 register in the channel.
2. Channel vertical capacity. Some station columns carry vertical x/ft lanes. Sum the vertical bits per column against 300 um of M8/M9 tracks, and widen to 450 um if needed (the die still shrinks).
3. SerDes content is UNMEASURED (cells 0 in cells_est). Confirm that the PMA macro fits a 2886 x 1227 tile and that the lk lanes keep their W/E side. The 2 moved SerDes doubles go to the centre edge rows.
4. svc: 13 internal hops over 405 stay a type-level fix (svc lane); the region placement is unchanged.
5. Re-sign batch: every centre type moves. Wing types are unchanged except for pins on the face toward the channel. List them in the KEEP/RESIGN table.
6. REACH-FIX-1 runs at compose (taps <=800 sinks, fclk repeaters, hops, reset).

## v2 (COORD, 11-12 05:3x): answers to GEOM-VIS-3's 4 blocking CHANGES. Drawing: hfp_s81_1v2.png
1. **Leaf-to-slice distance.** The centre now has THREE slice rows (S1 LEP C+LP pairs; S2 c1x/iq/kv512; S3 c3x/c1x + iqf/eng/seqhost) between 10 leaf rows in a 2-S1-3-S2-3-S3-2 pattern. Every leaf is at most 2 rows (2.45 mm, about 6 hops at 405 um) from a slice row, which fits the 6-8 cycle leaf<->C budget. Total centre height is unchanged.
2. **Channel width.** It follows a formula, not a fixed 300 um: width_um = max(300, 1.25 x Vbits / 12.7), with 12.7 b/um being M8+M9 at ~1.9k bits per 300 um per layer. Vbits = the vertical lane bits per old station column (6 and 15), summed by S81-DIEREVIEW-1 from the ready12f lanes. The die still shrinks while Vbits < 14.6k per column. Above that, the excess vertical lanes move into the wings' own vertical streets, so the channel never widens back to a full tile.
3. **Row heights.** Every leaf and slice row is one 1226.88 tile row. The only other heights are the two svc rows (2851.2 / 2747.5) and the channels (150).
4. **phy_hbm.** It stays at its OLD die x (11.66 mm from the west edge, bottom edge), so the HBM-side bump and PHY alignment is unchanged. SerDes and SD fill the rest of the bottom centre row.
