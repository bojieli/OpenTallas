LEP RX locality physical-source candidate, 2026-11-06

Changes: preserve 1762.56x1226.88 outline and all49 native master instances;
move upper pair1/3 +43.2um and move20 RX SRAMs from N row to middle street,
aligned to actual native K bit groups. Retain primary CLK/count-strap island.
Three reset tap sites move; counts/indices remain. Optional per-type floor7
adds real reset padding, preserving K7/release8. Actual tree comparison PASS;
fresh wrapper GEN PASS (E5 unit oth-ubuntu-469795-1793980294).
Actual7 START raw outputs preserve phases with unique new relay sources.
Export6 alone moves to [605.88,520.02] in an existing TX vertical channel.
Max refreshed parent hop284.692um; conservative whole-copy D-feed401.544um.
All7 proposed1.404x0.27 output-copy footprints fit full4.32um macro halos.
No leaf RTL, bus, parameter, strap, clock budget, data cycle or K cycle changes.

Apply head_lep_rx_locality_apply.py BASE_EXACT6 layout_delta.json OUT.json.
Requires codex/head-reset-depth-1106 capability tip2bd68c68300 (schema+generator).
The applicator requires the exact reviewed base SHA and verifies its output SHA.
Full immutable source and explicit4106 existing-register placement intent:
epyc5:/srv/opentallas-scratch2/claude/codex-head-lep-clock-1106/rx_data_v8/rf
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

Prepared source/GEN-only event: epyc5 rx_data_v8/prep/source_plan.json
Prepared SHA256 2eade5a773cf8ccfab25e77a46ddfdc08f1c672fbf5e73a7e1019aabadc14134
RF input SHA256 0c40fc53244a182777aa3547b120012e5996df7d4426d4e61a7e1e929ad5ae35
(The preparation tool writes equivalent JSON with indent1.)
Sidecar90d006a48f17 unchanged; only hd_lep0N republished. No CLOCK credit.

Actual production reset RTL component: 400-edge lockstep PASS across7 raw exports,
using production reset_tree.rtl_lines + alias/private-output patchers and real
ot_dp_rrelay/rgate/raw_export_pair module definitions. Depth4-for5 mutant FAIL
at edge35. This proves the scoped reset-output phases, not native token gates.
Proof capsule E5 rx_data_v8/actual_reset_rtl_a3; unit590463-1793980677.
