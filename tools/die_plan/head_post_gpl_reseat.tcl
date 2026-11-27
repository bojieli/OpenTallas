# Run the existing forest hook before correcting long detours on short native paths.
source /work/forest_recluster.tcl

# Load the stock path functions for this hook without running the ordinary
# subsequently invoked PRE_RESIZE gate before the correction.
set ot_reseat_has_mode [info exists ::env(OT_PLACE_WIRE_RATIO)]
if {$ot_reseat_has_mode} {set ot_reseat_old_mode $::env(OT_PLACE_WIRE_RATIO)}
set ::env(OT_PLACE_WIRE_RATIO) off
try {
  source /work/place_wire_ratio.tcl
} finally {
  if {$ot_reseat_has_mode} {
    set ::env(OT_PLACE_WIRE_RATIO) $ot_reseat_old_mode
  } else {
    unset ::env(OT_PLACE_WIRE_RATIO)
  }
}

proc head_wire_endpoint {block endpoint} {
  set slash [string last / $endpoint]
  set inst [$block findInst [string range $endpoint 0 [expr {$slash - 1}]]]
  if {$inst eq "NULL"} { return NULL }
  set name [string range $endpoint [expr {$slash + 1}] end]
  foreach pin [$inst getITerms] {
    if {[[$pin getMTerm] getName] eq $name} { return $pin }
  }
  return NULL
}

proc head_wire_buffer_chain {block path} {
  if {![regexp {^(.*)->(.*)$} $path _ launch capture]} { return {} }
  set first [head_wire_endpoint $block $launch]
  set final [head_wire_endpoint $block $capture]
  if {$first eq "NULL" || $final eq "NULL" || [$first getNet] eq "NULL"} { return {} }
  set stack [list [list [$first getNet] {}]]
  set seen {}
  while {[llength $stack]} {
    lassign [lindex $stack end] net chain
    set stack [lrange $stack 0 end-1]
    if {[dict exists $seen $net]} { continue }
    dict set seen $net 1
    foreach pin [$net getITerms] {
      if {$pin eq $final} { return $chain }
      if {![$pin isInputSignal] || [llength $chain] >= 64} { continue }
      set inst [$pin getInst]
      set master [[$inst getMaster] getName]
      if {![pwr_buf $master]} { continue }
      foreach out [$inst getITerms] {
        if {![$out isOutputSignal] || [$out getNet] eq "NULL"} { continue }
          set cell [list [$inst getName] $master [$inst getPlacementStatus]]
        lappend stack [list [$out getNet] [concat $chain [list $cell]]]
      }
    }
  }
  return {}
}


# Keep existing transparent cells on the short registered connection selected
# by their actual native connectivity. Do not edit the netlist.
proc hp_pre_resize_paths {path} {
  global fr_blk
  if {![regexp {^(.*)->(.*)$} $path _ start end]} {return {}}
  set src [head_wire_endpoint $fr_blk $start]
  set dst [head_wire_endpoint $fr_blk $end]
  if {$src eq "NULL" || $dst eq "NULL"} {return {}}
  set chain [head_wire_buffer_chain $fr_blk $path]
  return [list $src $dst $chain]
}
proc hp_middle {values} {
  set values [lsort -real $values]
  return [lindex $values [expr {[llength $values]/2}]]
}
proc hp_move_detours {} {
  global fr_blk fr_dbu
  set paths [pwr_paths]
  set before [pwr_eval $paths 400 3]
  set offers {}
  set sources {}
  set affected {}
  foreach row $before {
    lassign $row path direct built ratio
    if {$direct > 405} {continue}
    lassign [hp_pre_resize_paths $path] src dst chain
    if {![llength $chain]} {continue}
    set source_inst [$src getInst]
    dict set sources [string range $path 0 [expr {[string first "->" $path]-1}]] 1
    foreach node $chain {
      lassign $node name master status
      set i [$fr_blk findInst $name]
      if {$i eq "NULL"} {continue}
      if {$status in {FIRM LOCKED FIXED COVER}} {
        # Only the typed reader-START output inversion can be relocated out
        # of fixed seats by this hook. Other documented seats retain priority.
        if {![string match INV* $master] || ![regexp {^u_cland_reader_start_} [$source_inst getName]]} {continue}
      }
      dict set affected $name $i
    }
  }
  foreach row $paths {
    lassign $row path direct built
    set start [string range $path 0 [expr {[string first "->" $path]-1}]]
    if {![dict exists $sources $start]} {continue}
    lassign [hp_pre_resize_paths $path] src dst chain
    if {![llength $chain]} {continue}
    lassign [pwr_pt $src $fr_dbu] x0 y0
    lassign [pwr_pt $dst $fr_dbu] x1 y1
    set stages [expr {double([llength $chain]+1)}]
    set k 0
    foreach node $chain {
      incr k
      set name [lindex $node 0]
      if {![dict exists $affected $name]} {continue}
      set frac [expr {$k/$stages}]
      set x [expr {round(($x0+$frac*($x1-$x0))*$fr_dbu)}]
      set y [expr {round(($y0+$frac*($y1-$y0))*$fr_dbu)}]
      dict lappend offers $name [list [dict get $affected $name] $x $y \
        [expr {round(min($x0,$x1)*$fr_dbu)}] [expr {round(max($x0,$x1)*$fr_dbu)}] \
        [expr {round(min($y0,$y1)*$fr_dbu)}] [expr {round(max($y0,$y1)*$fr_dbu)}]]
    }
  }
  set moved 0
  set fh [open $::env(RESULTS_DIR)/polarity_detour_moves.tsv w]
  puts $fh "instance\tpaths\told_x\told_y\tnew_x\tnew_y"
  dict for {name choices} $offers {
    set i [lindex $choices 0 0]
    lassign [$i getLocation] x y
    set px [hp_middle [lmap row $choices {lindex $row 1}]]
    set py [hp_middle [lmap row $choices {lindex $row 2}]]
    set lo_x [tcl::mathfunc::max {*}[lmap row $choices {lindex $row 3}]]
    set hi_x [tcl::mathfunc::min {*}[lmap row $choices {lindex $row 4}]]
    set lo_y [tcl::mathfunc::max {*}[lmap row $choices {lindex $row 5}]]
    set hi_y [tcl::mathfunc::min {*}[lmap row $choices {lindex $row 6}]]
    if {$lo_x <= $hi_x} {set px [expr {max($lo_x,min($hi_x,$px))}]}
    if {$lo_y <= $hi_y} {set py [expr {max($lo_y,min($hi_y,$py))}]}
    if {[$i getPlacementStatus] in {FIRM LOCKED FIXED COVER}} { $i setPlacementStatus PLACED }
    lassign [fr_put $i $px $py] nx ny
    if {$nx == $x && $ny == $y} {continue}
    incr moved
    puts $fh [join [list $name [llength $choices] $x $y $nx $ny] "\t"]
  }
  close $fh
  set after [pwr_eval [pwr_paths] 400 3]
  set fh [open $::env(RESULTS_DIR)/post_detour_correction.tsv w]
  puts $fh "path\tdirect_um\tlength_um\tratio"
  foreach row $after {puts $fh [join $row "\t"]}
  close $fh
  puts "HEAD_POSITIVE_WIRE_DETOUR before=[llength $before] after=[llength $after] cells_moved=$moved"
}

hp_move_detours
