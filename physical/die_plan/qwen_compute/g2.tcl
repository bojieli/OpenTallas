set_thread_count 16
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /work/parts.lef
read_def /work/die.def
make_tracks M1 -x_offset 0.018 -x_pitch 1.333333 -y_offset 0.018 -y_pitch 1.333333
make_tracks M2 -x_offset 0.045 -x_pitch 1.333333 -y_offset 0.045 -y_pitch 1.333333
make_tracks M3 -x_offset 0.009 -x_pitch 1.333333 -y_offset 0.009 -y_pitch 1.333333
make_tracks M4 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048
make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048
make_tracks M6 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064
make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064
make_tracks M8 -x_offset 0.116 -x_pitch 0.08 -y_offset 0.116 -y_pitch 0.08
make_tracks M9 -x_offset 0.116 -x_pitch 0.08 -y_offset 0.116 -y_pitch 0.08
set_routing_layers -signal M2-M9 -clock M2-M9
set_global_routing_layer_adjustment M2-M7 0.0
set_global_routing_layer_adjustment M8-M9 0.0
set t0 [clock seconds]
global_route -congestion_iterations 0 -allow_congestion -verbose -congestion_report_file /work/g2_congestion.rpt
puts "OT_G2_GRT_S [expr {[clock seconds]-$t0}]"
catch {report_wire_length -net clk_spine -global_route}
catch {report_wire_length -net rst_async -global_route}
