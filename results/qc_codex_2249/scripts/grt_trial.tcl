# Diagnostic die GRT on actual fixed clock + complete physical PG access.
# PG IR remains NOT RUN: TRIAL ONLY, never freeze/signoff evidence.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_db /srv/opentallas-scratch2/claude/codex-qc-2249/complete_pg/provider.odb
create_clock -name dck -period 833.000 [get_ports root]
set_clock_uncertainty -setup 60 [get_clocks dck]
set_clock_uncertainty -hold 25 [get_clocks dck]
set_routing_layers -signal M4-M9 -clock M8-M9
foreach L {M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.75 }
# The actual pre-routes and their clock obstructions already take capacity.
set_global_routing_layer_adjustment M8 0
set_global_routing_layer_adjustment M9 0
global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file /srv/opentallas-scratch2/claude/codex-qc-2249/grt_trial/congestion.rpt
write_guides /srv/opentallas-scratch2/claude/codex-qc-2249/grt_trial/route.guide
write_db /srv/opentallas-scratch2/claude/codex-qc-2249/grt_trial/routed.odb
puts QC_ACTUAL_GRT_TRIAL_DONE
