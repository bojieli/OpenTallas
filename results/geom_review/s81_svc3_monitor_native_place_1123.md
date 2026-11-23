# S81 B2 native SVC3 monitor placement, 2026-11-23

I viewed the native fixed-placement image on E10 at `/srv/opentallas-scratch2/claude/s81-j9-r6/compose/svc3_monitor_codex_1438/native_floorplan_1450/svc3_monitor_native_actual.png`. OpenDB placement unit `oth-ubuntu-4188777-1795474307` and independent ODB readback `oth-ubuntu-34104-1795474385` completed successfully.

All 66 named ASAP7 cells are FIRM, with four flops, an inverter for falling-edge capture, and a retained forwarded-clock buffer per stage. The six distinct M7 endpoint centers match the selected corridor exactly. The two-row width is 3.78 µm. No cell intersects a planned hard box, including the narrow stage 9 gap. The corridor has several over-core legs and requires the upper-metal tracks under actual die reservations. The private zero-delay native RTL test proved the 11 status cycles, 85 matching edges and 76 disagreements with a bypass control.

**PASS-COND for the scoped native corridor route diagnostic.** Evaluate actual native pin escape and segment connectivity in a crop with current hard boxes and the die PG obstruction pattern. Whole-die phase, PG connectivity, complete top clock reservations, TT/FF and sign-off remain release gates.
