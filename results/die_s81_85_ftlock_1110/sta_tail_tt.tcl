set fp [open /out/pairs.txt]; set pairs [split [string trim [read $fp]] "\n"]; close $fp
set names [dict create]
foreach c [get_cells *] { dict set names [get_full_name $c] $c }
puts "PROBE_PAIRS [llength $pairs]"
foreach pr $pairs {
  lassign [split $pr "\t"] a b
  if {![dict exists $names $a] || ![dict exists $names $b]} { puts "PROBE_MISSING $a $b"; continue }
  puts "PROBE_BEGIN TT_MAX $a $b"
  report_checks -path_delay max -from [dict get $names $a] -to [dict get $names $b] -format full_clock_expanded -digits 2
  puts "PROBE_BEGIN FF_MIN_SAME $a $b"
  report_checks -path_delay min -from [dict get $names $a] -to [dict get $names $b] -format full_clock_expanded -digits 2
  puts "PROBE_END"
}
