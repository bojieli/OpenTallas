# Disposable-ODB integration check, never a routed qualification. Caller reads
# the immutable source ODB and sets ECTL_ECO_INPUT_ODB, ECTL_TEST_OUT,
# ECTL_TEST_PLAN, ECTL_TEST_REMOVED. Do not source in a production route snapshot.
foreach k {ECTL_TEST_OUT ECTL_TEST_PLAN ECTL_TEST_REMOVED} {
  if {![info exists ::env($k)]} {error "missing disposable-test argument $k"}
}
proc ectl_protected_census {tag} {
  set f [open $::env(ECTL_TEST_OUT)/${tag}_protected.tsv w]
  foreach i [[ord::get_db_block] getInsts] {
    set m [[$i getMaster] getName]
    if {[[$i getMaster] isBlock] || [regexp {^DFF} $m]} {
      puts $f [join [list CELL [$i getName] $m [$i getLocation] [$i getOrient]] "\t"]
      foreach it [$i getITerms] {
        set pin [[$it getMTerm] getName]
        if {[[$i getMaster] isBlock] || $pin in {CLK RESETN SETN}} {
          set n [$it getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]}
          puts $f [join [list PROTECTED [$i getName] $pin $nn] "\t"]
        }
      }
    }
  }
  foreach n [[ord::get_db_block] getNets] {
    if {[$n getSigType] eq "CLOCK"} {
      set terms {}
      foreach it [$n getITerms] {lappend terms "[[$it getInst] getName]/[[$it getMTerm] getName]"}
      puts $f [join [list CLOCK [$n getName] [lsort $terms]] "\t"]
    }
  }
  close $f
}
ectl_protected_census before
set before_n [llength [[ord::get_db_block] getInsts]]
source $::env(ECTL_TEST_PLAN)
set after_n [llength [[ord::get_db_block] getInsts]]
if {$before_n-$after_n != $::env(ECTL_TEST_REMOVED)} {error "wrong physical removal count"}
ectl_protected_census after
check_placement -verbose
write_db $::env(ECTL_TEST_OUT)/UNQUALIFIED_normalized.odb
write_verilog $::env(ECTL_TEST_OUT)/UNQUALIFIED_normalized.v
puts "DISPOSABLE_ODB_APPLY_PASS removed=[expr {$before_n-$after_n}] NO_ROUTED_QUALIFICATION"
