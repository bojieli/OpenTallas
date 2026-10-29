read_db $::env(ODB)
set b [ord::get_db_block]
foreach spec {u_twpd/q\[299\]$_DFF_P_ _5446_ u_twpd/q\[378\]$_DFF_P_ _4725_ _6555_ u_twpd/q\[357\]$_DFF_P_ _5437_ _6135_} {
  set i [$b findInst $spec]; if {$i eq "NULL"} { puts "NF $spec"; continue }
  foreach it [$i getITerms] { if {![$it isInputSignal]} continue; set n [$it getNet]; if {$n eq "NULL"} continue
    set mt [[$it getMTerm] getName]; if {$mt ne "D" && $mt ne "A"} continue
    set drv ""; set ns 0; set xs {}
    foreach x [$n getITerms] { set bb [[$x getInst] getBBox]; set xy "[expr {[$bb xMin]/1000.0}],[expr {[$bb yMin]/1000.0}]"; if {[$x isOutputSignal]} { set drv "[[$x getInst] getName]([[[$x getInst] getMaster] getName])@$xy" } else { incr ns; lappend xs $xy } }
    foreach bt [$n getBTerms] { set drv "PORT [$bt getName]" }
    puts "$spec/$mt net [$n getName] drv $drv sinks $ns [lrange $xs 0 5]"
  }
}
exit
