# Reset-input hold stage for dsfd_vm_be_sl (el1011-ds-vm/be 2026-10-12, PRE_GLOBAL_PLACE).
# s81vm-besl5-810b8c0f4-tc-rd-pd45: TT +27.1 / FF -23.48: the ONLY FF hold violator is input -> reg
# rns_in[0] (vclk_t, ideal latency 127.6 ps, hold input delay 0) -> u_rns/q (str_clk pin flop, cks tree 129.5 ps):
# arrival 141.9 vs required 165.4 (25 ps uncertainty + 10.8 ps hold time); the input has only a 9 ps buffer before the
# pin flop. Setup on these reset-input pin flops has the whole cycle (they are kreg stage-0 flops, no logic before them).
# Deterministic fix (OWNER 10-10 "hold-only miss -> delay stage at inputs; no ECO loops"), applied uniformly to the D of
# EVERY reset-input pin flop (u_rn_i/x/c/p/w on ck, u_rns on cks): OT_RHOLD_N (default 2) dont_touch HB4xp67
# (~36-41 ps FF each) in series between the port and the flop. Functional netlist unchanged (buffers only, same latency).
# The port net and the chain nets are dont_touch too: besl6-5c07be0cc cal died in 3_3 timing-driven GPL with
# RSZ-3006 "Failed to insert buffer before loads for net rn_in[0]" (ODB-1211: load ot_rhold_00_0/A is dont_touch) --
# repair_design must skip these nets entirely rather than try to split their (dont_touch) loads.
set ot_rh_master [expr {[info exists ::env(OT_RHOLD_MASTER)] ? $::env(OT_RHOLD_MASTER) : "HB4xp67_ASAP7_75t_R"}]
set ot_rh_nst [expr {[info exists ::env(OT_RHOLD_N)] ? $::env(OT_RHOLD_N) : 2}]
set ot_rh_blk [ord::get_db_block]
set ot_rh_m [[ord::get_db] findMaster $ot_rh_master]
if {$ot_rh_m eq "NULL"} { error "RHOLD: $ot_rh_master missing" }
set ot_rh_n 0; set ot_rh_k 0; set ot_rh_dtn {}
foreach inst [$ot_rh_blk getInsts] {
  set nm [string map {"\\" ""} [$inst getName]]
  if {![regexp {^u_(rns|rn_[ixcpw])[./]q(\[0\])?\$} $nm]} continue
  if {![string match "DFF*" [[$inst getMaster] getName]]} continue
  set d [$inst findITerm D]; if {$d eq "NULL"} continue
  set net [$d getNet]; if {$net eq "NULL"} continue
  lassign [$inst getLocation] x y
  $d disconnect
  set src $net
  lappend ot_rh_dtn $net
  for {set s 0} {$s < $ot_rh_nst} {incr s} {
    set cell [odb::dbInst_create $ot_rh_blk $ot_rh_m [format "ot_rhold_%02d_%d" $ot_rh_n $s]]
    set n2 [odb::dbNet_create $ot_rh_blk [format "ot_rhold_n%02d_%d" $ot_rh_n $s]]
    [$cell findITerm A] connect $src
    [$cell findITerm Y] connect $n2
    $cell setOrient [$inst getOrient]; $cell setLocation $x $y; $cell setPlacementStatus PLACED
    lappend ot_rh_dtn $n2
    set src $n2; incr ot_rh_k
  }
  $d connect $src
  puts "RHOLD: $nm"
  incr ot_rh_n
}
if {$ot_rh_k > 0} { set_dont_touch [get_cells ot_rhold_*] }
# nets last: odb refuses (ODB-0373) to connect an iterm to a net already marked dont_touch
foreach n [lsort -unique $ot_rh_dtn] { $n setDoNotTouch 1 }
puts "RHOLD: $ot_rh_n reset-input pin flops, $ot_rh_k hold cells ($ot_rh_nst x $ot_rh_master per D, cells+nets dont_touch)"
if {$ot_rh_n != 6} { error "RHOLD: expected 6 reset-input pin flops (u_rn_i/x/c/p/w, u_rns), matched $ot_rh_n" }
