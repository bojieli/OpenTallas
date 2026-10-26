# No data repair, hold padding or absolute-latency alignment in this trial.
::ot_dtsh::audit
set b [ord::get_db_block];set npg 0
foreach i [$b getInsts] {
 if {![string match ot_dtsh_* [$i getName]] && ![string match ot_dtap_* [$i getName]]} continue
 foreach it [$i getITerms] {
  if {[[$it getMTerm] getSigType] ni {POWER GROUND}} continue
  set n [$it getNet]
  if {$n eq "NULL" || $n eq ""} {error "R5 CLOCK PG missing [$i getName]/[[$it getMTerm] getName]"}
  incr npg
 }
}
puts "R5 CLOCK PG terminals connected: $npg"
