# VSW fresh pin-contract review

Picture: results/codex_s81_0822/vsw_template.png (personally viewed 2026-10-29).
Verdict: PASS-COND for one fresh PLACE; actual placed geometry before CTS/route.

The old native access centres are inside the outline and cannot serve as fresh edge pins. The new template keeps the same 224.64 um square, 321 N-face pins and 68 S-face pins, and the clock at (56.652,0.24) on M5. Every signal gets an explicit M5 edge rectangle and the nearest existing x track; no pin names, ordering, direction, logic or cycle changes. Max move is 1.7155 um, clock move zero, no duplicate/pitch sites. All 389 entries pass the actual modern planned_pin_geometry consumer without projection. Old routed view and old pin table are retained.

Wide input groups remain on N and outputs on S; the pin plot has no stacks and ample edge capacity. No core outline, halo, parent channel or PG reservation changes. This is a source pin plan, so actual logic placement, parent reach at changed pins, clock balance, PG and TT/FF timing are still measured in the new kit; there is no CTS/route or signed-view claim.

Actual parent reach consumer on all74 affected types: old0/new0 internal-station findings; exact original M5 VDD/VSS PG port blocks preserved, template obstruction ceiling M5 matches parent declaration.
