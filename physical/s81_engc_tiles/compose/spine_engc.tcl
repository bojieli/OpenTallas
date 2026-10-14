# Engram diagnostic spine: align functional positive-edge boundary means,
# not fall-edge ETM maxima or hand offsets. TT route geometry is built with
# actual TT references; FF/SS delivery must be measured independently.
# External source/reset phase remains unbound; this is not qualification.
source /src/physical/common_flow/clock_spine.tcl
source /src/physical/s81_engc_tiles/compose/child_clock_refs.tcl
set ::ot_engc_ck_target $::ot_engc_boundary_tt
set ::ot_engc_ck_offset [dict create u_win 0 u_io 0 u_ws 0 u_pb1 0 u_pb0 0 u_pb2 0 u_lkp 0 u_sink 0]
proc ot_sp_leaf_arrivals {} {
  ot_engc_attach_local_clocks
  estimate_parasitics -placement
  sta::find_timing_paths -path_delay max -group_path_count 1
  set a [dict create]
  dict for {n net} $::ot_sp_leafnet {
    set v 0.0
    foreach pin [get_pins -quiet -of_objects [get_nets -quiet [$net getName]] -filter "direction==input"] {
      set x [get_property $pin arrival_max_rise]
      if {$x eq "" || $x eq "INF" || $x eq "-INF"} continue
      set c [get_cells -quiet -of_objects $pin]
      if {[llength $c]} {
        set m [get_full_name $c]
        if {[dict exists $::ot_engc_ck_target $m]} { set x [expr {$x + [dict get $::ot_engc_ck_target $m] - [dict get $::ot_engc_ck_offset $m]}] }
      }
      if {$x > $v} { set v $x }
    }
    dict set a $n $v
  }
  return $a
}
puts "ENGC spine: per-child targets $::ot_engc_ck_target offsets $::ot_engc_ck_offset"
# The reset conditioner must see the SAME branch as the macro clock pin.
# Temporarily remove its clocks from spine binning (which intentionally gives
# ordinary top flops separate leaves), then reconnect to the child's leaf net.
rename clock_tree_synthesis ot_engc_spine_cts
proc clock_tree_synthesis {args} {
  set b [ord::get_db_block]; set reconnect {}
  foreach child {win io ws pb1 pb0 pb2 lkp sink} {
    foreach i [$b getInsts] {
      set belongs [string match *u_rst_${child}* [$i getName]]
      if {!$belongs} continue
      foreach it [$i getITerms] {
        set mt [$it getMTerm]
        if {[$mt getSigType] ne "CLOCK" && [$mt getName] ni {CLK CK CP}} continue
        lappend reconnect [list $child $it]
        $it disconnect
      }
    }
  }
  if {[llength $reconnect] != 16} { error "ENGC reset clocks missing: [llength $reconnect] !=16" }
  set ::ot_engc_pending_clocks $reconnect
  set ::ot_engc_clocks_attached 0
  ot_engc_spine_cts {*}$args
  if {!$::ot_engc_clocks_attached} { error "ENGC local clocks were not loaded during spine balancing" }
  estimate_parasitics -placement
}
# Called on the FIRST arrival measurement: the tree exists, and the macro-only
# bins are fixed. Attach local flop loads BEFORE padding/equalisation, so clock
# delays include those loads rather than changing after the balance was solved.
proc ot_engc_attach_local_clocks {} {
  if {![info exists ::ot_engc_pending_clocks] || $::ot_engc_clocks_attached} { return }
  set b [ord::get_db_block]
  foreach row $::ot_engc_pending_clocks {
    lassign $row child it
    set macro [$b findInst u_$child]
    set net [[$macro findITerm ck] getNet]
    if {$net eq "NULL"} { error "ENGC macro clock disconnected: $child" }
    # Spine completion protects its leaf nets; open only this branch while
    # adding the local reset/status clocks, then restore the same protection.
    $net setDoNotTouch 0
    [$it getInst] setDoNotTouch 0
    $it connect $net
    # A spine rollback must restore these local clocks with the same leaf.
    dict for {leaf leafnet} $::ot_sp_leafnet {
      if {$leafnet ne $net} continue
      if {[lsearch -exact [dict get $::ot_sp_members $leaf] $it] < 0} {
        dict lappend ::ot_sp_members $leaf $it
        dict incr ::ot_sp_cnt $leaf 1
      }
    }
    [$it getInst] setDoNotTouch 1
    $net setDoNotTouch 1
    puts "ENGC local clock [[$it getInst] getName]/[[$it getMTerm] getName] = u_${child}/ck net [$net getName]"
  }
  set ::ot_engc_clocks_attached 1
}
