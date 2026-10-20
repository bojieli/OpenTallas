set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
set libs [glob $P/lib/NLDM/*RVT_FF*]
foreach l $libs {read_liberty $l}
set ::env(LIB_FILES) $libs
unset -nocomplain ::env(CORNERS)
set ::env(RESULTS_DIR) /audit/coupon$::env(COUPON_N)
set ::env(DESIGN_NAME) top
read_verilog $::env(RESULTS_DIR)/1_2_yosys.v
link_design top
source /src/tools/ref_tile/native_census.tcl
puts PLACEMENT_STARTED
