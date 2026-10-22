# vms_glue_seam_census.tcl (HBMb/SMH7-VMG 10-21): for every flop D pin, the y of each source flop / input port of its combinational
# fan-in cone, on a placed odb.  usage (fleet, ORFS image): openroad -exit -no_init with /base = gate base results dir
# (3_place.odb) and /out writable -> /out/seam.txt (name y {src ys}); vms_glue_region_map.py turns it into the g8r region map
read_db /base/3_place.odb
set block [ord::get_db_block]
set dbu [$block getDefUnits]
proc isff {m} { return [regexp {^(DFF|SDF|DHL|DLL|ASYNC)} $m] }
set fo [open /out/seam.txt w]
foreach inst [$block getInsts] {
  set m [[$inst getMaster] getName]
  if {![isff $m]} continue
  set it [$inst findITerm D]
  if {$it == "NULL"} continue
  set cy [expr {[lindex [$inst getLocation] 1]/double($dbu)}]
  set seen [dict create]; set q [list [$it getNet]]; set srcs {}; set n 0
  while {[llength $q] && $n < 400} {
    set net [lindex $q 0]; set q [lrange $q 1 end]
    if {$net == "NULL" || [dict exists $seen [$net getId]]} continue
    dict set seen [$net getId] 1; incr n
    foreach bt [$net getBTerms] { if {[$bt getIoType] eq "INPUT"} { lappend srcs "P:[$bt getName]" } }
    foreach t [$net getITerms] {
      if {![$t isOutputSignal]} continue
      set di [$t getInst]; set dm [[$di getMaster] getName]
      if {[isff $dm]} { lappend srcs [format %.0f [expr {[lindex [$di getLocation] 1]/double($dbu)}]]; continue }
      foreach a [$di getITerms] { if {[$a isInputSignal] && ![$a isClocked]} { set an [$a getNet]; if {$an != "NULL" && [$an getSigType] eq "SIGNAL"} { lappend q $an } } }
    }
  }
  puts $fo "[$inst getName] [format %.0f $cy] [lsort -unique $srcs]"
}
close $fo
