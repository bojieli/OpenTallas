# Request-bus output-hop hold stage for dsfd_vm_bgq28 (el1011-ds-vm/bgq28 2026-10-11, PRE_GLOBAL_PLACE).
# s81vm-bgq28-803dc8b3a-tc-rd-pd45 EARLY_FAIL_HOLD: CTS hold repair cleared every class (TNS -6,299 -> -1,067) except
# ONE: the last relay hop rb[FS-1] (g_s[1].a_d/a_row/a_m) -> f_* S-face output pin flops, 80 endpoints, stuck at FF
# -36.4 ps for 2,000 iterations. Cause (STA on the pd45 CTS odb): the f_* pin-flop row (1,990 flops in one row along
# the S edge, 250 um from the W-face clock entry ck[0]) is fed by CTS leaves with long leaf wires (e.g. leaf_2447 input
# wire 68 ps), so f_* CLK arrivals span ~381..491 ps and the hop's capture clock lands ~100 ps after launch over
# 20-60 um of wire. Setup slack on that hop is > +600 ps.
# Deterministic fix (OWNER 10-10 "hold-only miss -> delay stage at inputs; no ECO loops"), applied uniformly to the
# D pin of EVERY f_* output pin flop: OT_FHOLD_N (default 2) dont_touch OT_FHOLD_MASTER (HB4xp67, ~36-41 ps FF each)
# in series between the relay and the pin flop. Functional netlist unchanged (buffers only, same latency).
set ot_fh_master [expr {[info exists ::env(OT_FHOLD_MASTER)] ? $::env(OT_FHOLD_MASTER) : "HB4xp67_ASAP7_75t_R"}]
set ot_fh_nst [expr {[info exists ::env(OT_FHOLD_N)] ? $::env(OT_FHOLD_N) : 2}]
set ot_fh_blk [ord::get_db_block]
set ot_fh_m [[ord::get_db] findMaster $ot_fh_master]
if {$ot_fh_m eq "NULL"} { error "FHOLD: $ot_fh_master missing" }
set ot_fh_n 0; set ot_fh_k 0
foreach inst [$ot_fh_blk getInsts] {
  set nm [string map {"\\" ""} [$inst getName]]
  if {![regexp {^u\.f_(v|we|row|mask|d)(\[|\$)} $nm]} continue
  if {![string match "DFF*" [[$inst getMaster] getName]]} continue
  set d [$inst findITerm D]; if {$d eq "NULL"} continue
  set net [$d getNet]; if {$net eq "NULL"} continue
  lassign [$inst getLocation] x y
  $d disconnect
  set src $net
  for {set s 0} {$s < $ot_fh_nst} {incr s} {
    set cell [odb::dbInst_create $ot_fh_blk $ot_fh_m [format "ot_fhold_%05d_%d" $ot_fh_n $s]]
    set n2 [odb::dbNet_create $ot_fh_blk [format "ot_fhold_n%05d_%d" $ot_fh_n $s]]
    [$cell findITerm A] connect $src
    [$cell findITerm Y] connect $n2
    $cell setOrient [$inst getOrient]; $cell setLocation $x $y; $cell setPlacementStatus PLACED
    set src $n2; incr ot_fh_k
  }
  $d connect $src
  incr ot_fh_n
}
if {$ot_fh_k > 0} { set_dont_touch [get_cells ot_fhold_*] }
puts "FHOLD: $ot_fh_n f_* output pin flops, $ot_fh_k hold cells ($ot_fh_nst x $ot_fh_master per D, dont_touch)"
if {$ot_fh_n == 0} { error "FHOLD: no f_* output flops matched" }
