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
 if {![[$i getMaster] isBlock]} continue
 set p [get_pins [$i getName]/ck]
 set fields {}
 foreach prop {arrival_max_rise arrival_min_rise arrival_max_fall arrival_min_fall slew_max_rise slew_min_rise slew_max_fall slew_min_fall} {
  lappend fields "$prop=[get_property $p $prop]"
 }
 puts "PARENT_DRIVER $C [$i getName] $fields"
}
exit
