# DIE-QC-50/gen47ndr stage 1: die GRT INCLUDING the gen47 clock with the planned clock NDR assigned to the clock nets.
# Source = predecessor DIE-QC-49/gen47 build2/clock_native.odb (48,296 CKINVDCx16, 7,889 native M7 taps), same GRT setup
# as grt_src.tcl (signal M4-M9, clock M8-M9, adj 0.75 M4-M7 / 0.4 M8-M9, 50 it; kit clock-track reservation obstructions
# removed, full-span PG stripe obstructions kept; pinless provider ports dropped).  NEW: NDR CLK2W2S = width 0.08 /
# spacing 0.08 on M8/M9 (R = R_sq/0.08 = 4.22 / 4.45 ohm/um = planned tree meta wire_r 4.336 ohm/um), assigned to every
# clock net (assign_ndr -all_clocks).  Then (a) GRT-NDR early-indicator readout on estimate_parasitics -global_routing
# (native estimator credits the NDR width), (b) clock-only DRT input DB: non-clock nets destroyed (their GRT guides go
# with them), native ASAP7 M1-M3 tracks (ORFS make_tracks; the source has 0.72-um sparse M1-M3 tracks), write clk_grt.odb.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set O $::env(OUT)
set C $::env(CORNER)
set R $::env(RUN)
foreach f [glob $P/lib/NLDM/*RVT_${C}_nldm*.lib*] { read_liberty $f }
read_db /srv/opentallas-scratch2/claude/die-qc-49/g47src/build2/clock_native.odb
set b [ord::get_db_block]
set da [$b getDieArea]
set kept 0; set gone 0
foreach o [$b getObstructions] {
  set bb [$o getBBox]
  if {([$bb xMin] == [$da xMin] && [$bb xMax] == [$da xMax]) || ([$bb yMin] == [$da yMin] && [$bb yMax] == [$da yMax])} { incr kept } else { odb::dbObstruction_destroy $o; incr gone }
}
puts "NDR_OBS kept_fullspan $kept removed_clock_reservations $gone"
set nb 0
foreach bt [$b getBTerms] { if {[llength [$bt getBPins]] == 0} { odb::dbBTerm_destroy $bt; incr nb } }
puts "NDR_PROVIDER_PORTS_DROPPED $nb"
create_clock -name dck -period 833.000 [get_ports root]
set_propagated_clock [all_clocks]
source $P/setRC.tcl
create_ndr -name CLK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.08 M9 0.08}
assign_ndr -ndr CLK2W2S -all_clocks
set nndr 0
foreach n [$b getNets] { if {[$n getNonDefaultRule] ne "NULL"} { incr nndr } }
puts "NDR_ASSIGNED $nndr"
set r [$b findNonDefaultRule CLK2W2S]
foreach ln {M7 M8 M9} { set lr [$r getLayerRule [[ord::get_db_tech] findLayer $ln]]; if {$lr ne "NULL"} { puts "NDR_LAYER $ln w [$lr getWidth] s [$lr getSpacing]" } }
set_routing_layers -signal M4-M9 -clock M8-M9
foreach L {M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.75 }
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file $O/congestion.rpt
puts NDR_GRT_DONE
estimate_parasitics -global_routing
set fh [open $O/edges_raw.txt w]
set n 0
foreach inst [$b getInsts] {
  set nm [$inst getName]
  if {[string range $nm 0 2] ne "ck_"} continue
  set p [get_pins -quiet $nm/Y]
  if {![llength $p]} { puts $fh "C $nm [[$inst getMaster] getName] NA"; continue }
  puts $fh "C $nm [[$inst getMaster] getName] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_rise] [get_property $p slew_max_fall]"
  incr n
}
puts "NDR_CELLS $n"
set tf [open $R/taps.txt]
while {[gets $tf l] >= 0} {
  lassign $l t inst pin x y
  set p [get_pins -quiet $inst/$pin]
  if {[llength $p]} {
    set drv ""
    set net [get_nets -quiet -of_objects $p]
    if {[llength $net]} { foreach dp [get_pins -quiet -of_objects $net -filter "direction==output"] { set drv [get_full_name $dp] } }
    puts $fh "T $t [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_rise] $drv"
  } else { puts $fh "T $t NA" }
}
close $tf
close $fh
puts NDR_ARR_DONE
if {$C eq "TT"} {
  set ng 0; set nd 0
  foreach n [$b getNets] {
    if {[$n getNonDefaultRule] ne "NULL"} { incr ng [llength [$n getGuides]]; continue }
    if {[$n getSigType] eq "POWER" || [$n getSigType] eq "GROUND"} continue
    odb::dbNet_destroy $n; incr nd
  }
  puts "NDR_CLKONLY destroyed_signal_nets $nd clock_guides $ng"
  foreach tg [$b getTrackGrids] { set l [[$tg getTechLayer] getName]; if {$l in {M1 M2 M3}} { odb::dbTrackGrid_destroy $tg } }
  make_tracks M3 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
  foreach yo {0.045 0.081 0.117 0.153 0.189 0.225 0.270} { make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset $yo -y_pitch 0.270 }
  make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
  write_db $O/clk_grt.odb
  puts NDR_DB_DONE
}
