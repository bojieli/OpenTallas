# Private T51 physical form: all signals M5-M6, requested wire repair cap 120um.
# This adds buffers, not RTL cycles.  MIN/MAX_ROUTING_LAYER live in config.mk.
# Source before every placement/resizer/GRT process which may repair data nets.
if {![llength [info commands ot_t51_m5_120_original_repair_design]]} {
  if {![llength [info commands repair_design]]} {
    error "OT_T51_M5_120: repair_design command unavailable"
  }
  rename repair_design ot_t51_m5_120_original_repair_design
  proc repair_design {args} {
    if {[lsearch -exact $args -max_wire_length] >= 0} {
      error "OT_T51_M5_120: conflicting explicit max_wire_length"
    }
    puts "OT_T51_M5_120 repair_design requested_max_wire_length_um=120 args=$args"
    tailcall ot_t51_m5_120_original_repair_design {*}$args -max_wire_length 120
  }
}
puts "OT_T51_M5_120 loaded; physical buffer stages only, RTL PIN CYCLES unchanged"
