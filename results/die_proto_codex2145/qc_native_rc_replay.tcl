read_db /work/combo_TT.odb
foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] {read_liberty $f}
set_routing_layers -signal M4-M7 -clock M8-M9
read_global_route_segments /work/segments_TT.txt
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
foreach scale {4 8} {
  if {$scale == 4} {set cc 1.3} else {set cc 1.6}
  # Actual dbNet NDR widths already divide resistance. Never divide R again.
  set_layer_rc -layer M8 -resistance 8.44765e-3 -capacitance [expr {.103962*$cc}]
  set_layer_rc -layer M9 -resistance 8.89556e-3 -capacitance [expr {.0928446*$cc}]
  estimate_parasitics -global_routing -spef_file /out/native${scale}w_$::env(CORNER).spef
  if {![file exists /out/native${scale}w_$::env(CORNER).spef] || [file size /out/native${scale}w_$::env(CORNER).spef] == 0} {error "native SPEF export missing"}
  puts [exec python3 /out/restore_clock_spef_caps.py /out/native${scale}w_$::env(CORNER).spef --out /out/fixed${scale}w_$::env(CORNER).spef --width $scale --clock /clock --prefix ck_]
}
puts [exec python3 /out/mix_clock_spef.py /out/fixed4w_$::env(CORNER).spef /out/fixed8w_$::env(CORNER).spef --clock /clock --prefix ck_ --out /out/mixed_$::env(CORNER).spef]
read_spef /out/mixed_$::env(CORNER).spef
puts OT_NATIVE_MIXED_RC_LOADED
create_clock -name vclk -period 833.000
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [get_ports t_*]
set_output_delay 0 -clock vclk [get_ports t_*]
set fh [open /out/arr_$::env(CORNER).txt w]
foreach p [get_ports t_*] {puts $fh "T [get_full_name $p] [expr {833.000-[get_property $p slack_max_rise]}] [get_property $p slack_min_rise] [get_property $p slew_max_rise]"}
foreach i [get_cells ck_n*] {set q [get_pins [get_full_name $i]/Y]; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise]"}
close $fh
report_check_types -max_slew -max_capacitance -violators
puts OT_DONE
