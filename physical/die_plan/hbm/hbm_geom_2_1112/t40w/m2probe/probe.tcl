# HBM-GEOM-2 11-12 M2 face-pin probe: W-face pins on M2 (the 3rd layer of NW_mcb.E / PHY_NW.W), each to a boundary DFF.
# MODE (env): pins per 0.27 row on M2 (2 = 7.4/um, the event needs ~2.3/um on M2); detail route must give 0 DRC and no
# pin-access errors.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set ppr $::env(PPR)
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l [glob $P/lib/NLDM/*RVT*TT*.lib*] { catch {read_liberty $l} }
read_verilog /w/m2probe.v
link_design m2probe
initialize_floorplan -die_area [list 0 0 $::env(DW) 69.12] -core_area [list 0 0 $::env(DW) 69.12] -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
set tr [list 0.081 0.189 0.135 0.225]
set step $::env(STEP)
set i 0
set row 2
while {$i < 200} {
  for {set k 0} {$k < $ppr && $i < 200} {incr k} {
    set y [expr {$row * 0.27 + [lindex $tr $k]}]
    place_pin -pin_name "in_w\[$i\]" -layer M2 -location [list 0.0 $y] -pin_size {0.072 0.018} -force_to_die_boundary
    incr i
  }
  set row [expr {$row + $step}]
}
place_pins -hor_layers M4 -ver_layers M5 -exclude left:* -exclude bottom:* -exclude top:*
global_placement -skip_io -density 0.6
detailed_placement
check_placement
set_routing_layers -signal M2-M7
global_route -allow_congestion -verbose
detailed_route -droute_end_iter 20 -output_drc /w/drc_${ppr}_${step}_$::env(DW).rpt -verbose 1
puts "M2PROBE ppr=$ppr step=$step dw=$::env(DW) DONE"
write_def /w/m2probe_${ppr}_${step}_$::env(DW).def
