# DIE-QC-58A: planned HB4 hold pads on zero-logic shift-chain pairs (owner 10-27 "zero-logic seam hold -> HB4"),
# applied right after clock_tree_synthesis (after the B3 hook when both are sourced), before the structural hold gate.
# OT_ZL_PAT  : capture flop patterns (get_cells) whose D is fed directly (buffers only) by a flop Q
# OT_ZL_TT_PS: pad each such D until its TT hold slack >= this (ps); OT_ZL_MAX: max HB4 per pin (default 4)
proc ot_zl_pad {} {
  if {![info exists ::env(OT_ZL_PAT)]} return
  set want [expr {[info exists ::env(OT_ZL_TT_PS)] ? $::env(OT_ZL_TT_PS) : 0.0}]
  set mx [expr {[info exists ::env(OT_ZL_MAX)] ? $::env(OT_ZL_MAX) : 4}]
  set hb [get_lib_cells -quiet */HB4xp67_ASAP7_75t_R]
  unset_dont_use $hb
  catch {estimate_parasitics -placement}
  set eps {}
  foreach pat $::env(OT_ZL_PAT) {
    foreach c [get_cells -quiet $pat] {
      if {![regexp {DFF} [get_property $c ref_name]]} continue
      set d [get_pins -quiet [get_full_name $c]/D]
      if {$d eq ""} continue
      lappend eps [get_full_name $d]
    }
  }
  # zero-logic test + slack collected first (no path objects survive a netlist edit)
  set todo {}
  foreach ep $eps {
    set p [lindex [find_timing_paths -path_delay min -to [get_pins $ep] -group_path_count 1] 0]
    if {$p eq ""} continue
    set s [get_property $p slack]
    if {$s >= $want} continue
    set zl 1
    foreach pt [get_property $p points] {
      if {[catch {get_property $pt pin} pin] || $pin eq "" || $pin eq "NULL"} continue
      if {[catch {get_cells -of_objects $pin} cell] || $cell eq ""} continue
      set rn [get_property $cell ref_name]
      if {[regexp {DFF} $rn]} continue
      if {![regexp {^(BUF|HB|INV)} $rn]} { set zl 0; break }
    }
    if {$zl} { lappend todo [list $ep $s] }
  }
  set n 0; set tot 0; set ws 1e9
  set blk [ord::get_db_block]
  foreach t $todo {
    lassign $t ep s
    set dbi [sta::sta_to_db_inst [get_cells -of_objects [get_pins $ep]]]
    set bb [$dbi getBBox]; set u [$blk getDbUnitsPerMicron]
    set xy [list [expr {double([$bb xMin]) / $u}] [expr {double([$bb yMin]) / $u}]]
    set j 0
    while {$s < $want && $j < $mx} {
      set nm ot_zl_hp${n}_$j
      insert_buffer -buffer_cell HB4xp67_ASAP7_75t_R -load_pins [list [get_pins $ep]] -location $xy -buffer_name $nm
      incr j; incr tot
      catch {estimate_parasitics -placement}
      set s [get_property [lindex [find_timing_paths -path_delay min -to [get_pins $ep] -group_path_count 1] 0] slack]
    }
    if {$s < $ws} { set ws $s }
    incr n
  }
  set_dont_use $hb
  puts [format "OT_ZL_PAD: %d zero-logic endpoints below %.1f ps TT hold (of %d matched D pins), %d HB4, worst TT hold after %.1f" $n $want [llength $eps] $tot [expr {$n ? $ws : 0}]]
}
if {[info commands ot_zl_cts_inner] eq "" && [info commands clock_tree_synthesis] ne ""} {
  rename clock_tree_synthesis ot_zl_cts_inner
  proc clock_tree_synthesis {args} { set r [ot_zl_cts_inner {*}$args]; ot_zl_pad; return $r }
}
