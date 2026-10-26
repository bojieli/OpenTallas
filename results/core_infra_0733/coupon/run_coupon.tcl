set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $P/lib/NLDM/*RVT_TT*.lib*] {read_liberty $f}
read_verilog /work/coupon.v
link_design coupon
initialize_floorplan -die_area {0 0 86.4 86.4} -core_area {0 0 86.4 86.4} -site asap7sc7p5t
foreach l {M1 M2 M3 M4 M5 M6 M7 M8 M9} {make_tracks $l -x_offset 0.04 -x_pitch 0.08 -y_offset 0.04 -y_pitch 0.08}
add_global_connection -net VDD -inst_pattern .* -pin_pattern ^VDD$ -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern ^VSS$ -ground
global_connect
set b [ord::get_db_block]
foreach {name x y} {f0 16 20 f1 16 66 f2 70 20 f3 70 66} {
  set i [$b findInst $name]
  $i setLocation [expr {int($x*1000)}] [expr {int($y*1000)}]
  $i setPlacementStatus PLACED
}
source /work/master_core_infra.tcl
write_db /work/coupon_once.odb
source /work/master_core_infra.tcl
write_db /work/coupon.odb
write_verilog /work/coupon_final.v
set map [ot_pg_prepare $b]
set pg [ot_pg_collect_all_native $b $map]
puts "COUPON_PG $pg"
puts "CORE_INFRA_COUPON_PASS"
