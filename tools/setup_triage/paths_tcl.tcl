# Setup-triage path dump (appended after the loop's own SS design load: libs, odb, sdc, spef, extra sdc).
# Text reports only (PathEnd properties crash this OpenROAD build); instance locations come from odb.
puts "TRI_SUMMARY_BEGIN"
report_checks -path_delay max -group_path_count 300 -endpoint_path_count 1 -unique_paths_to_endpoint -slack_max 15 -format summary
puts "TRI_FULL_BEGIN"
report_checks -path_delay max -group_path_count 20 -endpoint_path_count 1 -unique_paths_to_endpoint -slack_max 15 -format full_clock_expanded -fields {fanout cap} > /tri/full.rpt
set fh [open /tri/full.rpt r]; set txt [read $fh]; close $fh
puts $txt
puts "TRI_LOC_BEGIN"
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set seen [dict create]
foreach line [split $txt "\n"] {
  if {[regexp {^\s*[-0-9.]+\s+[-0-9.]+\s+[\^v]\s+(\S+)/\S+\s+\(} $line -> inst] || [regexp {^\s*\S+\s+[-0-9.]+\s+[-0-9.]+\s+[-0-9.]+\s+[\^v]\s+(\S+)/\S+\s+\(} $line -> inst]} {
    if {[dict exists $seen $inst]} continue
    dict set seen $inst 1
    set di [$blk findInst $inst]
    if {$di eq "NULL" || $di eq ""} continue
    set bb [$di getBBox]
    puts [format "TRI_LOC %s %.1f %.1f" $inst [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}] [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}]]
  }
}
foreach bt [$blk getBTerms] {
  set bb [$bt getBBox]
  puts [format "TRI_PORT %s %.1f %.1f" [$bt getName] [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}] [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}]]
}
set die [$blk getDieArea]
puts [format "TRI_DIE %.1f %.1f" [expr {[$die xMax]/double($dbu)}] [expr {[$die yMax]/double($dbu)}]]
puts "TRI_END"
exit
