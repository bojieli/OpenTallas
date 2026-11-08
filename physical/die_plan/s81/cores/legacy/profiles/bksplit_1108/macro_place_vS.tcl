# DIE-S81-80 11-08 bksel SPLIT parent vS (vI macro_place + the P child): P (ot_s81ph_hq_pk2, 194.4 x 194.4, W inputs /
# E outputs) in the middle band between the hist rows; u_fq (5 x 32x128) compact at the top right beside mem2 and the
# lane pins; u_ofq (5 x 32x128) stacked in the W column beside the t_o face.  hist banks and mem2 unchanged from vI.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach {master sites} {ot_sram_1r1w_128x256_m1_r2c2_p192_mir {{414.72 43.2 R0} {414.72 172.8 R0} {414.72 345.6 R0} {535.68 43.2 R0} {535.68 172.8 R0} {535.68 345.6 R0}} ot_sram_1r1w_32x128_m1_p192_rc {{414.72 475.2 R0} {474.48 475.2 R0} {534.24 475.2 R0} {414.72 529.2 R0} {474.48 529.2 R0} {17.28 183.6 R0} {17.28 231.12 R0} {17.28 278.64 R0} {17.28 326.16 R0} {17.28 373.68 R0}} ot_s81ph_native_sel_hist_bank {{17.28 25.92 R0} {112.32 25.92 R0} {216 25.92 R0} {311.04 25.92 R0} {17.28 120.96 R0} {112.32 120.96 R0} {216 120.96 R0} {311.04 120.96 R0} {17.28 423.36 R0} {112.32 423.36 R0} {216 423.36 R0} {311.04 423.36 R0} {17.28 518.4 R0} {112.32 518.4 R0} {216 518.4 R0} {311.04 518.4 R0}} ot_s81ph_hq_pk2 {{172.8 201.96 R0}}} {
  set hit {}
  foreach i [$b getInsts] { if {[[$i getMaster] getName] eq $master} { lappend hit $i } }
  if {[llength $hit] != [llength $sites]} { error "legacy macro_place: [llength $hit] instances of $master (want [llength $sites])" }
  set hit [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $hit]
  foreach i $hit s $sites {
    lassign $s x y orient
    $i setOrient $orient
    $i setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]
    $i setPlacementStatus FIRM
    puts "LEGACY place: [$i getName] $master at $x $y $orient"
  }
}
