foreach l $::env(PLIBS) {read_liberty $l}
read_db $::env(ODB)
read_sdc $::env(SDC)
proc snap {path} {
 set f [open $path w]
 foreach i [[ord::get_db_block] getInsts] {
  set b [$i getBBox]
  puts $f [list I [$i getName] [[$i getMaster] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax] [$i getOrient]]
  foreach it [$i getITerms] {
   set n [$it getNet];set nn {};if {$n ne "NULL" && $n ne {}} {set nn [$n getName]}
   puts $f [list P [$i getName] [[$it getMTerm] getName] $nn]
  }
 }
 close $f
}
snap /out/before.tsv
source /src/tools/die_plan/tap_chain_affinity.tcl
set proto_root [[[ord::get_db_block] findBTerm clk] getNet]
::ot_tap_chain::capture $proto_root
source /proto_assign.tcl
snap /out/after_A.tsv
::ot_tap_chain::apply
snap /out/after_B.tsv
exit
