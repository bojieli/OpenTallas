# HBM-HUBMESH-6 DRT feasibility from GRT guides on a COARSE gcell grid (diagnostic, not counted).
# The GRT grid (0.57 um, 14415x7578 = 109 M gcells) stalled the a3p full run; here the guides are read into a fresh db
# whose GCELLGRID step is GSTEP (default 9 x 570 dbu); DRT snaps each guide to the coarse gcells.
set t0 [clock seconds]
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_def /o/pilot.def
source $P/openRoad/make_tracks.tcl
set block [ord::get_db_block]
set die [$block getDieArea]
set st $::env(GSTEP)
set g [$block getGCellGrid]
if {$g == "NULL"} { set g [odb::dbGCellGrid_create $block] }
$g addGridPatternX 0 [expr {[$die xMax] / $st + 1}] $st
$g addGridPatternY 0 [expr {[$die yMax] / $st + 1}] $st
puts "OT_GCELL step $st nx [expr {[$die xMax] / $st + 1}] ny [expr {[$die yMax] / $st + 1}]"
create_ndr -name CK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.32 M9 0.32}
foreach n [get_nets n_*] { assign_ndr -ndr CK2W2S -net [get_full_name $n] }
set_routing_layers -signal M2-M9 -clock M8-M9
read_guides /o/route.guide
puts "OT_T init [expr {[clock seconds]-$t0}]"
detailed_route -output_drc /o/drc.rpt -verbose 1 -droute_end_iter $::env(ENDIT)
puts "OT_T drt [expr {[clock seconds]-$t0}]"
proc dump {tag corner} {
  set fh [open /o/tree_${tag}_${corner}.txt w]
  foreach c [get_cells *] {
    set n [get_full_name $c]
    if {[string match L_* $n]} { set pins {A} } else { set pins {A Y} }
    foreach pn $pins {
      set p [get_pins $n/$pn]
      puts $fh "$pn $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
    }
  }
  close $fh
}
proc timing {} {
  create_clock -name vclk -period 833.0
  set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
  set_input_delay 0 -clock vclk [get_ports root]
  foreach c [get_cells M*] { set_disable_timing $c }
}
source $P/setRC.tcl
timing
define_process_corner -ext_model_index 0 X
# CLOCK-128-R6 width-aware extraction: RPERSQ (ohm/sq) = rules r(w0) x w0 per layer, R = RPERSQ x L / w
# OWNER 12.24 optimistic size-effect credit per layer (credit at width): M1=1:w0 M2=1:w0 M3=1:w0 M4=1:w0 M5=1:w0 M6=1:w0 M7=1:w0 M8=0.826816:0.08 M9=0.826816:0.08
set ot_tech [ord::get_db_tech]
[$ot_tech findLayer M1] setResistance 0.563166
[$ot_tech findLayer M2] setResistance 0.534825
[$ot_tech findLayer M3] setResistance 0.563166
[$ot_tech findLayer M4] setResistance 0.432876
[$ot_tech findLayer M5] setResistance 0.455842
[$ot_tech findLayer M6] setResistance 0.380144
[$ot_tech findLayer M7] setResistance 0.400304
[$ot_tech findLayer M8] setResistance 0.27935
[$ot_tech findLayer M9] setResistance 0.29417
extract_parasitics -ext_model_file $P/rcx_patterns.rules -lef_res
write_spef /o/drt.spef
dump drt TT
write_db /o/drt.odb
write_def /o/drt.def
puts "OT_DONE [expr {[clock seconds]-$t0}]"
