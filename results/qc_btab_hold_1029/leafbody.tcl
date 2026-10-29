foreach i [[ord::get_db_block] getInsts] {
  set n [$i getName]
  if {![regexp {^mp_ck_T[a-z]+$} $n]} continue
  set o [$i findITerm Y]
  if {$o eq "NULL" || $o eq ""} continue
  set net [$o getNet]
  if {$net eq "NULL" || $net eq ""} continue
  set fo 0; set sink ""
  foreach it [$net getITerms] {
    if {[$it isOutputSignal]} continue
    incr fo
    if {[[$it getMTerm] getName] eq "CLK"} { set sink "[[$it getInst] getName]/CLK" }
  }
  if {$sink eq ""} continue
  puts "LEAFHDR $n [[$i getMaster] getName] fo $fo sink $sink"
  report_checks -from [get_pins $sink] -path_delay max -format full_clock_expanded -digits 2 -group_path_count 1
}
