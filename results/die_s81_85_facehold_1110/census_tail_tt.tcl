# FACEHOLD-S81 read-only TT max census of the OUT face (appended to the row's TT signoff session cut before so_timing STD):
# worst max path per output-port endpoint (slack, launch pin, launch clock arrival via report), plus the 6 worst reports.
set fh_out [open /out/census_tt.tsv w]
puts $fh_out "slack\tstart\tend"
foreach pe [find_timing_paths -path_delay max -to [all_outputs] -group_path_count 200000 -endpoint_path_count 1] {
  puts $fh_out "[format %.2f [get_property $pe slack]]\t[get_full_name [get_property $pe startpoint]]\t[get_full_name [get_property $pe endpoint]]"
}
close $fh_out
puts "FH_BEGIN TT_WORST_TO_OUT"
report_checks -path_delay max -to [all_outputs] -group_path_count 6 -endpoint_path_count 1 -format full_clock_expanded -digits 2
puts "FH_END"
puts "FH_DONE"
