# Existing routed PROG s8b: repair supply connectivity only, with immutable control snapshots.
read_db /work/base/6_final.odb
proc snapshot {name} {
  set b [ord::get_db_block]
  set f [open /work/$name.cells.tsv w]
  foreach i [$b getInsts] {
    puts $f "[$i getName]\t[[$i getMaster] getName]\t[$i getLocation]\t[$i getOrient]\t[$i getPlacementStatus]\t[$i isDoNotTouch]"
  }
  close $f
  set f [open /work/$name.signal.tsv w]
  foreach n [$b getNets] {
    if {[$n getSigType] in {POWER GROUND}} continue
    set pins {}
    foreach t [$n getITerms] {lappend pins "[[$t getInst] getName]/[[$t getMTerm] getName]"}
    foreach t [$n getBTerms] {lappend pins "PORT:[$t getName]"}
    puts $f "[$n getName]\t[$n getSigType]\t[lsort $pins]"
  }
  close $f
  write_def /work/$name.def
}
snapshot before
source /work/pg_connect.tcl
set before_open 0
foreach i [[ord::get_db_block] getInsts] {incr before_open [ot_pg_open_terms $i]}
if {$before_open != 216} {error "Unexpected original PG census: $before_open != 216"}
set repaired [ot_pg_connect_all codex_prog_s8b]
if {$repaired != 108} {error "Unexpected repaired instance count: $repaired != 108"}
ot_pg_require_bound codex_prog_s8b
snapshot after
write_db /work/repaired/6_final.odb
puts "CODEX_PROG_PG_REPAIRED open_before=$before_open repaired_instances=$repaired"
