# Opt-in structural clock grouping for the eight RP1 three-bit-to-onehot decoder families.
# Each family = 3 address landing FFs,3 snapshots,3 offsets,16 onehot FFs.
# All twenty-five cells retain the same functional clock; no data connection or RTL changes.
uplevel #0 {
set da_blk [ord::get_db_block]
set da_u [[ord::get_db_tech] getDbUnitsPerMicron]
set da_groups {}
proc da_name {i} {string map [list [format %c 92] ""] [$i getName]}
proc da_xy {i} {set b [$i getBBox];list [expr {([$b xMin]+[$b xMax])/2.0/$::da_u}] [expr {([$b yMin]+[$b yMax])/2.0/$::da_u}]}
proc da_ck {i} {
  foreach t [$i getITerms] {if {[[$t getMTerm] getName] in {CLK CK}} {return $t}}
  error "RP1_DECODE no clock pin on [$i getName]"
}
foreach i [$da_blk getInsts] {
  set n [da_name $i]; set g ""
  if {[regexp {^c1_off\[([0-9]+)\]\$_DFF_P_$} $n -> k]} {set g [expr {$k/3}]}
  if {[regexp {^g_cext\[([0-9]+)\]\.u[01]/q\[[0-7]\]\$_DFF_P_$} $n -> k]} {set g $k}
  if {[regexp {^g_rs1\.u_rs/q\[([0-9]+)\]\$_DFF_P_$} $n -> k] && $k>0} {set g [expr {($k-1)/3}]}
  if {[regexp {^pcr_addr\[([0-9]+)\]\$_DFF_P_$} $n -> k] && $k%24<3} {set g [expr {$k/24}]}
  if {$g ne ""} {dict lappend da_groups $g $i}
}
if {[dict size $da_groups]!=8} {error "RP1_DECODE expected eight decoder families, got [dict size $da_groups]"}
set da_cands {}
foreach i [$da_blk getInsts] {
  if {![string match *DFF* [[$i getMaster] getName]]} continue
  set ck [da_ck $i];set n [$ck getNet]
  if {$n eq "NULL" || ![string match *ot_ctap_W0_n [$n getName]]} continue
  dict set da_cands [$n getName] $n
}
set da_moved 0
foreach g {3 0 1 2 4 5 6 7} {
  set group [dict get $da_groups $g]
  if {[llength $group]!=25} {error "RP1_DECODE family $g expected25 registers, got[llength $group]"}
  set group_names {}
  foreach i $group {dict set group_names [$i getName] 1}
  set best "";set score -1e20;set bestN 0;set bestR 0
  dict for {nn n} $da_cands {
    set driver "";set count 0;set ours 0
    foreach t [$n getITerms] {
      if {[$t isOutputSignal]} {set driver [$t getInst]}
      if {[$t isInputSignal] || [$t isClocked]} {
        incr count
        if {[dict exists $group_names [[$t getInst] getName]]} {incr ours}
      }
    }
    if {$driver eq "" || ![regexp {^(BUF|INV|HB|CK)} [[$driver getMaster] getName]]} continue
    set projected [expr {$count-$ours+25}]
    if {$projected>60} continue
    lassign [da_xy $driver] x y
    set radius 0;set sum 0
    foreach i $group {lassign [da_xy $i] a b;set d [expr {abs($x-$a)+abs($y-$b)}];set radius [expr {max($radius,$d)}];set sum [expr {$sum+$d}]}
    if {$radius>30.0} continue
    set s [expr {1000*$ours-$sum-5*$projected}]
    if {$s>$score} {set score $s;set best $n;set bestN $projected;set bestR $radius}
  }
  if {$best eq ""} {error "RP1_DECODE family$g has no local leaf with <=60 sinks and <=30um radius"}
  foreach i $group {set t [da_ck $i];if {[$t getNet] ne $best} {$t disconnect;$t connect $best;incr da_moved}}
  puts "RP1_DECODE family $g regs25 leaf [$best getName] projected_sinks $bestN max_radius_um $bestR"
}
puts "RP1_DECODE PASS families8 registers200 clock_sinks_moved $da_moved data_changes0 added_cycles0"
}
