# Preserve the logical clock enable when a state flop moves to an ungated related clock.
# Opt-in: caller supplies the exact state flop and its original ICG. QN library polarity
# Dnext = NAND(NAND(ENA,Dold), OR(ENA,QN)); no clock/reset changes or added cycles.
# STA must close the resulting data/enable paths; final routed LEC remains required.
proc ot_preserve_clock_enable {ff_name icg_name {prefix ot_ce_hold}} {
  set ce_blk [ord::get_db_block]
  set ce_db [ord::get_db]
  set ce_ff [$ce_blk findInst $ff_name]
  set ce_icg [$ce_blk findInst $icg_name]
  if {$ce_ff eq "NULL" || $ce_icg eq "NULL"} {error "MID_CE: expected idle flop and root ICG"}
  if {![string match DFFASRHQN* [[$ce_ff getMaster] getName]]} {error "MID_CE: expected QN async-reset flop"}
  # This class is qualified with the ICG test port physically tied low. Never drop a dynamic test enable.
  set ce_se [$ce_icg findITerm SE]
  if {$ce_se ne "NULL"} {
    set ce_sen [$ce_se getNet]
    set ce_zero 0
    if {$ce_sen eq "NULL"} {error "MID_CE: unconnected ICG test enable"}
    foreach ce_it [$ce_sen getITerms] {
      if {![$ce_it isOutputSignal]} continue
      if {![string match TIELO* [[[$ce_it getInst] getMaster] getName]]} {
        error "MID_CE: dynamic or unproved ICG test enable; preserve its effective latched/test enable explicitly"
      }
      set ce_zero 1
    }
    if {!$ce_zero || [llength [$ce_sen getBTerms]]} {error "MID_CE: ICG test enable is not a proved TIELO"}
  }
  set ce_dit [$ce_ff findITerm D]
  set ce_dold [$ce_dit getNet]
  if {[$ce_dold getName] eq "${prefix}_d"} {puts "MID_CE: already present"; return}
  set ce_qn [[$ce_ff findITerm QN] getNet]
  set ce_en [[$ce_icg findITerm ENA] getNet]
  set ce_clock [[[$ce_ff findITerm CLK] getNet] getName]
  set ce_xy [$ce_ff getLocation]
  set ce_nets {}
  foreach n {n1 n2 d} {dict set ce_nets $n [odb::dbNet_create $ce_blk ${prefix}_$n]}
  set ce_cells {}
  foreach {nm master} {a NAND2x1_ASAP7_75t_R b OR2x2_ASAP7_75t_R y NAND2x1_ASAP7_75t_R} {
    set m [$ce_db findMaster $master]
    if {$m eq "NULL"} {error "MID_CE: missing $master"}
    set c [odb::dbInst_create $ce_blk $m ${prefix}_$nm]
    $c setLocation [lindex $ce_xy 0] [lindex $ce_xy 1]
    $c setPlacementStatus PLACED
    dict set ce_cells $nm $c
  }
  foreach {nm pin net} [list a A $ce_en a B $ce_dold a Y [dict get $ce_nets n1] \
                           b A $ce_en b B $ce_qn b Y [dict get $ce_nets n2] \
                           y A [dict get $ce_nets n1] y B [dict get $ce_nets n2] y Y [dict get $ce_nets d]] {
    [[dict get $ce_cells $nm] findITerm $pin] connect $net
  }
  $ce_dit disconnect
  $ce_dit connect [dict get $ce_nets d]
  puts "MID_CE: [$ce_ff getName] D guarded by [$ce_en getName], QN [$ce_qn getName], clock $ce_clock unchanged; 3 combinational cells, 0 cycles"
}
