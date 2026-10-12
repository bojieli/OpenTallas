# el1011-hbm-idx 2026-10-11 r6: deliberate macro floorplan of the hierarchical 8-wide IDX.TOPK engine (no RTLMP: MPL-0005
# could not track-align the hardened tiles' upper-layer pins).  Every origin is a multiple of 8.64 um = the common multiple
# of the M4..M7 track pitches and the placement site, so every R0 macro pin stays on track.
# HORIZONTAL SPINE (r6; r5 put both tile rows at the bottom and the logic band 800 um above row 0): tile row 0 (lanes 0..3)
# along the bottom edge, tile row 1 (lanes 4..7) along the top edge, each lane's reverse-buffer SRAM in the spine directly
# against its own tile row, and the front end / status tree / merge tree / output in the spine between the two SRAM rows.
# Lane order follows the merge tree (pairs 0-1, 2-3 adjacent; level 2 = row 0 vs row 1 across the spine).  Pins (cfg):
# command + scores on the west edge, results on the east edge, both at spine height.
set G 8.64
proc idx_of {name tag} { if {[regexp [format {%s\\?\[(\d+)\\?\]} $tag] $name -> i]} { return $i }; return -1 }
set block [ord::get_db_block]
set dh [ord::dbu_to_microns [[$block getDieArea] yMax]]
set y1 [expr {floor(($dh - 3 * $G - 260.0) / $G) * $G}]           ;# tile row 1 origin (top edge, 25.9-um channel)
set ys1 [expr {floor(($y1 - 3 * $G - 70.47) / $G) * $G}]          ;# row-1 lanes' SRAMs, one channel under row 1
foreach inst [$block getInsts] {
  set m [[$inst getMaster] getName]
  set n [$inst getName]
  if {$m eq "ot_hgi_topk_heap_tile"} {
    set h [idx_of $n g_h]; set c [expr {$h % 4}]; set r [expr {$h / 4}]
    set x [expr {6 * $G + $c * 36 * $G}]; set y [expr {$r == 0 ? 3 * $G : $y1}]
    place_macro -macro_name $n -location [list $x $y] -orientation R0
  } elseif {[string match "ot_sram_1r1w_1024x256*" $m]} {
    set h [idx_of $n g_h]; set c [expr {$h % 4}]; set r [expr {$h / 4}]
    set x [expr {18 * $G + $c * 36 * $G}]; set y [expr {$r == 0 ? 36 * $G : $ys1}]
    place_macro -macro_name $n -location [list $x $y] -orientation R0
  }
}
