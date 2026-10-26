# el1011-hbm-idx 2026-10-11: deliberate macro floorplan of the hierarchical indexer chunk: 4 systolic columns g_col[0..3]
# of 8 slices g_s[0..7], head 0 at the top (inputs enter on the north edge, the running sum leaves south).  Origins on the
# 8.64-um common multiple of the track pitches and the site (RTLMP failed: MPL-0005 / MPL-0003).
set G 8.64
proc idx_of {name tag} { if {[regexp [format {%s\\?\[(\d+)\\?\]} $tag] $name -> i]} { return $i }; return -1 }
set block [ord::get_db_block]
foreach inst [$block getInsts] {
  if {[[$inst getMaster] getName] ne "ot_hdc_v41x_idx_hslice"} { continue }
  set n [$inst getName]
  set c [idx_of $n g_col]; set h [idx_of $n g_s]
  set x [expr {4 * $G + $c * 25 * $G}]; set y [expr {8 * $G + (7 - $h) * 16 * $G}]
  place_macro -macro_name $n -location [list $x $y] -orientation R0
}
