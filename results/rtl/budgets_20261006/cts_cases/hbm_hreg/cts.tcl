foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_SS*] { read_liberty $l }
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /work/ckplan.v
link_design ckplan
initialize_floorplan -die_area {0 0 24401.520 24621.840} -core_area {0 0 24401.520 24621.840} -site asap7sc7p5t
source /work/place.tcl
read_sdc /work/clocks.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_wire_rc -clock -layers {M6 M7}
set_wire_rc -signal -layers {M4 M5}
proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; puts "OTMEM $tag [expr {$r/1024}] MB [clock seconds]" }
mem loaded
set t0 [clock seconds]
clock_tree_synthesis -root_buf BUFx24_ASAP7_75t_R -buf_list {BUFx4_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx16f_ASAP7_75t_R} -sink_clustering_enable \
  -distance_between_buffers 150.0
puts "OT_TIME cts_s=[expr {[clock seconds]-$t0}]"
mem cts
write_db /work/cts.odb
exit
