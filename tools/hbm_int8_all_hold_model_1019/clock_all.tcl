# READ ONLY frozen native DB; no physical mutation or DB export.
set corner $::env(INT8_CORNER)
source /work/kit/libs_${corner}.tcl
read_db /work/output/cts_checkpoint.odb
source $p/setRC.tcl
source /work/kit/constraints.sdc
set_propagated_clock [all_clocks]
estimate_parasitics -placement
find_timing_paths -path_delay min_max -group_path_count 1
set fd [open /audit/clock_all_$corner.tsv w]
puts $fd "pin\tmode\tarrival_ps"
foreach pin [all_registers -clock_pins] {
 foreach mm {min max} {
  set arrivals {}
  foreach vertex [$pin vertices] {
   if {$vertex eq "NULL"} continue
   set paths [$vertex path_iterator rise $mm]
   while {[$paths has_next]} {
    set path [$paths next];set tag [$path tag]
    if {[lindex $tag 2] ne "^$mm" || [lindex $tag 3] ne "core_clk" || [string first "(clock prop)" $tag]<0} continue
    lappend arrivals [sta::time_sta_ui [$path arrival]]
   }
   $paths finish
  }
  if {[llength $arrivals]!=1} {error "CLOCK_ACTUAL_CARDINALITY [get_full_name $pin] $mm $arrivals"}
  puts $fd "[get_full_name $pin]\t$mm\t[lindex $arrivals 0]"
 }
}
close $fd
puts CLOCK_ALL_NATIVE_MIN_MAX_PASS
