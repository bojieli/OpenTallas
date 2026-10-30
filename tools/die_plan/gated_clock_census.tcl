# Read-only native gated-clock inventory; no STA, clock rewiring or physical edits.
# env ODB OUT CLK. Preserve each actual CLK/ENA/GCLK domain rather than treating
# an ICG as a flop endpoint or bypassing its enable function.
read_db $::env(ODB)
set b [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
proc xy {it} {
  set r [$it getBBox]
  return [list [expr {([$r xMin]+[$r xMax])/2.0/$::u}] [expr {([$r yMin]+[$r yMax])/2.0/$::u}]]
}
proc rect {r} {
  return [list [expr {[$r xMin]/double($::u)}] [expr {[$r yMin]/double($::u)}] [expr {[$r xMax]/double($::u)}] [expr {[$r yMax]/double($::u)}]]
}
set bt [$b findBTerm $::env(CLK)]
if {$bt eq "NULL" || [$bt getNet] eq "NULL"} { error "declared root clock missing/unconnected" }
set out [open $::env(OUT) w]
puts $out [join [concat [list DIE] [rect [$b getDieArea]]] \t]
puts $out [join [concat [list CORE] [rect [$b getCoreArea]]] \t]
puts $out [join [list ROOT [$bt getName] [[$bt getNet] getName]] \t]
foreach bp [$bt getBPins] {
 foreach bx [$bp getBoxes] {
  puts $out [join [concat [list ROOT_RECT [[$bx getTechLayer] getName]] [rect $bx]] \t]
 }
}
set todo [list [list [$bt getNet] ROOT]]
set visited [dict create];set gates [dict create];set sinks [dict create]
set pass 0;set macros 0;set flops 0
while {[llength $todo]} {
 lassign [lindex $todo 0] net domain;set todo [lrange $todo 1 end]
 set nn [$net getName]
 if {[dict exists $visited $nn]} {
  if {[dict get $visited $nn] ne $domain} {error "clock net $nn reached from different gated domains"}
  continue
 }
 dict set visited $nn $domain
 foreach it [$net getITerms] {
  if {[$it getIoType] ne "INPUT"} {continue}
  set inst [$it getInst];set master [$inst getMaster];set mn [$master getName];set name [$inst getName]
  set pin [[$it getMTerm] getName]
  if {[regexp {^ICG} $mn]} {
   if {$pin ne "CLK"} {error "clock network feeds non-CLK ICG pin $name/$pin"}
   if {[dict exists $gates $name]} {error "ICG reached more than once: $name"}
   set pins [dict create]
   foreach p [$inst getITerms] {dict set pins [[$p getMTerm] getName] $p}
   foreach required {CLK ENA GCLK} {
    if {![dict exists $pins $required] || [[dict get $pins $required] getNet] eq "NULL"} {error "incomplete native ICG $name/$required"}
   }
   set ci [dict get $pins CLK];set en [dict get $pins ENA];set go [dict get $pins GCLK]
   dict set gates $name $domain
   puts $out [join [concat [list GATE $name $mn $domain [[$ci getNet] getName] [[$en getNet] getName] [[$go getNet] getName]] [xy $ci] [xy $en] [xy $go]] \t]
   foreach p [$inst getITerms] {
    set pn [$p getNet];set nn_pin UNCONNECTED
    if {$pn ne "NULL"} {set nn_pin [$pn getName]}
    puts $out [join [concat [list GATE_PIN $name [[$p getMTerm] getName] [$p getIoType] $nn_pin] [xy $p]] \t]
   }
   lappend todo [list [$go getNet] $name]
  } elseif {[regexp {BUF|INV} $mn] && ![$master isBlock]} {
   set outputs 0
   foreach p [$inst getITerms] {
    if {[$p getIoType] eq "OUTPUT" && [$p getNet] ne "NULL"} {
     incr outputs
     puts $out [join [concat [list PASS $name $mn $domain $pin [[$p getMTerm] getName] $nn [[$p getNet] getName]] [xy $it] [xy $p]] \t]
     lappend todo [list [$p getNet] $domain]
    }
   }
   if {!$outputs} {error "clock pass cell has no output: $name"}
   incr pass
  } elseif {[[$it getMTerm] getSigType] eq "CLOCK" || [regexp -nocase {^(CLK|CK)$} $pin]} {
   set key "$name/$pin"
   if {[dict exists $sinks $key]} {error "clock sink reached more than once: $key"}
   dict set sinks $key $domain
   if {[$master isBlock]} {
    puts $out [join [concat [list MACRO $domain $name $mn $pin $nn] [xy $it] [rect [$inst getBBox]]] \t]
    incr macros
   } else {
    puts $out [join [concat [list SINK $domain $name $mn $pin $nn] [xy $it]] \t]
    incr flops
   }
  } else {
   error "unsupported clock-net input $name/$pin ($mn); no implicit clock traversal"
  }
 }
}
puts $out [join [list COUNTS $flops $macros [dict size $gates] $pass [dict size $visited]] \t]
close $out
puts "GATED_CLOCK_CENSUS flops=$flops macros=$macros gates=[dict size $gates] pass=$pass"
exit
