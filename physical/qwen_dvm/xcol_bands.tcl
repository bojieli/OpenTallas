# Flat DVM column (qfd_xcol_e/w, 64.8 x 1434.24): fence each source block into its natural band so every
# clock root (ck0 head, ck1..4 N leaves, ck5..8 S leaves) owns a compact 136-345 um region.  Bands follow the
# column plan: S leaves j=0..3 below the head (j=0 nearest), head 544.32..889.92, N leaves above.  Runs before
# the pin flops are fixed; all head-row pins lie inside the head band.  ABC leaves combinational cells anonymous:
# only named (sequential) cells are fenced; their logic follows by wirelength.
set xb_blk [ord::get_db_block]
set xb_dbu [$xb_blk getDbUnitsPerMicron]
set xb_w [expr {[[$xb_blk getDieArea] xMax]}]
set xb_lh 136.08; set xb_h0 544.32; set xb_h1 889.92
proc xb_box {name y0 y1} {
  global xb_blk xb_dbu xb_w
  set r [odb::dbRegion_create $xb_blk "dvm_band_$name"]
  odb::dbBox_create $r 0 [expr {round($y0*$xb_dbu)}] $xb_w [expr {round($y1*$xb_dbu)}]
  return [odb::dbGroup_create $r "dvm_band_grp_$name"]
}
set xb_g(head) [xb_box head $xb_h0 $xb_h1]
for {set j 0} {$j < 4} {incr j} {
  set xb_g(n$j) [xb_box n$j [expr {$xb_h1 + $j*$xb_lh}] [expr {$xb_h1 + ($j+1)*$xb_lh}]]
  set xb_g(s$j) [xb_box s$j [expr {$xb_h0 - ($j+1)*$xb_lh}] [expr {$xb_h0 - $j*$xb_lh}]]
}
array set xb_n {}
foreach i [$xb_blk getInsts] {
  if {[[$i getMaster] isBlock] || [[$i getMaster] getType] ne "CORE"} continue
  regsub -all {\\} [$i getName] {} n
  if {[regexp {g_ch\[([01])\][./]g_leaf\[([0-3])\][./]u_leaf} $n -> h j]} {
    set k [expr {$h ? "s$j" : "n$j"}]
  } elseif {[regexp {g_h[ew][./]u_h} $n]} {
    set k head
  } else { continue }
  if {[$i getGroup] ne "NULL"} continue
  $xb_g($k) addInst $i
  incr xb_n($k)
}
foreach k [lsort [array names xb_g]] {
  if {![info exists xb_n($k)] || $xb_n($k) < 1000} { error "XCOL_BANDS: band $k got [expr {[info exists xb_n($k)] ? $xb_n($k) : 0}] cells" }
  puts "XCOL_BANDS $k cells=$xb_n($k)"
}
