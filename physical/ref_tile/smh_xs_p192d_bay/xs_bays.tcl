# smh_xs D regional bays (HBM-SMATT6 10-20, POST_TAPCELL): realises the e3bdacfca model
# (results/arch/codex_xs_regional_1020/d_control_bay_v3_subset_proof.json, all 61679 source/capture pairs
# <= 399.879 um) as two EXCLUSIVE placement fences, before PDN/GPL so global + detailed placement honour them.
#   strap   = every mapped flop u_leaf.g_sm[*].q1[*] / .q2[*] and u_leaf.r0a[*]   (exactly 519)
#   control = every mapped flop u_leaf.c3bd[*]                                  (exactly 19)
# Boxes are on the 2.16-origin 0.054 x 1.08 site/row grid, clear of every SRAM + 6.48 x 2.16 halo.  A member count
# or row-capacity mismatch refuses (the model only holds for exactly these members).  No cell is created/changed.
set xb_block [ord::get_db_block]
set xb_dbu [$xb_block getDbUnitsPerMicron]
set xb_boxes [dict create strap {189.216 153.36 208.656 172.8} control {192.888 192.24 196.992 195.48}]
set xb_expect [dict create strap 519 control 19]
set xb_members [dict create strap {} control {}]
foreach inst [$xb_block getInsts] {
  set m [$inst getMaster]
  if {[$m isBlock] || ![$m isSequential]} continue
  set n [string map [list "\\" ""] [$inst getName]]
  if {[regexp {^u_leaf\.g_sm\[[0-9]+\]\.q[12]\[} $n] || [regexp {^u_leaf\.r0a\[} $n]} {
    dict lappend xb_members strap $inst
  } elseif {[regexp {^u_leaf\.c3bd\[} $n]} {
    dict lappend xb_members control $inst
  }
}
set xb_rep [open [file join $::env(RESULTS_DIR) xs_bays.tsv] w]
puts $xb_rep "bay\tflops\tcell_area_um2\trow_capacity_um2\tfill"
foreach bay {strap control} {
  set mem [dict get $xb_members $bay]
  if {[llength $mem] != [dict get $xb_expect $bay]} {error "XS_BAY $bay owns [llength $mem] flops, model needs [dict get $xb_expect $bay]"}
  lassign [dict get $xb_boxes $bay] x0 y0 x1 y1
  set region [odb::dbRegion_create $xb_block xs_bay_$bay]
  $region setRegionType EXCLUSIVE
  odb::dbBox_create $region [expr {round($x0*$xb_dbu)}] [expr {round($y0*$xb_dbu)}] [expr {round($x1*$xb_dbu)}] [expr {round($y1*$xb_dbu)}]
  set group [odb::dbGroup_create $region xs_bay_$bay]
  set area 0.0
  foreach inst $mem {
    if {[$inst getGroup] ne "NULL" && [$inst getGroup] ne ""} {error "XS_BAY member already grouped: [$inst getName]"}
    $group addInst $inst
    set m [$inst getMaster]
    set area [expr {$area + double([$m getWidth])*[$m getHeight]/($xb_dbu*$xb_dbu)}]
  }
  set cap 0.0
  foreach row [$xb_block getRows] {
    set bb [$row getBBox]
    set rx0 [expr {[$bb xMin]/double($xb_dbu)}]; set ry0 [expr {[$bb yMin]/double($xb_dbu)}]
    set rx1 [expr {[$bb xMax]/double($xb_dbu)}]; set ry1 [expr {[$bb yMax]/double($xb_dbu)}]
    set cap [expr {$cap + max(0.0,min($x1,$rx1)-max($x0,$rx0))*max(0.0,min($y1,$ry1)-max($y0,$ry0))}]
  }
  if {$cap <= 0 || $area/$cap > 0.60} {error "XS_BAY $bay cannot fit its rows: $area / $cap"}
  puts $xb_rep "$bay\t[llength $mem]\t$area\t$cap\t[expr {$area/$cap}]"
  puts "XS_BAY_PASS $bay flops=[llength $mem] area=$area capacity=$cap fill=[expr {$area/$cap}]"
}
close $xb_rep
