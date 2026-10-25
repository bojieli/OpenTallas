# ELEM-S81 canonical legacy cores (POST_SYNTH_TCL hook of ORFS synth_odb.tcl, after eliminate_dead_logic, before
# 1_synth.odb is written): make the register-on-every-pin contract hold in the IMPLEMENTED netlist without touching RTL.
#  1. physical/common_flow/pin_reg_split.tcl: every flop-driven output port gets its own launch flop (clone with the
#     same D / clock / reset nets: register duplication, function unchanged, 0 cycles) when the RTL flop also feeds
#     internal logic (sticky / hold self-loops, status bits read back) or a second port.
#  2. unused input bits (no load left after synthesis): one capture flop per bit (D = the pin, clock = the core clock,
#     output unconnected, dont_touch): the face register the plan budgets at every pin; it drives nothing, so the
#     function is unchanged.
#  3. constant outputs (TIE-driven after Yosys removed a constant register): one launch flop per bit;
#  4. internal nets left with a port's name are renamed (no aliasing in the written netlist);
#  5. writes RESULTS_DIR/1_synth.v (the netlist of 1_synth.odb): face_guard (run_kit.sh) and signoff.py read it.
# Env: OT_CORE_CLK (clock port base name), OT_CORE_SKIP (clock / reset port base names, never captured).
source /work/pin_reg_split.tcl
set ot_fc_blk [ord::get_db_block]
set ot_fc_ck ""
foreach bt [$ot_fc_blk getBTerms] {
  if {[regexp "^$::env(OT_CORE_CLK)(\\\[0\\\])?\$" [$bt getName]]} { set ot_fc_ck [$bt getNet] }
}
if {$ot_fc_ck eq "" || $ot_fc_ck eq "NULL"} { error "OT_FCAP: clock port $::env(OT_CORE_CLK) has no net" }
set ot_fc_m [[ord::get_db] findMaster DFFHQNx1_ASAP7_75t_R]
set ot_fc_n 0
set ot_fc_bts {}
foreach bt [$ot_fc_blk getBTerms] {
  if {[$bt getIoType] ne "INPUT"} continue
  if {[lsearch -exact $::env(OT_CORE_SKIP) [regsub {\[[0-9]+\]$} [$bt getName] ""]] >= 0} continue
  lappend ot_fc_bts [list [$bt getName] $bt]
}
foreach pr [lsort -index 0 $ot_fc_bts] {
  set bt [lindex $pr 1]
  set net [$bt getNet]
  if {$net eq "NULL" || $net eq ""} {
    set net [odb::dbNet_create $ot_fc_blk [format "ot_fcap_%05d_d" $ot_fc_n]]
    $bt connect $net
  }
  set loads 0
  foreach it [$net getITerms] { if {[$it isInputSignal]} { incr loads } }
  if {$loads} continue
  set ci [odb::dbInst_create $ot_fc_blk $ot_fc_m [format "ot_fcap_%05d_ff" $ot_fc_n]]
  [$ci findITerm D] connect $net
  [$ci findITerm CLK] connect $ot_fc_ck
  $ci setDoNotTouch 1
  incr ot_fc_n
}
puts "OT_FCAP: $ot_fc_n unused input bits given a capture flop (dont_touch)"
# constant outputs: Yosys removes a register whose D is constant (RTL: reset 0, always loaded 0, e.g. gunit_l1
# rw_x[511:192]) and ties the port(s) to a TIE cell.  Give every such port bit its own launch flop holding that constant
# (DFFHQN: D = the opposite tie, QN = the constant from the first clock edge on; the S81 reset rule keeps the clock
# running for many edges under reset, so the port shows the RTL value whenever the RTL register would), dont_touch.
set ot_fc_lo ""; set ot_fc_hi ""; set ot_fc_kn 0
foreach bt [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} [$ot_fc_blk getBTerms]] {
  if {[$bt getIoType] ne "OUTPUT"} continue
  set net [$bt getNet]
  if {$net eq "NULL" || $net eq ""} continue
  # walk port -> driver through <= 4 BUF / INV cells (synthesis output buffers) to a TIE cell
  set val ""; set inv 0; set cn $net
  for {set hop 0} {$hop < 5 && $val eq ""} {incr hop} {
    set dv ""
    foreach it [$cn getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { set dv $it; break } }
    if {$dv eq ""} break
    set dm [[[$dv getInst] getMaster] getName]
    if {[string match "TIELO*" $dm]} { set val [expr {$inv}]; break }
    if {[string match "TIEHI*" $dm]} { set val [expr {1 - $inv}]; break }
    if {![regexp {^(BUF|INV|HB)} $dm]} break
    if {[string match "INV*" $dm]} { set inv [expr {1 - $inv}] }
    set ain [[$dv getInst] findITerm A]
    if {$ain eq "NULL" || $ain eq ""} break
    set cn [$ain getNet]
    if {$cn eq "NULL" || $cn eq ""} break
  }
  if {$val eq ""} continue
  if {$ot_fc_lo eq ""} {
    set c [odb::dbInst_create $ot_fc_blk [[ord::get_db] findMaster TIELOx1_ASAP7_75t_R] ot_fconst_lo]
    set ot_fc_lo [odb::dbNet_create $ot_fc_blk ot_fconst_lo_n]; [$c findITerm L] connect $ot_fc_lo
    set c [odb::dbInst_create $ot_fc_blk [[ord::get_db] findMaster TIEHIx1_ASAP7_75t_R] ot_fconst_hi]
    set ot_fc_hi [odb::dbNet_create $ot_fc_blk ot_fconst_hi_n]; [$c findITerm H] connect $ot_fc_hi
  }
  set ci [odb::dbInst_create $ot_fc_blk $ot_fc_m [format "ot_fconst_%05d_ff" $ot_fc_kn]]
  [$ci findITerm D] connect [expr {$val ? $ot_fc_lo : $ot_fc_hi}]
  [$ci findITerm CLK] connect $ot_fc_ck
  set q [odb::dbNet_create $ot_fc_blk [format "ot_fconst_%05d_q" $ot_fc_kn]]
  [$ci findITerm QN] connect $q
  $bt disconnect
  $bt connect $q
  $ci setDoNotTouch 1
  incr ot_fc_kn
}
puts "OT_FCAP: $ot_fc_kn constant output bits given their own launch flop (dont_touch)"
# pin_reg_split moves a port to a new net; the old internal net keeps the port's name, and write_verilog would then emit
# two drivers for that port name (internal net + assign).  Rename such internal nets (connectivity unchanged).
set ot_fc_rn 0
foreach bt [$ot_fc_blk getBTerms] {
  set n [$ot_fc_blk findNet [$bt getName]]
  if {$n eq "NULL" || $n eq ""} continue
  if {[$bt getNet] ne "NULL" && [[$bt getNet] getName] eq [$n getName]} continue
  $n rename [format "ot_fc_int_%05d" $ot_fc_rn]
  incr ot_fc_rn
}
puts "OT_FCAP: $ot_fc_rn internal nets renamed off their former port names"
write_verilog $::env(RESULTS_DIR)/1_synth.v
