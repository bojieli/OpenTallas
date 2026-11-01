# S81 landing-band class: corrected placement model

LOOK PASS for prototype placement on all11 affected types; no routed/timing qualification is asserted. The contact sheet shows every type; details cover svc_hi rs t1/t6, leaf t8 and svc_lo rs t7.

The previous17 new multi-rectangle bands intersected existing fixed reset/collector4.32um boxes on every band (4–40 intersections per band). `fill_failed_bands` consulted the legacy resize opt-in, which is empty in S81. New absent-band allocation now honors the actual stored/sidecar reset trees and other fixed landing-control groups without moving them. Existing unrelated bands/legacy compose are unchanged.

The exact batch fits all17 bands in157 rectangles across11 types, maximum18 rectangles per band. Maximum corner-to-input hop402.807um remains below the original402.84um allocation bound. Original padded area reserves, widths, ring widths, clock roles and ring placement mode are unchanged. All new rectangles remain macro/FT/other-band free and avoid the fixed control boxes. All target instances are disjoint from PHY PG domains; the solver asserts that before using independent complete type geometry.

The logical plan and sidecar, after excluding only physical band data/copies, compare equal. No core, clock/reset topology, input/output bus, RTL stage or cycle changes. Therefore the existing event2 strict bind and clock result apply; no fullbind rerun is needed for this band-only replacement. The sidecar receives matching physical copies rather than retaining FAIL/stale band data.

The existing DFF first-fit estimate gives capacity ratios1.059–1.287, including rectangle fragmentation. This remains an estimate; actual mapped cell sizes, placement and GRT/DRT decide closure. Narrow channels make the leaf ft1 bands the smallest estimated margin. No budget, track threshold or clock margin is relaxed.

Source captures event2 2026e1e1561 plus current main7e8e74493 (native SRAM, HCPL/VS/RXSB providers and svc parser/coretap metadata). Existing cutfrac declaration remains included: it corrects analytical per-type FT budgets while the die route model keeps its global minimum0.25; actual partition route gates remain required. The old unadopted die-owned stripe trial and tapered SVC row-shift prototype are not used.

Measured batch: Epyc2 unit oth-ubuntu-1413372-1793562931, exit0. Raw outputs /srv/opentallas-scratch2/claude/codex-s81-a2-1131/refill_typewise. Initial snapshot import failures were before the allocator; corrected exact S81 compact_plan helper was staged. Earlier unstarted waiters were replaced without killing running computation. No P&R launched by this worker during the correction.
