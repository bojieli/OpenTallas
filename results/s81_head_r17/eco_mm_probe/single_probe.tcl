foreach l $::env(BC_LIB_FILES) { read_liberty $l }
read_db $::env(RESULTS_DIR)/5_1_grt.odb
read_sdc /probe/4_cts.sdc
set_clock_latency -source 202.5 [get_clocks vclk]
read_spef $::env(RESULTS_DIR)/6_final.spef
puts [format "PROBE single-BC spef hold %.3f" [sta::time_sta_ui [sta::worst_slack_cmd min]]]
exit
