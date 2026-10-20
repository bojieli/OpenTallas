# Preserve real native clocks, SDC and global-connect/write composition.
proc erase_non_stage_variables {args} {}
proc load_design {args} {
 read_db $::env(TEST_ODB)
 ot_mm_read_sdc /src/tests/canonical_sdc_scene_load_1019/coupon.sdc
 joint_assert_loads loaded
}
proc source_step_tcl {pre step} {source $::env(TEST_BOOTSTRAP)}
proc orfs_write_db {path} {write_db $path}
proc orfs_write_sdc {path} {write_sdc -no_timestamp $path}
