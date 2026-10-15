# el1011-hbm-idx 2026-10-11 r6: macro floorplan of the w8 hard cluster ot_hgi_idx_topk_w8_cluster (hub glue + 8 hard heap
# tiles).  Lane h owns a 311.04-um stripe (36 x 8.64; c = h % 4): tiles t0..t3 along the SOUTH edge, t4..t7 along the NORTH
# edge (each 25.9 um inside its stripe and the die edge), each lane's reverse-buffer SRAM in the middle band one 25-um
# channel inside its own tile row, and the hub logic (front end, lane FIFOs, status tree, merge tree, result skid) in the
# band between the two SRAM rows: every tile seam is tile pin flop / tile output reg <-> hub flop over <= ~400 um.
# Origins on the 8.64-um common multiple of the M4..M7 pitches and the site (R0 pins stay on track; no RTLMP: MPL-0005).
set G 8.64
proc idx_of {name tag} { if {[regexp [format {%s\\?\[(\d+)\\?\]} $tag] $name -> i]} { return $i }; return -1 }
proc lane_of {name} { if {[regexp {u_t(\d)} $name -> i]} { return $i }; return [idx_of $name g_h] }
set block [ord::get_db_block]
set dh [ord::dbu_to_microns [[$block getDieArea] yMax]]
set yt1 [expr {floor(($dh - 3 * $G - 260.0) / $G) * $G}]           ;# north tile row
set ys1 [expr {floor(($yt1 - 3 * $G - 70.47) / $G) * $G}]          ;# north lanes' SRAMs
foreach inst [$block getInsts] {
  set m [[$inst getMaster] getName]
  set n [$inst getName]
  if {$m eq "ot_hgi_topk_heap_tile"} {
    set h [lane_of $n]; set c [expr {$h % 4}]; set r [expr {$h / 4}]
    place_macro -macro_name $n -location [list [expr {3 * $G + $c * 36 * $G}] [expr {$r == 0 ? 3 * $G : $yt1}]] -orientation R0
  } elseif {[string match "ot_sram_1r1w_1024x256*" $m]} {
    set h [idx_of $n g_h]; set c [expr {$h % 4}]; set r [expr {$h / 4}]
    place_macro -macro_name $n -location [list [expr {8 * $G + $c * 36 * $G}] [expr {$r == 0 ? 36 * $G : $ys1}]] -orientation R0
  }
}
