LEP RX locality physical-source candidate, 2026-11-06

Changes: preserve 1762.56x1226.88 outline and all49 native master instances;
move upper pair1/3 +43.2um and move20 RX SRAMs from N row to middle street,
aligned to actual native K bit groups. Retain primary CLK/count-strap island.
Three reset tap sites move; counts/indices remain. Reset depth comparison and
fresh wrapper GEN must complete before adopting a coherent prepared cohort.
No leaf RTL, bus, parameter, strap, clock budget, data cycle or K cycle changes.

Apply head_lep_rx_locality_apply.py BASE_EXACT6 layout_delta.json OUT.json.
The applicator requires the exact reviewed base SHA and verifies its output SHA.
Full immutable source and explicit4106 existing-register placement intent:
epyc5:/srv/opentallas-scratch2/claude/codex-head-lep-clock-1106/rx_data_v5/rf
Full clearance audit reports0 fit errors, preserving4.32um macro halos.
The diagram is source placement intent, not a placed/CTS timing result.
Capture placements are NOT automatically activated by this plan delta.
A fresh-placement adapter must verify exact masters and all existing fixed-cell
and PDN keepouts before applying these target positions or launching CAD.

Die-owner reviewed v5 render and conditionally accepts source/GEN only.
Native M5 clk_c0..3 attachment proposal uses actual pair ITerm metal and helper
d0391d814c8. Provider, phase, source-drive cost and source-plan integration remain
UNBOUND. Exact6 has no real parent provider witness. No ideal-port closure credit.
TT450/FF380 and native ETM timing stay unchanged. No CTS or route authorization.
The previous full-load vA5 clock pilot remains failed (TTmean1226ps), while its
paired CPPR and real data-path results motivated this geometry change.
