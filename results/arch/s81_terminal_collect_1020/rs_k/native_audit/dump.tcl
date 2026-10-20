set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $P/lib/NLDM/*RVT*TT*.lib*] {read_liberty $l}
foreach l [glob -nocomplain /src/physical/asap7_memory_macros/*/*_tt.lib] {read_liberty $l}
read_db /case/routes/gate/work/orfs/results/asap7/opentallas_ot_s81sl_rs_asap7_ref_gate/base/4_cts.odb
write_verilog /audit/grt.v
set b [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /audit/terms.tsv w]
set pg_bound 0;set pg_unbound 0
foreach inst [$b getInsts] {
 set name [string map {\\ {}} [$inst getName]]
 set master [[$inst getMaster] getName]
 foreach it [$inst getITerms] {
  set mt [$it getMTerm];set net [$it getNet];set sig [$mt getSigType]
  if {$sig in {POWER GROUND}} {
   if {$net eq "NULL"} {incr pg_unbound} else {incr pg_bound}
   continue
  }
  if {$net eq "NULL"} continue
  lassign [$it getAvgXY] good x y
  if {!$good} {error "missing native ITerm coordinate $name/[$mt getName]"}
  puts $f [join [list "$name/[$mt getName]" [$net getName] [$mt getIoType] $master [[$inst getMaster] isBlock] [expr {$x/double($u)}] [expr {$y/double($u)}]] "\t"]
 }
}
foreach bt [$b getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} continue
 set net [$bt getNet];if {$net eq "NULL"} continue
 set bb [$bt getBBox]
 puts $f [join [list "PORT/[$bt getName]" [$net getName] [$bt getIoType] PORT 0 [expr {([$bb xMin]+[$bb xMax])/2.0/$u}] [expr {([$bb yMin]+[$bb yMax])/2.0/$u}]] "\t"]
}
close $f
set f [open /audit/instances.tsv w]
foreach inst [$b getInsts] {
 set bb [$inst getBBox]
 puts $f [join [list [string map {\\ {}} [$inst getName]] [[$inst getMaster] getName] [[$inst getMaster] isBlock] [$inst getOrient] [$inst getPlacementStatus] [expr {[$bb xMin]/double($u)}] [expr {[$bb yMin]/double($u)}] [expr {[$bb xMax]/double($u)}] [expr {[$bb yMax]/double($u)}]] "\t"]
}
close $f
puts "CTRL_NATIVE_DB_DUMP_PASS pg_bound=$pg_bound pg_unbound=$pg_unbound"
