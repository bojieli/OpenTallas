# PRE_DETAIL_PLACE: deterministic delay on the eight epoch observer D pins.
# r5b exact CTS 211a020c8: wg1[2] FF hold -48.174 ps, 10940 iterations,
# 20471 buffers in chunk 1. The same tree closes only after chunk restart.
# Three HB4 stages (~111 ps FF) preserve the Gray value and sampling edge.
# BUF stages stay resizable; only local HB input nets and HB cells are protected.
set gh_blk [ord::get_db_block]
set gh_db [ord::get_db]
set gh_hb [$gh_db findMaster HB4xp67_ASAP7_75t_R]
set gh_bf [$gh_db findMaster BUFx4f_ASAP7_75t_R]
if {$gh_hb eq "NULL" || $gh_bf eq "NULL"} { error "CFIFO_GRAY_HOLD missing masters" }
set gh_targets {}
foreach gh_i [$gh_blk getInsts] {
  # OpenDB stores escaped bus brackets; canonicalize before matching the eight flops.
  regsub -all {\\} [$gh_i getName] {} gh_canonical
  if {[regexp {^u_x2?\.u_cross\.wg1\[[0-9]+\].*}  $gh_canonical]} {
    set gh_d [$gh_i findITerm D]
    if {$gh_d ne "NULL" && [$gh_d getNet] ne "NULL"} { lappend gh_targets $gh_d }
  }
}
if {[llength $gh_targets] != 8} { error "CFIFO_GRAY_HOLD expected 8 D pins, got [llength $gh_targets]" }
set gh_n 0
foreach gh_d $gh_targets {
  set gh_cur [$gh_d getNet]
  lassign [[$gh_d getInst] getLocation] gh_x gh_y
  $gh_d disconnect
  foreach gh_m [list $gh_bf $gh_hb $gh_bf $gh_hb $gh_bf $gh_hb $gh_bf] {
    set gh_hold [expr {$gh_m eq $gh_hb}]
    set gh_name [format "ot_gray_%s_%02d" [expr {$gh_hold ? "hold" : "drv"}] $gh_n]
    set gh_c [odb::dbInst_create $gh_blk $gh_m $gh_name]
    set gh_net [odb::dbNet_create $gh_blk ${gh_name}_q]
    [$gh_c findITerm A] connect $gh_cur
    [$gh_c findITerm Y] connect $gh_net
    $gh_c setOrient R0
    $gh_c setLocation $gh_x $gh_y
    $gh_c setPlacementStatus PLACED
    if {$gh_hold} { $gh_cur setDoNotTouch 1 }
    set gh_cur $gh_net
    incr gh_n
  }
  $gh_d connect $gh_cur
}
set_dont_touch [get_cells ot_gray_hold_*]
puts "CFIFO_GRAY_HOLD: 8 observer D pins, 24 protected HB4, 32 resizable drivers; zero cycles"
