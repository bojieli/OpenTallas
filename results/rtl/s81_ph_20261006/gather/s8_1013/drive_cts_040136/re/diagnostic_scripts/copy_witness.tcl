read_db [lindex [glob /work/results/asap7/*/base/3_2_place_iop.odb] 0]
set b [ord::get_db_block];set copies {};set seq {}
foreach i [$b getInsts] {
 if {![[$i getMaster] isSequential]} continue
 lappend seq $i
 regsub -all {\\} [$i getName] {} n
 if {[string match {*g_candidate_local.u_sv/q*} $n]} {lappend copies $i}
}
if {[llength $copies]!=4} {error "CANDIDATE_COPY expected4 real consumed local SV FFs, got[llength $copies]"}
foreach c $copies {
 set d [[$c findITerm D] getNet];set clk [[$c findITerm CLK] getNet];set rst [[$c findITerm RESETN] getNet]
 set matches {}
 foreach i $seq {
  if {$i eq $c} continue
  set ip [$i findITerm D];set cp [$i findITerm CLK];set rp [$i findITerm RESETN]
  if {$ip eq "NULL" || $cp eq "NULL" || $rp eq "NULL"} continue
  if {[$ip getNet] eq $d && [$cp getNet] eq $clk && [$rp getNet] eq $rst} {lappend matches [$i getName]}
 }
 set q [$c findITerm QN];if {$q eq "NULL"} {set q [$c findITerm Q]}
 set qnet [$q getNet];set loads {}
 foreach it [$qnet getITerms] {if {![$it isOutputSignal]} {lappend loads "[[$it getInst] getName]/[[$it getMTerm] getName]"}}
 if {![llength $matches] || ![llength $loads]} {error "CANDIDATE_COPY no original sameD/reset/clock or no consumedQ [$c getName]"}
 puts "CANDIDATE_COPY [$c getName] [[$c getMaster] getName] D=[$d getName] CLK=[$clk getName] RESETN=[$rst getName] originals=[join $matches ,] Q=[$qnet getName] actualloads=[join $loads ,]"
}
puts "CANDIDATE_COPY PASS4 actual synthesized state present, original sameD/sameclock/samereset, real drivenQ loads; no unused role witness."
exit
