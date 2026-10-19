read_db /baseline/results/asap7/sf6u_source_census/base/1_synth.odb
set block [ord::get_db_block]
proc is_trans {inst} {return [regexp -nocase {^(BUF|INV|HB)[x0-9_]} [[$inst getMaster] getName]]}
proc is_clock_pin {it} {return [regexp -nocase {^(CLK|CK|CP|GCLK|CLKN|CLKB)$} [[$it getMTerm] getName]]}
set out [open /work/all_roots_full.tsv w]
puts $out "root\tkind\tloads\tflop_loads\tmacro_loads\treset_loads\tports\texamples"
foreach net [$block getNets] {
 set drivers {};set labels {};set kind unknown
 foreach it [$net getITerms] {if {[$it getIoType] eq "OUTPUT"} {lappend drivers $it}}
 foreach bt [$net getBTerms] {if {[$bt getIoType] eq "INPUT"} {lappend labels [$bt getName];set kind input}}
 if {[llength $drivers] == 1} {
  set dr [lindex $drivers 0];set inst [$dr getInst];if {[is_trans $inst]} {continue}
  set mn [[$inst getMaster] getName];set kind comb
  if {[regexp -nocase {DFF|SDFF} $mn]} {set kind ff}
  if {[[$inst getMaster] isBlock]} {set kind macro}
  if {[regexp -nocase {TIE|LOGIC[01]} $mn]} {set kind tie}
  set labels [list "[$inst getName]/[[$dr getMTerm] getName]"]
 } elseif {[llength $drivers]>1} {set kind multidriver;set labels [list [$net getName]]}
 if {![llength $labels]} {continue};if {[$net getName] eq "ck"} {continue}
 set queue [list $net];set seen [dict create];set sinkset [dict create];set nflop 0;set nmacro 0;set nrst 0;set nport 0;set examples {}
 while {[llength $queue]} {
  set nn [lindex $queue end];set queue [lrange $queue 0 end-1];set id [$nn getId]
  if {[dict exists $seen $id]} {continue};dict set seen $id 1
  foreach bt [$nn getBTerms] {if {[$bt getIoType] eq "OUTPUT"} {set label "port:[$bt getName]";if {![dict exists $sinkset $label]} {dict set sinkset $label 1;incr nport;lappend examples $label}}}
  foreach it [$nn getITerms] {
   if {[$it getIoType] ni {INPUT INOUT} || [is_clock_pin $it]} {continue}
   set inst [$it getInst]
   if {[is_trans $inst]} {
    foreach op [$inst getITerms] {if {[$op getIoType] eq "OUTPUT" && [$op getNet] ne "NULL"} {lappend queue [$op getNet]}}
   } else {
    set label "[$inst getName]/[[$it getMTerm] getName]"
    if {[dict exists $sinkset $label]} {continue};dict set sinkset $label 1
    if {[regexp -nocase {DFF|SDFF} [[$inst getMaster] getName]]} {incr nflop}
    if {[[$inst getMaster] isBlock]} {incr nmacro}
    if {[regexp -nocase {RESET|RST|CLR|PRESET|SETN} [[$it getMTerm] getName]]} {incr nrst}
    if {[llength $examples]<6} {lappend examples $label}
   }
  }
 }
 puts $out "[join $labels ,]\t$kind\t[dict size $sinkset]\t$nflop\t$nmacro\t$nrst\t$nport\t[join [dict keys $sinkset] ,]"
}
close $out

puts "PICKUP_NATIVE_DUMP_DONE"

set out [open /work/cells.tsv w]
puts $out "instance\tmaster\tkind\tarea_um2"
set u [$block getDbUnitsPerMicron]
foreach i [$block getInsts] {
 set m [$i getMaster];set mn [$m getName];set kind comb
 if {[is_trans $i]} {set kind transparent}
 if {[regexp -nocase {DFF|SDFF} $mn]} {set kind ff}
 if {[$m isBlock]} {set kind macro}
 if {[regexp -nocase {TIE|LOGIC[01]} $mn]} {set kind tie}
 puts $out "[$i getName]\t$mn\t$kind\t[expr {double([$m getWidth])*[$m getHeight]/$u/$u}]"
}
close $out
