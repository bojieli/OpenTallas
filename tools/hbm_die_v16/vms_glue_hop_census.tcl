# pure flop->flop hop distance census on a placed odb (launch flop -> capture flop through buffers/inverters)
# usage (fleet, ORFS image): openroad -exit -no_init vms_glue_hop_census.tcl with /base = the gate base results dir (3_place.odb), /out writable -> /out/hops.txt; aggregate: vms_glue_hop_agg.py hops.txt
read_db /base/3_place.odb
set block [ord::get_db_block]
set dbu [$block getDefUnits]
proc isff {m} { return [regexp {^(DFF|SDF|DHL|DLL|ASYNC)} $m] }
proc isbuf {m} { return [regexp {^(BUF|INV|HB)} $m] }
set fo [open /out/hops.txt w]
foreach inst [$block getInsts] {
  set m [[$inst getMaster] getName]
  if {![isff $m]} continue
  set it [$inst findITerm D]
  if {$it == "NULL"} continue
  set net [$it getNet]
  set depth 0; set src ""; set wl 0
  set cur $net
  while {$cur != "NULL" && $depth < 12} {
    set drv ""
    foreach t [$cur getITerms] { if {[$t isOutputSignal]} { set drv $t; break } }
    if {$drv == ""} { set src "port"; break }
    set di [$drv getInst]; set dm [[$di getMaster] getName]
    if {[isff $dm]} { set src $di; break }
    if {[isbuf $dm]} { set a [$di findITerm A]; set cur [$a getNet]; incr depth; continue }
    set src "logic"; break
  }
  if {$src == "port" || $src == "logic" || $src == ""} { puts $fo "$src $depth 0 [$inst getName]"; continue }
  set l1 [$src getLocation]; set l2 [$inst getLocation]
  set d [expr {(abs([lindex $l1 0]-[lindex $l2 0]) + abs([lindex $l1 1]-[lindex $l2 1]))/double($dbu)}]
  puts $fo "pure $depth [format %.1f $d] [$inst getName]"
}
close $fo
puts HOPS_DONE
