# East HEAD 40e5 form 7988 detailed-placement review

**BAD. Keep CTS and route held.** I opened the stock layout and density images for the final E7 placement. The large north and south hard blocks retain side corridors, but the SRAM bank rows in the central band concentrate routing demand and standard cells in the same area.

The final `3_place.odb` and its stock-rendered `3_5_place_dp.odb` are byte-identical, SHA-256 `f2437d9675c1b9a7c2f4e0862e7cf42a56e0a8bee1297536cea61495935a9d92`. Native detailed placement passed. The producer skipped pre-placement equivalence checking in R-MINIMAL mode (`LEC_PREPLACE_DROPPED R-MINIMAL`). Stock DPL reported zero wrong-region, row, site, overlap, edge-spacing and padding violations.

The exact pre-DPL region census found zero initial overhangs in all 14 RX fences and the additional local write-select fence. The placement hook seated all 6,437 LEPK ring flops FIRM next to their bit pins on the east edge, with zero fallback to the band cursor, and applied all five writer guards. The East owner separately checked the final START and guard sites. All 281 START segments came in below 150 µm, worst 149.687 µm, and all five guards remained FIRM. The prior 12 opposite-facing CA pins are now zero among 6,712 inspected pins. Peak face pin demand is 0.262.

| Bank seam | Centre (µm) | Gap (µm) | Stock demand/capacity |
| --- | --- | ---: | ---: |
| TX3 B1–B2 | (527.016, 666.912) | 14.040 | 1.222 |
| RX0 B0–B1 | (649.416, 554.736) | 21.576 | 1.111 |
| RX2 B1–B2 | (341.316, 677.856) | 3.456 | 1.056 |
| RX1 B2–B3 | (335.136, 632.496) | 7.320 | 1.006 |

The strongest excess is the horizontal TX3 seam, with an estimated 834.1 nets for 682.5 tracks. The density view shows a group of compact hotspots near the central SRAM banks. The worst stock 10 µm bin is 99.6% at (679.3, 719.3) µm. The 825.9 µm fanout mark is a reset sink bounding-box measure. The native floorplan PG check found zero pin-spacing hits and zero blocking rail findings across 12,396 rows. The stock DPL channel check uses flight bounding boxes and excludes guide and PG blockage adjustments. Signal escape through the failed seams and the local ring-to-PG corridor remain open.

Remediate the four channel excesses and the localized density without undoing the verified fences, ring placement or PG structure. Repeat exact source and physical visual review after changes. The independent BAD vote is recorded against central request `3cefe37fd7b1c1e4b827545d8878b2c5965ada022b1214776acbbc98c0d3bd08`. The automated ISSUES assessment is preserved alongside it.

Exact kit is `epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w10_1125/private/HEAD-EAST-R2/hd_lep0N_1126050327_exact_sidecar/gen/hd_lep0N`, with `run/layout_review/place/{layout.png,density.png,smells.json}`. The pre-DPL fence witness is `epyc7:/srv/opentallas-scratch2/claude/head-east-r2/east_predpl_profile.otrun.log`. No new CAD ran during this review.

## Exact VDD connectivity follow-up

The independent full connectivity check rejected VDD with one `PSM-0038` shape and `PSM-0069`. The reported M5 box is [723.636, 1371.330]–[723.756, 1371.600] µm. A narrow read-only exact ODB extract identified it as VDD SWire 2, SBox 2376586, a routed STRIPE. The full component is one 0.120 × 0.270 µm metal piece. It touches no same-net M5 metal, M5-access via, PG BPin or placed instance. The adjacent VSS SWire 1/SBox 509773 is the corresponding physically isolated M5 piece at [723.444, 1371.330]–[723.564, 1371.600] µm. That VSS observation was first identified from geometry, then confirmed by the original full connectivity check.

The generated `reserved_pg_cut.tcl` entries at y1369.980–1371.330 and y1371.600–1372.950 clip the stripes on both sides. Each continuing same-net M5 stripe is 1.350 µm away in y and has its own M5 vias. Intact M1/M2 rails and their M1–M2 vias cross the same xy coordinates on their own layers. The earlier `pg_rail_check` established row rail and stack structure, and `pg_pin_check` measured spacing. A floating cut remainder can pass both of those checks. The West W10 exact retention has the same cut-generator mechanism for its M5 and M6 fragments, at distinct coordinates.

The smallest proposed correction is one additional M5-only window [723.444, 1371.330, 723.756, 1371.600] supplied solely to the existing reserved-PG cut generator for the exact East source. Keep the placement and route reservations and other layers as they are. Replaying the existing interval split in integer DBU removes exactly the two isolated rectangles, leaves all eight other extracted M5 stripe rectangles intact, and touches no M5 via, BPin or load. Only materialize it on a fresh combined source after rechecking the shape and load guards. The official connectivity receipt is still required on the resulting checkpoint.

PSM evidence is in `epyc7:/srv/opentallas-scratch2/claude/head-east-r2/codex-route-capacity/actual_40e5/rail_only.otrun.log`. The exact inspection used a read-only E7 ODB window with no placement, route, or duplicate power solve. The BAD visual verdict and physical hold stay in effect.

The original VSS connectivity check subsequently finished. It confirmed the VSS M5 fragment and reported two additional isolated VSS M6 shapes. Both were routed STRIPE boxes on SWire 1.

| SBox | Exact M6 rectangle (µm) | Reserved-cut lines |
| --- | --- | --- |
| 488344 | [488.970, 559.104]–[490.266, 559.392] | 244–245 |
| 469889 | [497.610, 585.024]–[498.204, 585.312] | 254–255 |

A narrow read of the exact ODB found no M6-contact via, PG BPin or placed instance touching either fragment. The first crosses a VSS M5 stripe in projection without a connecting via. Both cross intact M1/M2 followpin rails on other layers. The stock split replay removes just these two boxes when their exact rectangles are supplied as M6-only windows. All six other M6 stripes in the two inspected windows, including both continuations on each affected track, keep their exact bounds. The M5 projection and all existing vias, pins and loads remain intact. Add the two M6 windows to the same existing PG-only cut input as the M5 pair, then require clean native connectivity on the resulting fresh checkpoint. The original PSM now confirms all four identified pieces. No duplicate full solve was run.
