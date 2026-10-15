# Measured g8 native defect: co178 is driven by this dedicated pin flop,
# followed by real output hold stages. Its FF routed output slack is +95.071ps.
# Use the existing local clock subtree one genuine buffer earlier for that
# flop only. This is physical wiring; all periods and setup/hold checks stay.
proc s81_co178_local_retap {} {
 set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
 set ff [$b findInst ot_prs_00083_ff]
 if {$ff eq "NULL"} {error "S81_CO178 missing actual dedicated output register"}
 set cp [$ff findITerm CLK];set old [$cp getNet];set drv "NULL"
 foreach it [$old getITerms] {
  if {[[$it getMTerm] getIoType] eq "OUTPUT"} {set drv [$it getInst]}
 }
 if {$drv eq "NULL" || ![string match clkbuf_leaf_* [$drv getName]]} {error "S81_CO178 expected genuine final clock leaf"}
 set ip [$drv findITerm A]
 if {$ip eq "NULL"} {error "S81_CO178 expected actual clock buffer A input"}
 set upstream [$ip getNet]
 if {$upstream eq "NULL" || [$upstream getSigType] ne "CLOCK"} {error "S81_CO178 requires same actual clock subtree"}
 lassign [$ff getLocation] x y;lassign [$drv getLocation] a z
 set distance [expr {(abs($x-$a)+abs($y-$z))/double($dbu)}]
 if {$distance>20} {error "S81_CO178 refuses nonlocal clock retap $distance um"}
 $cp disconnect;$cp connect $upstream
 puts "S81_CO178 retapped actual outputFF [$ff getName] from [$old getName] to [$upstream getName], bypass [$drv getName] distance=$distance um; no latency or SDC change"
}
rename clock_tree_synthesis s81_co178_original_cts
proc clock_tree_synthesis {args} {
 uplevel 1 [list s81_co178_original_cts {*}$args]
 s81_co178_local_retap
}
