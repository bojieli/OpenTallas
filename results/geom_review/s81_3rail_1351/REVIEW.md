# S81 three-rail RCX coupon geometry review

CODEX personally viewed review.png before native extraction (2026-10-27 14:16 PDT). PASS-COND for extraction only.

The literal materialized p128_r2 patch retains two adjacent nominal clusters in each direction (six actual rails per layer), 60 segments and 36 M8/M9 crossing via arrays. Clock strips have widths 1.60/1.68/1.76 um; actual encodable DEF uses per-path TAPERRULEs. PG stripes are 0.48 um on 8.64 um pitch with offset 4.32 um and alternating VDD/VSS, preserving global phase after translation. Minimum same-layer clock-to-PG gap in this patch is 1.16 um, above the specified 1 um. The close view shows regular three-rail crossings and contained via-array footprints without PG overlap. No standard cells, macros or signal routes are claimed.

This is a cropped local electrical component, not the full mesh. No die P&R, clock STA, freeze or physical closure claim follows. The parent plan remains BLOCKED. All source coordinates, widths, via rows/columns/pads and source-input hash are in geometry.json. Existing 1.28 um rules fail the explicit actual-width guard and are not extrapolated. New 1.60/1.68/1.76 um field rules and native extraction are required. Graph connectivity and actual SPEF results, including the PG-ground/coupling model, remain to be collected.
