# Mini die: one R0 and one MY instance of a closed master on the die track/site convention; real DRT pin access.
set PLAT /home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7
read_lef $PLAT/lef/asap7_tech_1x_201209.lef
read_lef $PLAT/lef/asap7sc7p5t_28_R_1x_220121a.lef
if {[info exists ::env(PRELEF)]} { foreach l $::env(PRELEF) { read_lef $l } }
read_lef $::env(MLEF)
set db [ord::get_db]; set chip [odb::dbChip_create $db]; set blk [odb::dbBlock_create $chip mini]
set tech [$db getTech]; $blk setDefUnits 1000
set M [$db findMaster $::env(MASTER)]
set W [$M getWidth]; set H [$M getHeight]
set xa $::env(XA); set xb $::env(XB)
$blk setDieArea [odb::new_Rect 0 0 [expr {$xb + $W + 20160}] [expr {$H + 21600}]]
set a [odb::dbInst_create $blk $M A]; $a setOrient R0; $a setLocation $xa 10800; $a setPlacementStatus FIRM
set b [odb::dbInst_create $blk $M B]; $b setOrient MY; $b setLocation $xb 10800; $b setPlacementStatus FIRM
set n 0
foreach mt [$M getMTerms] {
  set st [$mt getSigType]; if {$st eq "POWER" || $st eq "GROUND"} continue
  set net [odb::dbNet_create $blk "n$n"]; incr n
  [$a findITerm [$mt getName]] connect $net; [$b findITerm [$mt getName]] connect $net
}
puts "OT_NETS $n"
source $PLAT/openRoad/make_tracks.tcl
puts "OT_INST A [$a getOrient] [$a getLocation] B [$b getOrient] [$b getLocation]"
pin_access -bottom_routing_layer M2 -top_routing_layer M7 -verbose 1
puts OT_PA_DONE
