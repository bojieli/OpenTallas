set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
set vs {hbm_su_pghead_r5/views/ot_hbm_su_programme_pghead hbm_su_pgcol_l_r5/views/ot_hbm_su_programme_pgcol_l hbm_su_pgcol_s_r5/views/ot_hbm_su_programme_pgcol_s}
foreach C {TT FF} {
  set L($C) [glob $PLAT/lib/NLDM/*RVT_${C}*]
  foreach v $vs { lappend L($C) /t/views/$v/[file tail $v]_[string tolower $C].lib }
  foreach l $L($C) { read_liberty $l }
}
read_db /r/4_1_cts.odb
read_sdc -mode ss /t/4_cts.sdc
read_sdc -mode ff /t/4_cts.sdc
define_scene WC -mode ss -liberty $L(TT)
define_scene BC -mode ff -liberty $L(FF)
source $PLAT/setRC.tcl
if {[info exists ::env(BCPROP)]} { set_mode ff; set_propagated_clock [all_clocks]; set_mode ss }
source /t/$::env(CHILDREN)
source /t/child_centre_tap_r15.tcl
ot_cct_tap
exit
