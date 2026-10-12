# fe-push-qwen-1010 (2026-10-10): fixed macro placement for ot_qfd_sp_vector_memory_bv USE_MACRO=1 (replaces RTLMP: every
# bv route died at floorplan with MPL-0003 "no valid tilings for mixed cluster").  128 x ot_sram_1r1w_256x256 (172.8 x
# 41.04, copy 0: 64 banks x lo/hi, the x beats) + 96 x ot_sram_1r1w_1024x256 (174.744 x 70.47, the 3 SU replica copies:
# 16 banks x lo/hi each).  Four (>= 900 um outline) or three (777.6) columns off the W / E faces (x_q / rb_data pins and their capture flops), equal
# channels between columns; in each column the SU copies sit at the bottom (the SU port face) and copy 0 above, every
# macro pair (lo, hi) adjacent, the remaining height spread evenly as std-cell channels (>= 50 um at 6,220.8 um).
set b [ord::get_db_block]
set die [$b getDieArea]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set W [expr {double([$die xMax]) / $dbu}]
set H [expr {double([$die yMax]) / $dbu}]
set small {}; set big {}
foreach i [$b getInsts] {
  set m [$i getMaster]
  if {![$m isBlock]} continue
  set n [$m getName]
  if {[string match *256x256* $n]} { lappend small [$i getName] } elseif {[string match *1024x256* $n]} { lappend big [$i getName] } else { error "vm_bv_place: unexpected macro $n" }
}
set small [lsort -dictionary $small]; set big [lsort -dictionary $big]
if {[llength $small] != 128 || [llength $big] != 96} { error "vm_bv_place expects 128 + 96 macros: [llength $small] + [llength $big]" }
# 4 columns 100 um off the faces when the outline is >= 900 um wide (1,036.8), else 3 columns 60 um off (777.6 slot)
if {$W >= 900.0} { set NC 4; set XM 100.0 } else { set NC 3; set XM 60.0 }
set MW 174.744; set YM 120.0
set gx [expr {($W - 2 * $XM - $NC * $MW) / ($NC - 1)}]
if {$gx < 20.0} { error "vm_bv_place: column channel $gx um < 20 um (outline too narrow)" }
set nb [expr {([llength $big] + $NC - 1) / $NC}]; set ns [expr {([llength $small] + $NC - 1) / $NC}]
set used [expr {$nb * 70.47 + $ns * 41.04}]
set gy [expr {($H - 2 * $YM - $used) / ($nb + $ns - 1)}]
if {$gy < 10.0} { error "vm_bv_place: row channel $gy um < 10 um" }
puts "vm_bv_place: columns $NC channel x [format %.2f $gx] um, up to [expr {$nb + $ns}] rows, channel y [format %.2f $gy] um"
set placed 0
for {set c 0} {$c < $NC} {incr c} {
  set x [expr {floor(($XM + $c * ($MW + $gx)) / 0.216) * 0.216}]
  set y $YM
  for {set k [expr {$c * $nb}]} {$k < min(($c + 1) * $nb, [llength $big])} {incr k} {
    place_macro -macro_name [lindex $big $k] -location [list $x [expr {floor($y / 0.27) * 0.27}]] -orientation R0
    set y [expr {$y + 70.47 + $gy}]; incr placed
  }
  for {set k [expr {$c * $ns}]} {$k < min(($c + 1) * $ns, [llength $small])} {incr k} {
    place_macro -macro_name [lindex $small $k] -location [list $x [expr {floor($y / 0.27) * 0.27}]] -orientation R0
    set y [expr {$y + 41.04 + $gy}]; incr placed
  }
}
if {$placed != 224} { error "vm_bv_place placed $placed of 224" }
