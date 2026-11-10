# FACEHOLD-S81 read-only TT max per output-port endpoint, full format (launch clock arrival, every stage), for the
# out-face latch setup estimate (estimate.py tt2).
puts "FH_BEGIN TT_ALL_TO_OUT"
report_checks -path_delay max -to [all_outputs] -group_path_count 100000 -endpoint_path_count 1 -format full -digits 2
puts "FH_END"
puts "FH_DONE"
