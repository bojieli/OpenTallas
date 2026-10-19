# Read-only reproduction of canonical ot_mm_read_sdc ordering on actual 1_synth.
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach corner {TT FF} {
 set libs($corner) {}
 foreach name [list asap7sc7p5t_AO_RVT_${corner}_nldm_211120.lib.gz asap7sc7p5t_OA_RVT_${corner}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${corner}_nldm_220122.lib.gz asap7sc7p5t_SEQ_RVT_${corner}_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_${corner}_nldm_211120.lib.gz] {
  lappend libs($corner) $plat/lib/NLDM/$name
  read_liberty $plat/lib/NLDM/$name
 }
}
read_db $::env(COUPON_ODB)
set base $::env(COUPON_OUT)
set sdc /src/tests/pg_canonical_coupon_1019/component.sdc
read_sdc -mode ss $sdc
read_sdc -mode ff $sdc
set_mode ss
write_sdc -no_timestamp ${base}/before_define_scene_ss.sdc
define_scene TC -mode ss -liberty $libs(TT)
define_scene BC -mode ff -liberty $libs(FF)
set_mode ss
write_sdc -no_timestamp ${base}/after_define_scene_ss.sdc
set_mode ff
write_sdc -no_timestamp ${base}/after_define_scene_ff.sdc
set_mode ss
source /src/tests/pg_canonical_coupon_1019/component_boundary.tcl
write_sdc -no_timestamp ${base}/after_boundary_ss.sdc
set_mode ff
source /src/tests/pg_canonical_coupon_1019/component_boundary.tcl
write_sdc -no_timestamp ${base}/after_boundary_ff.sdc
exit
