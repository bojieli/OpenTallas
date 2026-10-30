# DIE-QC-49/gen47: die GRT INCLUDING the gen47 clock on the source rebuilt from the kit ctree.v
# (main tools/clk/native_clock_source.py on the plan_qc49 native target; 48,296 CKINVDCx16 + 7,889 native taps).
# Same GRT settings as the gen47 kit GRT (signal M4-M9, adj 0.75 M4-M7 / 0.4 M8-M9, 50 iterations) plus the clock
# nets on their planned layers M8-M9; the kit's clock-track reservation obstructions are removed (the clock itself
# now routes there), full-span PG stripe obstructions are kept. Then routed-RC (estimate_parasitics -global_routing)
# both-edge readout of every clock cell and native tap (DIE-QC-45 edge_readout format). No provider, no PG access.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set O $::env(OUT)
set C $::env(CORNER)
set D $::env(SRC)
foreach f [glob $P/lib/NLDM/*RVT_${C}_nldm*.lib*] { read_liberty $f }
read_db $D/build2/clock_native.odb
set b [ord::get_db_block]
set dbu [[$b getTech] getDbUnitsPerMicron]
set da [$b getDieArea]
set kept 0; set gone 0
foreach o [$b getObstructions] {
  set bb [$o getBBox]
  if {([$bb xMin] == [$da xMin] && [$bb xMax] == [$da xMax]) || ([$bb yMin] == [$da yMin] && [$bb yMax] == [$da yMax])} { incr kept } else { odb::dbObstruction_destroy $o; incr gone }
}
puts "G47_OBS kept_fullspan $kept removed_clock_reservations $gone"
# provider (start/reset) is not imported in this source: its die ports (pst_*/rst*) have no pin geometry -> drop them
set nb 0
foreach bt [$b getBTerms] { if {[llength [$bt getBPins]] == 0} { odb::dbBTerm_destroy $bt; incr nb } }
puts "G47_PROVIDER_PORTS_DROPPED $nb"
create_clock -name dck -period 833.000 [get_ports root]
set_propagated_clock [all_clocks]
source $P/setRC.tcl
set_routing_layers -signal M4-M9 -clock M8-M9
foreach L {M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.75 }
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file $O/congestion.rpt
puts G47_GRT_DONE
if {$C eq "TT"} { write_guides $O/route.guide }
if {[info exists ::env(NDR_RC)] && $::env(NDR_RC) eq "1"} {
  # variant N: clock-layer RC = the planned NDR clock wire the tree was priced with (tree.json meta wire_r/wire_c)
  set_layer_rc -layer M8 -resistance 0.0043358025 -capacitance 0.10824363
  set_layer_rc -layer M9 -resistance 0.0043358025 -capacitance 0.10824363
  puts "G47_NDR_RC M8/M9 r 0.0043358 c 0.1082436"
}
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
puts "G47_CELLS $n"
set tf [open $D/taps.txt]
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
puts G47_ARR_DONE
