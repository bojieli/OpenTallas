# R2 WG spine placement was legal before repair_timing; resizing 342 cells
# enlarged packed FIRM enable/reset buffers and made detailed placement fail.
# Preserve the gated root, clock spine and raw-clock register anchors. Ordinary
# combinational cells in the moved local cone remain eligible for resizing and
# subsequent standard-cell legalization. No location/RTL/clock constraint change.
if {![llength [info procs clock_tree_synthesis_smn_resize_legal]]} {
  rename clock_tree_synthesis clock_tree_synthesis_smn_resize_legal
  proc clock_tree_synthesis {args} {
    set result [uplevel 1 [linsert $args 0 clock_tree_synthesis_smn_resize_legal]]
    if {![info exists ::ot_sp_icg_move] || ![info exists ::ot_sp_icg]} {
      error "SM_NATIVE_RESIZE_LEGAL: through-ICG spine did not establish its local cone"
    }
    set released 0
    foreach inst $::ot_sp_icg_move {
      if {$inst eq $::ot_sp_icg} continue
      set master [[$inst getMaster] getName]
      if {[regexp {^(DFF|DHL|DLL|SDF|ICG|ASYNC_DFF)} $master]} continue
      if {[$inst getPlacementStatus] eq "FIRM"} {
        $inst setPlacementStatus PLACED
        incr released
      }
    }
    if {!$released} { error "SM_NATIVE_RESIZE_LEGAL: no combinational gate-cone cells released" }
    check_placement -verbose
    puts "SM_NATIVE_RESIZE_LEGAL: released $released combinational cone cells for actual resize legalization; ICG and register/spine anchors preserved"
    return $result
  }
}
