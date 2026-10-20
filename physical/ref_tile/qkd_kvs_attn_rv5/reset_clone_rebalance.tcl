# Private rv5 structural reset redistribution, after pin_reg_split and before placement/CTS.
# No cells, clocks, data nets, reset edges or reset polarity are changed. Copies
# may share terminals ONLY inside one actual first-stage-D/clock/master family.
set ot_rb [ord::get_db_block]
proc ot_rv5_origin {n} {
 set seen {}
 while {1} {
  set nn [$n getName]
  if {[dict exists $seen $nn]} {error "RV5_RESET cycle at $nn"}
  dict set seen $nn 1
  set ds {}
  foreach t [$n getITerms] {if {[$t isOutputSignal]} {lappend ds $t}}
  if {[llength $ds] == 0 && [llength [$n getBTerms]] == 1 && [[lindex [$n getBTerms] 0] getIoType] eq "INPUT"} {return $nn}
  if {[llength $ds] != 1} {error "RV5_RESET source count [llength $ds] at $nn"}
  set i [[lindex $ds 0] getInst];set m [[$i getMaster] getName]
  if {![regexp {^(BUF|HB|CKBUF)} $m]} {return $nn}
  set a [$i findITerm A]
  if {$a eq "NULL" || [$a getNet] eq "NULL"} {error "RV5_RESET no buffer source $m"}
  set n [$a getNet]
 }
}
set ot_rf {};set ot_rn {}
foreach i [$ot_rb getInsts] {
 if {![regexp {ot_rrs__rst_n__ot_rlv__c[0-9]+\$_DFF_P_} [$i getName]]} {continue}
 if {[[$i getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "RV5_RESET unsupported final master"}
 set d [[$i findITerm D] getNet];set c [[$i findITerm CLK] getNet];set q [[$i findITerm QN] getNet]
 if {$d eq "NULL" || $c eq "NULL" || $q eq "NULL"} {error "RV5_RESET disconnected final copy"}
 set key [list [ot_rv5_origin $d] [ot_rv5_origin $c] [[$i getMaster] getName]]
 dict lappend ot_rf $key [list [$i getName] $q]
 dict set ot_rn [$q getName] $key
}
if {[dict size $ot_rn] < 1 || [dict size $ot_rn] > 64 || [dict size $ot_rf] != 2} {error "RV5_RESET unsupported final/first family counts [dict size $ot_rn]/[dict size $ot_rf]"}
# The mapped kept landing FF has exactly one polarity inverter, possibly with
# transparent physical buffers before/after it. Keep that inverter and its clock,
# D/control path unchanged. Reassign only downstream terminals, on inverse outputs
# whose FFs share the same actual first-copy D and clock family.
set ot_assign {};set ot_seen {}
dict for {key copies} $ot_rf {
 set terms {};set dests {}
 foreach pair $copies {
  set todo [list [lindex $pair 1]];set nets {};set invs {}
  while {[llength $todo]} {
   set n [lindex $todo end];set todo [lrange $todo 0 end-1];set nn [$n getName]
   if {[dict exists $nets $nn]} {continue};dict set nets $nn 1
   foreach t [$n getITerms] {
    if {![$t isInputSignal]} {continue}
    set i [$t getInst];set m [[$i getMaster] getName];set pn [[$t getMTerm] getName]
    if {![regexp {^(BUF|INV|HB|CKBUF|CKINV)} $m] || $pn ne "A"} {error "RV5_RESET unexpected positive-polarity endpoint [$i getName]/$pn"}
    set y [$i findITerm Y]
    if {$y eq "NULL" || [$y getNet] eq "NULL"} {error "RV5_RESET unsupported transparent output"}
    if {[regexp {^(INV|CKINV)} $m]} {lappend invs [list [$i getName] [$y getNet]]} else {lappend todo [$y getNet]}
   }
   if {[llength [$n getBTerms]]} {error "RV5_RESET exported reset-copy source $nn"}
  }
  if {[llength $invs] != 1} {error "RV5_RESET expected exactly one existing polarity inverter per final FF"}
  set inv [lindex $invs 0];lappend dests [list [lindex $pair 0] [lindex $inv 1]]
  set todo [list [lindex $inv 1]];set nets {}
  while {[llength $todo]} {
   set n [lindex $todo end];set todo [lrange $todo 0 end-1];set nn [$n getName]
   if {[dict exists $nets $nn]} {continue};dict set nets $nn 1
   foreach t [$n getITerms] {
    if {![$t isInputSignal]} {continue}
    set i [$t getInst];set m [[$i getMaster] getName];set pn [[$t getMTerm] getName]
    if {[regexp {^(BUF|HB|CKBUF)} $m] && $pn eq "A"} {
     set y [$i findITerm Y]
     if {$y eq "NULL" || [$y getNet] eq "NULL"} {error "RV5_RESET unsupported buffer"}
     lappend todo [$y getNet]
    } elseif {$pn ne "CLK" && ![regexp {^(INV|CKINV)} $m]} {
     set tn "[$i getName]/$pn"
     if {[dict exists $ot_seen $tn]} {error "RV5_RESET duplicate terminal $tn"}
     dict set ot_seen $tn 1;lappend terms [list $tn $t $nn]
    } else {error "RV5_RESET clock/double-inverted endpoint [$i getName]/$pn"}
   }
   if {[llength [$n getBTerms]]} {error "RV5_RESET exported final reset $nn"}
  }
 }
 set dests [lsort -index 0 $dests];set terms [lsort -index 0 $terms]
 set nc [llength $dests];set nt [llength $terms]
 if {$nt > 32*$nc} {error "RV5_RESET family capacity $nt > 32*$nc ($key)"}
 set k 0
 foreach term $terms {
  set dest [lindex $dests [expr {$k % $nc}]]
  lappend ot_assign [list [lindex $term 1] [lindex $dest 1] [lindex $term 0] [lindex $term 2]]
  incr k
 }
 puts "RV5_RESET_FAMILY key=$key copies=$nc terminals=$nt max=[expr {($nt+$nc-1)/$nc}]"
}
# Mutate only after the complete capability/capacity/polarity check succeeds.
foreach a $ot_assign {[lindex $a 0] connect [lindex $a 1]}
puts "RV5_RESET_REBALANCED final_copies=[dict size $ot_rn] terminals=[llength $ot_assign] new_cells=0 added_edges=0"
