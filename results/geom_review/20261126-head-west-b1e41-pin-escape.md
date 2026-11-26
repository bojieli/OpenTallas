# West HEAD b1e41 first-via geometry

I screened the retained native pin and track rectangles, clock reservations, PG straps and obstruction geometries from exact final placement `ff95a3fc0407`. The screen uses the production ASAP7 default via footprints and short orthogonal wire stubs. Unclassified existing via envelopes are treated as local blockers. These are independent local geometry witnesses.

| Scope | First-via geometry witness in µm |
| --- | --- |
| `fclk_in_coll_i0` | Direct VIA67 at (746.720, 1405.344) and VIA78 at (746.720, 1405.320). Both have space for the first horizontal segment toward the west. |
| `clk_t61` | Direct VIA78 at (672.864, 1376.840). |
| `clk_t62` | Direct VIA78 at (737.632, 1376.840). |
| `clk_t63` | Direct VIA78 at (811.104, 1379.000). |
| Left lower central SRAM `rd_out[0]` | Outward M4 segment and VIA45 at (260.808, 524.568), then an M5 stub. |
| Right lower central SRAM `rd_out[0]` | Outward M4 segment and VIA45 at (474.648, 524.568), then an M5 stub. |

The M6 reservations cover the complete direct downward via launch region for all three interior clock taps. These three pins can rise directly to M8 in the reserved-track gaps or extend on their M7 pin track outside the M6 reservations before turning down. The top boundary FCLK has turns on both adjacent layers. The central SRAM screen finds at least one outward VIA45 and M5 stub for each of the 810 M4 terminals on the two bottom banks, 203 on the west and 202 on the east of each bank. The screen charges metal enclosure, same-layer clearance and signal wire minimum area. These per-pin options may compete for tracks in a routed design.

The 4.320 µm region between each pair's east edge and the core boundary has no east-face boundary terminal opposite either hard pair. Four representative edge terminals at M4 and M6 were screened in the middle and upper openings. The collector samples `o_coll_i0_p[0]` and `o_coll_i0_p[101]` and the H2R samples `i_h2r1_p[0]` and `i_h2r1_p[101]` each have a first turn on a native track. The route along the side of the hard pair still needs a continuous guide and routed clock evidence.

For the next admitted checkpoint, keep the existing visual and CTS hold until the other findings are resolved. The remaining physical evidence is router pin-access output on the exact checkpoint, the first routed clock path through the M6/M7/M8 entry pockets, and continuity through whichever parts of the right corridor the route actually uses. No router, CAD run, or verdict override was performed for this screen.

Native source is the E7 run `/srv/opentallas-scratch2/claude/head-west/west_w10_combined_271_265_ck5_1126/codex-independent-review-1126`, with `escape.tsv`, `west_pin_links.tsv`, and `native_escape_summary.json`.
