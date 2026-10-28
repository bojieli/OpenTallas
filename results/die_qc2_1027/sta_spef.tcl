# DIE-QC-2: clock-tree STA on a clock-only SPEF (spef_ck.py) of the combo GRT estimate; same arrival dump as mk_combo_qc
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_verilog /clk/ctree.v
link_design ctree
read_spef /out/ck_$::env(MODE)_$::env(CORNER).spef
create_clock -name vclk -period 833.333
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [get_ports t_*]
set_output_delay 0 -clock vclk [get_ports t_*]
set fh [open /out/arr_$::env(MODE)_$::env(CORNER).txt w]
foreach p [get_ports t_*] { puts $fh "T [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}] [get_property $p slack_min_rise] [get_property $p slew_max_rise]" }
foreach i [get_cells *] { set q [get_pins [get_full_name $i]/Y]; set a [get_pins [get_full_name $i]/A]; puts $fh "N [get_full_name $i] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise] [get_property $a slew_max_rise] [get_property $q slew_max_rise]" }
close $fh
report_check_types -max_slew -violators
puts OT_DONE
