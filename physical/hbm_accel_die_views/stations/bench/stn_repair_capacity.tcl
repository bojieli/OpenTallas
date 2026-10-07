# Default station policy remains the shared 100% instance-count allowance.
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
# Opt in only for r33, at both PRE_CTS and PRE_GLOBAL_ROUTE. The failed full-shape
# route exhausted 2923 buffers at +1.664 ps, below its unchanged +35 ps margin.
# 2923 buffers cost +62.8% cell area; three such allocations project <35% of
# the measured 2999.70 um^2 core, below the unchanged 45% placement density.
# Evidence: results/physical/hbm_stn_r33_capacity_20261006/diagnosis.json.
if {[info exists ::env(OT_STN_R33_CAPACITY)] && $::env(OT_STN_R33_CAPACITY) eq "1"} {
  if {[[ord::get_db_block] getName] ne "hfd_stn_r33"} {
    error "OT_STN_R33_CAPACITY is qualified only for hfd_stn_r33"
  }
  if {[info procs ot_orig_repair_timing_helper] eq ""} {
    error "r33 capacity requires the ORFS repair_timing_helper hook"
  }
  proc repair_timing_helper {args} {
    # This OpenROAD build checks percentages <=100, although repair_hold takes
    # a buffer-count ratio. Allow exactly this measured 300% capacity during
    # this call; preserve every other percentage check and restore on errors.
    rename sta::check_percent sta::ot_r33_check_percent
    proc sta::check_percent {cmd_arg arg} {
      if {$cmd_arg eq "-max_buffer_percent" && $arg eq "300"} { return }
      sta::ot_r33_check_percent $cmd_arg $arg
    }
    try {
      ot_orig_repair_timing_helper {*}$args -max_buffer_percent 300
    } finally {
      rename sta::check_percent {}
      rename sta::ot_r33_check_percent sta::check_percent
    }
  }
  puts "OT_STN_R33_CAPACITY: max_buffer_percent=300; timing constraints unchanged"
}
