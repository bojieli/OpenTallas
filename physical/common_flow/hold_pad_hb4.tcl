# HOLD PAD = HB4 (S-NORM 2026-10-15, measured on s81hc_ctfxnt_ref v5 CTS): ORFS asap7 DONT_USE_CELLS '*xp*_ASAP7*' bars
# every HBnxp67 hold cell from rsz, so repair_timing -hold pads with BUFx2 (FF ~15 ps / 0.0729 um2 per cell).  A strip
# whose every boundary bit needs ~75 ps of contract hold delay (input min L-50 / output min -L-50, +25 uncertainty,
# +30 guard) then takes ~5 BUFx2 per bit: ctfx_nt 3,384 registered boundary bits -> 14,265-19,396 hold buffers inside
# one 115 um pin span, GRT overflow 26,013 (M3 V 15,042) at 14 % average use.  HB4xp67 gives ~37 ps FF per cell
# (0.102 um2): 2.4x the delay per cell, 1.7x per um2 -> ~2.4x fewer pad cells, pins and local nets for the SAME delay.
# Local test (openroad, asap7 FF, 16 skewed reg pairs): BUFx2 32 cells -> HB4 16 cells, worst hold +1.2 -> +11.0 ps.
# The wrapper lifts the dont_use for HB4 ONLY inside repair_timing -hold and restores it afterwards, so setup repair,
# repair_design and CTS never pick the slow cell.  Same constraints, margins and acceptance; idempotent per process.
if {![llength [info procs ::ot_hb4pad_rt_orig]] && [llength [info commands ::repair_timing]]} {
  rename ::repair_timing ::ot_hb4pad_rt_orig
  proc ::repair_timing {args} {
    set hold [expr {[lsearch -exact $args -hold] >= 0}]
    set cells {}
    if {$hold} {
      set cells [get_lib_cells -quiet */HB4xp67_ASAP7_75t_R]
      if {[llength $cells]} { unset_dont_use $cells; puts "OT_HB4PAD: hold repair may pad with HB4xp67 ([llength $cells] lib cells)" }
    }
    set rc [catch {uplevel 1 [list ::ot_hb4pad_rt_orig {*}$args]} out opts]
    if {[llength $cells]} {
      set_dont_use $cells
      set n 0
      foreach i [get_cells -quiet -hierarchical *] {
        if {[get_property $i ref_name] eq "HB4xp67_ASAP7_75t_R"} { incr n }
      }
      puts "OT_HB4PAD: after hold repair the design holds $n HB4xp67 cells"
    }
    return -options $opts $out
  }
}
