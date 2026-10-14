# Native local collective port: two independent asynchronous physical roots.
# Reuse the established spine algorithm without running TritonCTS over a
# protected finished root. Keep node numbers unique across the two calls.
if {![info exists ::ot_native_dual_spine_installed]} {
  if {![llength [info procs ot_clock_spine]]} {
    error "NATIVE_DUAL_SPINE requires clock_spine.tcl first"
  }
  set ot_native_body [info body ot_clock_spine]
  set ot_native_needle {set ::ot_sp_nn 0}
  if {[regexp -all {set ::ot_sp_nn 0} $ot_native_body] != 1} {
    error "NATIVE_DUAL_SPINE unsupported clock_spine node initialization"
  }
  rename ot_clock_spine ot_native_original_spine
  proc ot_native_one_spine {} [string map [list $ot_native_needle {set ::ot_sp_nn $::ot_native_spine_nodebase}] $ot_native_body]
  proc ot_clock_spine {} {
    set have_port [info exists ::env(OT_SPINE_PORT)]
    if {$have_port} { set old_port $::env(OT_SPINE_PORT) }
    set ::ot_native_spine_nodebase 0
    try {
      foreach port {ck ckd} {
        set ::env(OT_SPINE_PORT) $port
        set first $::ot_native_spine_nodebase
        if {![ot_native_one_spine]} {
          error "NATIVE_DUAL_SPINE root $port did not build; no CTS fallback"
        }
        set ::ot_native_spine_nodebase $::ot_sp_nn
        puts "NATIVE_DUAL_SPINE root $port nodes $first..$::ot_native_spine_nodebase built independently"
      }
    } finally {
      if {$have_port} { set ::env(OT_SPINE_PORT) $old_port } else { unset -nocomplain ::env(OT_SPINE_PORT) }
    }
    return 1
  }
  set ::env(OT_SPINE_CTS_REST) 0
  set ::ot_native_dual_spine_installed 1
}
