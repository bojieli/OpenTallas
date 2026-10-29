SPB native bank clock interface estimate

Source native placement: codex/hbm-spb-native-1029@e64c6bba8. Source plan is the PG-consistent 103.68 um PHY street candidate; SHA is recorded in clock_budget.json. This is a proposed parent-composed C25c event, not an independently adopted plan or P&R approval.

The existing q_spb0 grid has 20 soft clock entries plus 2 core entries. Native bank placement adds 4104 actual FFs not represented by the previous planned_sinks inventory. The old grid leaves 830 of these FFs beyond 200 um. The proposed density clock delta supplies 8 soft entries, with maximum 1026 sinks and 139.3 um radius, while retaining the 2 core entries. Parent must regenerate GEN, CA and clock/reset/START contracts together. Fixed native FFs must be counted once.

spb_bank_clock_hosting.json preserves the rejected e53 placement finding: 2054 FF bodies per partition collided with the full VDDPHY domain. e64 placement and the PG-consistent source fix that collision without shrinking PG. The full PG rectangle starts at x=40.04, not the old clock-only keepout x=69.12.

The coupon uses shared physical DME source c0e4ae487, the exact fast-detour helper from 45717fa03, and excludes all 4104 actual native FF footprints from clock-cell homes. Runtime source dependencies are the adjacent tools_actual2/die_plan snapshot, fast_detour_v2.py, adaptive_detour_v2.py, clock_reach.py, stage_actual_ttff.json and spb_clock_budget/clock_delta.json. Active job at packet creation: intel2 oth-ubuntu-3919067-1793262540, python3919916; output /srv/opentallas-scratch2/claude/codex-hbm-clock-1028/actual_spb_clock. No terminal construction result yet.

No route or STA has run. Parent current-plan PG/CA, review of actual geometry, frozen legal clock homes and signal G2 capacity remain prerequisites to any physical adoption. The pin lane owns the signal-only G2 probe.

Update: original SPB coupon was superseded for a structural modeling bug, not a timeout: native soft FF home exclusions were incorrectly also wire barriers. Only exact own PID3919916 was stopped; its SUPERSEDED.txt and logs remain. coupon_spb_clock_v2.py uses placement-only site.legal exclusions and preserves hard macro/PG wire barriers. New job intel2 oth-ubuntu-10312-1793263337, python10516, output actual_spb_clock_v2; no result at packet creation. Old A* physical baseline2391204 remains live.

The composed type split retains NW_spb0=q_spb0 and changes NE_spb0=q_spb0__physical_v1 with identical native FF bank geometry. Apply the clock_update to both types once each.

Calibration qualification: existing positive coupon windows use retained raw OpenSTA EARLY stage fits and heuristic TT/FF core-early balancing. They are geometry diagnostics only, not setup timing predictions. fit_actual_clock.py and raw_parent_fits.json preserve a same-master raw TT/FF LATE/EARLY per-actual-parent-edge fit from retained trial2b, including full and <=405um domain outlier rows. Fits are NOT READY: TTlate residual max215ps globally and128ps within405um; substantial inherited narrow M7 pin-access routing and high input slew explain important errors despite nominal M8/M9 NDR. No cross-die fit transfer or new STA invocation.
