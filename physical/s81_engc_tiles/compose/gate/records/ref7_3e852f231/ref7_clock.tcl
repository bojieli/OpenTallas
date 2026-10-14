# per-corner clock path dump of the composition after CTS: env CORNER (TT/FF/SS), /base = ORFS base, /src = snapshot
set C $::env(CORNER); set c [string tolower $C]
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $PLAT/lib/NLDM/*RVT_${C}*] { read_liberty $l }
foreach v {physical/s81_ph_views/closed/dsfd_engram_lkp/dsfd_engram_lkp physical/s81_ph_views/closed/dsfd_engram_sink/dsfd_engram_sink physical/s81_engc_tiles/views/ot_engc_t_win/ot_engc_t_win physical/s81_engc_tiles/views/ot_engc_t_io/ot_engc_t_io physical/s81_engc_tiles/views/ot_engc_t_ws/ot_engc_t_ws physical/s81_engc_tiles/views/ot_engc_t_pbb/ot_engc_t_pbb physical/s81_engc_tiles/views/ot_engc_t_pbc/ot_engc_t_pbc} { read_liberty /src/${v}_$c.lib }
read_db /base/$::env(DB)
read_sdc /base/$::env(SDC)
source $PLAT/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set b [ord::get_db_block]
foreach i [$b getInsts] {
  set n [$i getName]
  if {[[$i getMaster] isBlock]} {
    set p [get_pins $n/ck]; set bb [$i getBBox]
    set it [$i findITerm ck]; set net [[$it getNet] getName]
    lassign [lindex [$it getGeometries] 0] ; set r [$it getBBox]
    puts "CKP $C MAC $n arr [format %.1f [expr {[get_property $p arrival_max_rise]*1}]] slew [format %.1f [get_property $p slew_max_rise]] pin ([expr {[$r xMin]/1000.0}] [expr {[$r yMin]/1000.0}]) net $net"
  } elseif {[string match *u_hdly_ck_* $n]} {
    set a [get_property [get_pins $n/A] arrival_max_rise]; set y [get_property [get_pins $n/Y] arrival_max_rise]
    lassign [$i getLocation] x yy
    puts "CKP $C HB $n A [format %.1f $a] Y [format %.1f $y] d [format %.1f [expr {$y-$a}]] at ([expr {$x/1000.0}] [expr {$yy/1000.0}]) slewY [format %.1f [get_property [get_pins $n/Y] slew_max_rise]]"
  }
}
foreach group {status_win xtrans_pb0 rst_win rst_io rst_ws rst_pb1 rst_pb0 rst_pb2 rst_lkp rst_sink} {
 set values {}
 foreach cell [get_cells -quiet *u_${group}*] {
  foreach pin [get_pins -of_objects $cell] {
   if {![string match */CLK [get_full_name $pin]]} continue
   lappend values [get_property $pin arrival_max_rise]
  }
 }
 if {[llength $values]} {
  set total 0.0; foreach v $values {set total [expr {$total+$v}]}
  set values [lsort -real $values]
  puts "CKP_LOGIC $C $group n=[llength $values] min=[lindex $values 0] mean=[expr {$total/[llength $values]}] max=[lindex $values end]"
 }
}
exit
