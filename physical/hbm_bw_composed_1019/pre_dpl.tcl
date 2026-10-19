source /src/physical/dsrom_window_source/leaf_inhold_release.tcl
source /src/physical/qwen_die_masters/out_flop_release.tcl
# Restore the GPL boundary exclusion list across ORFS's separate processes.
set ::ot_bw_composed_boundary {}
foreach ot_bw_file {ot_out_flop_at_pins.txt ot_inhold_firm.txt} {
  set ot_bw_path $::env(RESULTS_DIR)/$ot_bw_file
  if {![file exists $ot_bw_path]} continue
  set ot_bw_fh [open $ot_bw_path r]
  foreach ot_bw_name [split [read $ot_bw_fh] "\n"] {
    if {$ot_bw_name ne ""} { dict set ::ot_bw_composed_boundary $ot_bw_name 1 }
  }
  close $ot_bw_fh
}
source /src/physical/hbm_bw_composed_1019/core_band.tcl
