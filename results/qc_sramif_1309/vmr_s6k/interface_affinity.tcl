# Clock each existing pre-MIF / MIF data-register pair from one nearby leaf.
uplevel #0 {
set ia_blk [ord::get_db_block];set ia_u [[ord::get_db_tech] getDbUnitsPerMicron]
proc ia_name {i} {string map [list [format %c 92] ""] [$i getName]}
proc ia_ck {i} {foreach t [$i getITerms] {if {[[$t getMTerm] getName] in {CLK CK}} {return $t}};error "IF_PAIR no clock [$i getName]"}
proc ia_xy {i} {set b [$i getBBox];list [expr {([$b xMin]+[$b xMax])/2.0/$::ia_u}] [expr {([$b yMin]+[$b yMax])/2.0/$::ia_u}]}
set ia_map {}
foreach i [$ia_blk getInsts] {dict set ia_map [ia_name $i] $i}
set ia_n 0;set ia_moved 0
dict for {name src} $ia_map {
 if {![regexp {^g_wr\[([01])\]\.g_r\.u_d/q\[([0-9]+)\]\$_DFF_P_$} $name -> bank bit]} continue
 set dst [dict get $ia_map [format {g_mw[%s].u_d/q[%s]$_DFF_P_} $bank $bit]]
 set chosen ""
 foreach n [list [[ia_ck $dst] getNet] [[ia_ck $src] getNet]] {
  set count 0;set ours 0;set driver ""
  foreach t [$n getITerms] {
   if {[$t isOutputSignal]} {set driver [$t getInst]}
   if {[$t isInputSignal] || [$t isClocked]} {incr count;if {[$t getInst] in [list $src $dst]} {incr ours}}
  }
  if {$driver eq "" || ![regexp {^(BUF|INV|HB|CK)} [[$driver getMaster] getName]] || $count-$ours+2>60} continue
  lassign [ia_xy $driver] x y;set rad 0
  foreach i [list $src $dst] {lassign [ia_xy $i] a b;set rad [expr {max($rad,abs($x-$a)+abs($y-$b))}]}
  if {$rad<=30} {set chosen $n;break}
 }
 if {$chosen eq ""} {error "IF_PAIR no local leaf with radius30/sinks60 for $name"}
 foreach i [list $src $dst] {set t [ia_ck $i];if {[$t getNet] ne $chosen} {$t disconnect;$t connect $chosen;incr ia_moved}}
 incr ia_n
}
if {$ia_n!=512} {error "IF_PAIR expected512 clock pairs, got$ia_n"}
puts "IF_PAIR_CLOCK PASS pairs $ia_n clock_sinks_moved $ia_moved data_changes0 added_cycles0"
}
