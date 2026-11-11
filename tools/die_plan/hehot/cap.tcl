# DS85-HEHOT capacity probe (GRT only, DO_NOT_COUNT, in-memory edits only). hca swap identical to grt_hca.tcl, then
# WI=v0: as hca; v1: he master +M6 full-outline OBS (delta = M6 capacity GRT gives he); v2: he M5 OBS removed;
# v3: he M4+M5 OBS removed; v4: he M5 pins dropped from capacity (pins kept) not possible -> skipped.
read_db /r/4_cts.odb
set db [ord::get_db]; set b [ord::get_db_block]; set tech [$db getTech]
set fh [open /l/swap.list]; set pairs {}
while {[gets $fh line] >= 0} { if {[string trim $line] eq ""} continue; lassign $line old lef; read_lef -library /l/$lef; lappend pairs $old }
close $fh
set n 0
foreach i [$b getInsts] { set nm [[$i getMaster] getName]; if {[lsearch -exact $pairs $nm] < 0} continue
  if {![$i swapMaster [$db findMaster ${nm}_hca]]} { error "swap failed" }; incr n }
puts "WI swapped $n"
set he [$db findMaster ot_v41_rom_elem_q_qxpq_w10_gb_he_hca]
set W [$he getWidth]; set H [$he getHeight]
set wi $::env(WI); set k 0
if {$wi eq "v1"} { odb::dbBox_create $he [$tech findLayer M6] 0 0 $W $H; set k 1 }
if {$wi eq "v2" || $wi eq "v3"} {
  set kill [expr {$wi eq "v2" ? {M5} : {M4 M5}}]
  foreach o [$he getObstructions] { set l [$o getTechLayer]; if {$l ne "NULL" && [lsearch $kill [$l getName]] >= 0} { odb::dbBox_destroy $o; incr k } }
}
puts "WI $wi edits $k"
set_routing_layers -signal M2-M7 -clock M2-M7
foreach {l a} {M2 0.5 M3 0.5 M4 0.25 M5 0.25 M6 0.30 M7 0.30} { set_global_routing_layer_adjustment $l $a }
set t0 [clock seconds]
global_route -congestion_iterations $::env(IT) -allow_congestion -verbose -congestion_report_file /o/$wi.congestion.rpt
puts "WI_DONE [expr {[clock seconds]-$t0}] s"
