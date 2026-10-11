# el1011-hbm-idx 2026-10-11: deliberate macro floorplan of the hierarchical 8-wide IDX.TOPK engine (no RTLMP: MPL-0005
# could not track-align the hardened tiles' upper-layer pins).  Every origin is a multiple of 8.64 um = the common multiple
# of the M4..M7 track pitches and the placement site, so every R0 macro pin stays on track.  Rows: heap tiles g_h[0..3],
# g_h[4..7]; then reverse buffers g_rb[0..3], g_rb[4..7] under their heaps; front end / merge logic in the remaining band.
set G 8.64
proc idx_of {name tag} { if {[regexp [format {%s\\?\[(\d+)\\?\]} $tag] $name -> i]} { return $i }; return -1 }
set block [ord::get_db_block]
foreach inst [$block getInsts] {
  set m [[$inst getMaster] getName]
  set n [$inst getName]
  if {$m eq "ot_hgi_topk_heap_tile"} {
    set h [idx_of $n g_h]; set c [expr {$h % 4}]; set r [expr {$h / 4}]
    set x [expr {6 * $G + $c * 36 * $G}]; set y [expr {3 * $G + $r * 36 * $G}]
    place_macro -macro_name $n -location [list $x $y] -orientation R0
  } elseif {[string match "ot_sram_1r1w_1024x256*" $m]} {
    set h [idx_of $n g_rb]; set c [expr {$h % 4}]; set r [expr {$h / 4}]
    set x [expr {6 * $G + $c * 36 * $G}]; set y [expr {72 * $G + $r * 12 * $G}]
    place_macro -macro_name $n -location [list $x $y] -orientation R0
  }
}
