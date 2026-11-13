# ---- CLAND-RELAY-3: every FF hold violator endpoint (+ its worst start), after the full kit FF sign-off session ----
report_checks -path_delay min -group_path_count 1000 -endpoint_path_count 1 -slack_max -0.0001 -format end > /out/hold_end.rpt
report_checks -path_delay min -group_path_count 1000 -endpoint_path_count 1 -slack_max -0.0001 -format short > /out/hold_short.rpt
puts "CR2 HOLD done"
