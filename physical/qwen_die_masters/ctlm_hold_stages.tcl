# PRE_GLOBAL_PLACE hook, qfd_tt_ctlm_i fp{a,b}_amh (el1011-q-seq 2026-10-12; coordinator-approved deterministic hold stages,
# no ECO loop).  Evidence: fp{a,b}sc-43229d70e routed TT +40.77 / +60.87 (setup closed), FF -31.52 / -45.84 =
#   R2O -31.52 / -45.84 on flop-driven outputs (station Q -> pin; TT slack of those outputs >= +342 ps),
#   R2R -28.99 / -19.22: zero-wire 2-4-level pairs whose launch and capture sit on DIFFERENT cg_pushdown clones of
#     u_me_cg (e.g. g_alvl c -> atop: cgpd62 469 ps vs cgpd77 533 ps at FF, data 45-60 ps); TT setup on every failing
#     D pin >= +100 ps (the classes below; b_off and argmax c -> c are excluded: pattern-level TT < +100),
#   I2R at the routed IO ref is +51.36 / +38.53 (the -127.7 window is the CTS-stage estimate); input capture flops
#     have TT >= +193 ps once p_am is pin-registered (AMI, 40964f285).
# Stages (all dont_touch, built before GPL; delay cells are ASAP7 HB4xp67, ~37 ps FF / ~50 ps TT each):
#   1. io_flop_at_pins.tcl (unchanged): pin flops FIRM at their pins.
#   2. INPUT: port -> HB4 -> BUFx4f -> its single capture flop D; pair FIRM at the pin (vm8 181753c60 pattern: the weak
#      hold cell sees one local load, the strong BUF drives the wire and stays resizable).
#   3. OUTPUT: driver net -> HB4 -> HB4 -> BUFx4f -> port, all FIRM at the pin, for outputs driven by a flop (directly
#      or through BUF / INV); tie / combinational outputs untouched.
#   4. R2R: one HB4 in front of each D pin of the listed capture classes, seeded at the capture flop.
# ctlm_hold_release.tcl (PRE_DETAIL_PLACE) returns the FIRM cells and the pin flops to PLACED for DPL.
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
# ORFS sources step hooks inside a proc (global_place.tcl): bind every script-level name to the global namespace
# so the procs below (global hs_*) see them (fp{a,b}amh-837f0663a crashed: can't read "hs_ca").
global hs_blk hs_db hs_hb hs_bf hs_firm hs_dt_nets hs_seq hs_ca hs_ni hs_no hs_nr hs_r2r
set hs_blk [ord::get_db_block]
set hs_db [ord::get_db]
set hs_hb [$hs_db findMaster [expr {[info exists ::env(OT_HS_HOLD)] ? $::env(OT_HS_HOLD) : "HB4xp67_ASAP7_75t_R"}]]
set hs_bf [$hs_db findMaster [expr {[info exists ::env(OT_HS_DRV)] ? $::env(OT_HS_DRV) : "BUFx4f_ASAP7_75t_R"}]]
if {$hs_hb eq "NULL" || $hs_bf eq "NULL"} { error "HOLDSTAGE: master missing" }
set hs_firm {}; set hs_dt_nets {}; set hs_seq 0
set hs_ca [$hs_blk getCoreArea]
proc hs_pin_xy {bt m} {
  global hs_ca
  set x 0; set y 0
  foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
    set x [expr {([$bx xMin] + [$bx xMax]) / 2}]; set y [expr {([$bx yMin] + [$bx yMax]) / 2}]; break }; break }
  set x [expr {max([$hs_ca xMin], min($x, [$hs_ca xMax] - [$m getWidth]))}]
  set y [expr {max([$hs_ca yMin], min($y, [$hs_ca yMax] - [$m getHeight]))}]
  return [list $x $y]
}
# chain: insert masters (list) between net `in` and returns the last output net (new); cells placed at xy, status st
proc hs_chain {pfx in masters xy st} {
  global hs_blk hs_firm hs_dt_nets hs_seq
  set cur $in; set cells {}
  foreach m $masters {
    set i [odb::dbInst_create $hs_blk $m [format "%s_%05d" $pfx $hs_seq]]
    set n [odb::dbNet_create $hs_blk [format "%s_n%05d" $pfx $hs_seq]]
    incr hs_seq
    [$i findITerm A] connect $cur
    [$i findITerm Y] connect $n
    lassign $xy x y
    $i setOrient R0; $i setLocation $x $y; $i setPlacementStatus $st
    if {$st eq "FIRM"} { lappend hs_firm [$i getName] }
    lappend cells $i
    set cur $n
  }
  return [list $cur $cells]
}
proc hs_is_ff {inst} { return [string match "DFF*" [[$inst getMaster] getName]] }
proc hs_flop_driven {net} {
  # driver is a flop, or a BUF/INV chain (<= 3) back to a flop
  for {set k 0} {$k < 4} {incr k} {
    set d ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set d $it; break } }
    if {$d eq ""} { return 0 }
    set inst [$d getInst]
    if {[hs_is_ff $inst]} { return 1 }
    if {![regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]]} { return 0 }
    set net [[$inst findITerm A] getNet]
    if {$net eq "NULL"} { return 0 }
  }
  return 0
}
# 2. INPUT stages
set hs_ni 0; set hs_no 0; set hs_nr 0
foreach bt [$hs_blk getBTerms] {
  if {[$bt getIoType] ne "INPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} continue
  set its [$net getITerms]
  if {[llength $its] != 1} continue
  set d [lindex $its 0]
  if {![hs_is_ff [$d getInst]] || [[$d getMTerm] getName] ne "D"} continue
  $d disconnect
  lassign [hs_chain ot_hsi $net [list $hs_hb $hs_bf] [hs_pin_xy $bt $hs_hb] FIRM] last cells
  $d connect $last
  lappend hs_dt_nets $net [[[lindex $cells 0] findITerm Y] getNet]
  incr hs_ni
}
# 3. OUTPUT stages
foreach bt [$hs_blk getBTerms] {
  if {[$bt getIoType] ne "OUTPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} continue
  if {![hs_flop_driven $net]} continue
  set pn [odb::dbNet_create $hs_blk [format "ot_hso_p%05d" $hs_no]]
  $bt disconnect
  $bt connect $pn
  lassign [hs_chain ot_hso $net [list $hs_hb $hs_hb $hs_bf] [hs_pin_xy $bt $hs_hb] FIRM] last cells
  # move the BUF output onto the port net
  set bi [lindex $cells end]; [$bi findITerm Y] disconnect; [$bi findITerm Y] connect $pn
  odb::dbNet_destroy $last
  lappend hs_dt_nets [[[lindex $cells 0] findITerm Y] getNet] [[[lindex $cells 1] findITerm Y] getNet]
  incr hs_no
}
# 4. R2R capture classes (instance globs; D pin, or wd_in* on the tag SRAM macros)
set hs_r2r {
  u_c.u_tt.u_ctl.atop* u_c.u_tt.u_ctl.s1_tag* u_c.u_tt.u_ctl.s1b_tag* u_c.u_tt.u_ctl.s2_tag* u_c.u_tt.u_ctl.s3_tag*
  u_c.u_tt.u_ctl.g_spre2.g_b*b_sbase* u_c.u_tt.u_ctl.g_spre2.g_b*b_act* u_c.u_tt.u_ctl.g_spre2.a_sbase* u_c.u_tt.u_ctl.g_spre2.a_nbs*
  u_c.u_tt.scale_addr* u_c.u_tt.mx_data* u_c.u_tt.am_val* u_c.u_sd_me_i_*line* u_c.u_su_me_am_*line*
  u_c.u_tt.u_ctl.u_rtag*ptr* u_c.u_tt.u_ctl.u_rtag*mem* u_c.u_tt.u_ctl.g_ttreg.u_ttag*ptr*
  u_c.u_tt.u_ctl.ot_step* u_c.u_tt.u_ctl.nb_step* u_c.u_tt.u_ctl.e_oen* u_c.u_tt.u_ctl.g_sca.pre_tag_r*
  u_c.u_tt.u_ctl.g_alvl*x0* u_c.u_tt.u_ctl.g_lctl*line* u_c.u_tt.u_ctl.g_lctl*sp_sel*
}
foreach inst [$hs_blk getInsts] {
  set nm [$inst getName]
  if {[string match "ot_hs*" $nm]} continue
  set hit 0
  foreach g $hs_r2r { if {[string match $g $nm]} { set hit 1; break } }
  set mac [string match "*u_tag.g_mem.g_b*u_m" $nm]
  if {!$hit && !$mac} continue
  if {$hit && ![hs_is_ff $inst]} continue
  foreach it [$inst getITerms] {
    set p [[$it getMTerm] getName]
    if {$hit && $p ne "D"} continue
    if {$mac && ![string match "wd_in*" $p]} continue
    set n [$it getNet]; if {$n eq "NULL"} continue
    $it disconnect
    lassign [hs_chain ot_hsr $n [list $hs_hb] [$inst getLocation] PLACED] last cells
    $it connect $last
    incr hs_nr
  }
}
if {$hs_seq > 0} {
  set_dont_touch [get_cells ot_hs*]
  foreach n $hs_dt_nets { $n setDoNotTouch 1 }
}
set fh [open $::env(RESULTS_DIR)/ot_hold_stage_firm.txt w]; puts $fh [join $hs_firm "\n"]; close $fh
puts "HOLDSTAGE: inputs $hs_ni (HB4+BUF), outputs $hs_no (2xHB4+BUF), r2r D pins $hs_nr (HB4), [llength $hs_firm] FIRM"
