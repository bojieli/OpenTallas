read_db /kit/run/results/asap7/dp_coll_ucie/base/2_1_floorplan.odb
source /probe/fully_fixed_macros.tcl
puts NATIVE_MANUAL_BEGIN
place_macro -macro_name {u_bound.u_io_ucie} -location {0.0000 0.0000} -orientation R0 -exact
puts NATIVE_MANUAL_PASS
rtl_macro_placer -halo_width 0.05 -halo_height 0.05
