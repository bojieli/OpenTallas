# West LEP b1e41 detailed-placement review

**FIX-FIRST overall.** I opened the native detailed-placement layout and density images. The macro aisles remain visible between the two hard-pair blocks and ten SRAMs. Density is localized in the upper-right landing strip, at the west face, and beside the SRAM aisle. The independent automated image review is ISSUES for the same checkpoint. It flags right-perimeter clearance, central pin escape, and local clock and power access for separate physical assessment.

| Exact placed metric | d51 | b1e41 |
| --- | ---: | ---: |
| Peak local density | 0.667 | 0.662 |
| Density bins above 0.700 | 0 | 0 |
| Peak estimated channel use | 0.386 | 0.323 |
| Maximum pin-track use | 0.262 | 0.262 |
| Raw pre-tap core-clock sinks | 27,749 | 27,737 |
| Raw core-clock pin-to-centroid distance | 908.961 µm | 909.899 µm |
| Peak fanout bounding-box spread | 1,040.9 µm | 980.8 µm |

Detailed placement reports zero row-alignment, overlap, edge-spacing, and padding violations. The actual M7 boundary clock `fclk_in_coll_i1` is at (2.144, 742.816) µm, matching the parent contract. The native fanout spread leaders are the `coll_i1` strap and its copy. The picture's clock measure uses the unsplit clock fanout. The five CK5 moves are part of pre-CTS after the stock tap assignment and remain pending.

The post-DPL `rrl265` guard applied on this exact placement. It split the 383.778 µm single-load branch into 138.402, 123.606, and 121.770 µm legs at the two reviewed seats. Stock DPL reports its timing before that insertion and recorded 842.86 ps at the old B16 input. A read-only TT query loaded the final placed database with the same stock library files, SDC, and placement RC. The larger transition at each of the three buffer inputs was 129.670, 92.894, and 98.623 ps against a 320 ps limit. The two same-age launch paths had +402.629 and +403.757 ps estimated setup slack. This resolves the scoped placement estimate, while fresh CTS and routed timing remain gated.

## Exact evidence

- E7 kit `/srv/opentallas-scratch2/claude/head-west/west_w10_combined_271_265_ck5_1126/kit_work_b1e41/gen/hd_lep0N_w`. Place-only unit `oth-ubuntu-3211891-1795701916` exited 0.
- Checkpoint `run/results/asap7/dp_hd_lep0N_w/base/3_place.odb`, SHA-256 `ff95a3fc0407b47c8b15860babbed7552feed3d9f8705efd1dac1928552e7b11`.
- Opened `run/layout_review/place/layout.png` SHA-256 `22017a859e328af528575afbe200b507e3922d83fd00ac1055aa00a9429b6f4d` and `density.png` SHA-256 `9e30eb00695cba9528b227897a17d53a767cba566dced980f4d90163f321e951`.
- Independent visual-review request `fcf649e72bec6b6287671c67b56bb59514c4211cf6e1afeb130309d289d95ed8`. Its ISSUES receipt remains authoritative for the automated hold.
- Exact read-only TT probe unit `oth-ubuntu-3896772-1795703234` exited 0. Report is in the run's parent packet at `rrl265_exact_placed_tt/check.log`.
