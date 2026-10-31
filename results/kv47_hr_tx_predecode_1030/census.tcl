# DIE-KV-47-HR placed STA census (TT libs, placement parasitics via kit setRC, ideal clock as at 3_place)
foreach l [split [string trim [read [open $::env(LIBS_FILE)]]] " "] { if {$l ne ""} { read_liberty $l } }
read_db $::env(ODB)
read_sdc $::env(SDC)
source $::env(SETRC)
estimate_parasitics -placement
set fh [open $::env(OUT) w]
puts $fh "WS [worst_slack -max] TNS [total_negative_slack -max]"
set n 0
foreach p [find_timing_paths -path_delay max -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] {
  incr n
  set sp [get_full_name [get_property $p startpoint]]
  set ep [get_full_name [get_property $p endpoint]]
  puts $fh "P [get_property $p slack] $sp $ep"
}
puts $fh "NVIOL $n"
close $fh
report_checks -path_delay max -group_path_count 3 -format full_clock_expanded > $::env(OUT).rpt
exit
