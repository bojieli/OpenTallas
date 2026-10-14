# Leaf-local adapter for the existing clock_spine.tcl implementation.
# First distribute native GCLK. Then balance primary clocks against the actual
# measured gated subtree at its ICG input, preserving the native gate and phase.
# No clock/enable port, timing exception, or guessed insertion is introduced.
if {[info procs ot_clock_spine] eq ""} {error "TT dual spine requires the standard spine hook first"}
rename ot_clock_spine ::ot_tt_spine_native
proc ot_clock_spine {} {
  if {[ot_sp_env OT_SPINE_THROUGH_ICG 0] ne "1"} {error "TT dual spine needs the native ICG pass"}
  set ::env(OT_SPINE_CTS_REST) 0
  # The primary branch has its own balanced spine below. Its FFs and the
  # ICG therefore retain the original GPL data placement instead of being
  # packed at an unbuffered port. Use the standard builder with relocation
  # disabled; all geometry, sink grouping, and measured balancing are shared.
  set original [info body ::ot_tt_spine_native]
  set move {if {![[$i getMaster] isBlock] && [lsearch -exact $::ot_sp_icg_move $i] < 0} { lappend ::ot_sp_icg_move $i }}
  if {[string first $move $original] < 0} {error "TT primary relocation dependency changed"}
  proc ::ot_tt_spine_native {} [string map [list $move {if {0} { lappend ::ot_sp_icg_move $i }}] $original]
  try {
    if {![::ot_tt_spine_native]} {error "TT native GCLK spine was not built"}
  } finally {proc ::ot_tt_spine_native {} $original}
  set gated [ot_sp_leaf_arrivals]
  set gate $::ot_sp_icg
  set master [[$gate getMaster] getName]
  set cgpin [get_pins -quiet "[$gate getName]/CLK"]
  if {[llength $cgpin] != 1} {error "TT native ICG CLK pin missing"}
  set ck [get_property $cgpin arrival_max_rise]
  set latest [tcl::mathfunc::max {*}[dict values $gated]]
  set insertion [expr {$latest - $ck}]
  if {$insertion <= 0 || $insertion > 5000} {error "TT invalid measured native subtree insertion $insertion"}
  puts "TT_DUAL_SPINE gated latest $latest ICG_CLK $ck measured subtree $insertion ps"
  # Every gated sink is behind its dedicated spine. Permit primary reconnection
  # before the second spine fixes its completed clock connections.
  set block [ord::get_db_block]
  set port [$block findBTerm [ot_sp_env OT_SPINE_PORT clk]]
  set primary [$port getNet]
  $primary setDoNotTouch 0
  set primary_insts {}
  foreach it [$primary getITerms] {
    if {[$it getIoType] ne "INPUT"} continue
    set i [$it getInst]
    $i setDoNotTouch 0
    lappend primary_insts $i
  }
  # Separate names let the same measured placement/balance procedures build
  # both trees. Fail loudly if a standard implementation dependency changes.
  set saved [dict create]
  foreach p {ot_sp_emit ot_sp_checkpoint ot_sp_restore ot_sp_pad} {
    set body [info body $p]
    if {[string first clkbuf_sp_ $body] < 0} {error "TT spine dependency $p changed"}
    dict set saved $p $body
    proc $p [info args $p] [string map {clkbuf_sp_ clkbuf_tt_primary_} $body]
  }
  set native [info body ::ot_tt_spine_native]
  set old {&& [[[$it getInst] getMaster] isBlock]}
  set new {&& ([[[$it getInst] getMaster] isBlock] || [string match ICG* [[[$it getInst] getMaster] getName]])}
  if {[string first $old $native] < 0} {error "TT macro-leaf dependency changed"}
  proc ::ot_tt_spine_native {} [string map [list $old $new] $native]
  set ::env(OT_SPINE_THROUGH_ICG) 0
  set ::env(OT_SPINE_MACRO_LEAF) 1
  set ::env(OT_SPINE_SYM) 1
  dict set ::ot_ref_child_ins $master $insertion
  try {
    if {![::ot_tt_spine_native]} {error "TT primary spine was not built"}
    foreach i $primary_insts {
      if {[string match ICG* [[$i getMaster] getName]]} {
        $i setDoNotTouch 1
      } else {
        $i setDoNotTouch 0
        if {![[$i getMaster] isBlock]} {$i setPlacementStatus PLACED}
      }
    }
    puts "TT_DUAL_SPINE complete: independent primary and native-gated local trees"
  } finally {
    dict for {p body} $saved {proc $p [info args $p] $body}
    proc ::ot_tt_spine_native {} $native
  }
  return 1
}
