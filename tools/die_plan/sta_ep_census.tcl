# Full violating-endpoint census (startpoint, endpoint, slack) of a CTS/route DB.
# env: ODB SDC LIBS SETRC OUT. Writes OUT (setup) and OUT.hold. BENCH-KEEP from QC-HC1-CLKENTRY.
foreach l $::env(LIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
source $::env(SETRC)
set_propagated_clock [all_clocks]
estimate_parasitics -placement
puts "WS [sta::worst_slack -max] TNS [sta::total_negative_slack -max] HWS [sta::worst_slack -min] HTNS [sta::total_negative_slack -min]"
sta::redirect_file_begin $::env(OUT)
report_checks -path_delay max -group_path_count 20000 -endpoint_path_count 1 -slack_max 0 -format summary
sta::redirect_file_end
sta::redirect_file_begin $::env(OUT).hold
report_checks -path_delay min -group_path_count 20000 -endpoint_path_count 1 -slack_max 0 -format summary
sta::redirect_file_end
