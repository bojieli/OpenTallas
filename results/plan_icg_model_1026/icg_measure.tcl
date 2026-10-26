# PLAN-ICG-MODEL measurement probe (read-only, diagnostic): routed 6_final ODB + SPEF, one corner.
# Walks the clock net forward from the clock source through BUF/INV/ICG stages; writes every stage cell
# (input arrival, output arrival, fanout, xy, depth, owning ICG, stages below that ICG) and every sink.
set c $::env(CORNER); set lo [string tolower $c]
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_${c}*] {read_liberty $f}
foreach f [glob -nocomplain /macros/*_${lo}.lib] {read_liberty $f}
read_db /work/6_final.odb
read_sdc /work/6_final.sdc
read_spef /work/6_final.spef
set_propagated_clock [get_clocks core_clk]
report_worst_slack -max
set clk [get_clocks core_clk]
set src [lindex [get_property $clk sources] 0]
puts "OT_ICGM clock [get_name $clk] src [get_full_name $src]"
set block [ord::get_db_block]
set bterm [$block findBTerm [get_full_name $src]]
set net0 [$bterm getNet]
set dbu [$block getDbUnitsPerMicron]
proc esc {n} {if {[string first "\\" $n] >= 0} {return $n}; return [string map [list "\[" "\\\[" "\]" "\\\]"] $n]}
proc arr {pinname} {
  set p [get_pins -quiet [esc $pinname]]
  if {$p eq ""} {return NA}
  set a [get_property $p arrival_max_rise]
  if {$a eq "" || $a eq "INF" || $a eq "-INF"} {return NA}
  return [format %.3f [expr {$a}]]
}
proc slw {pinname} {
  set p [get_pins -quiet [esc $pinname]]
  if {$p eq ""} {return NA}
  set s [get_property $p slew_max]
  if {$s eq ""} {return NA}
  return [format %.3f [expr {$s}]]
}
set fs [open /work/out/stages_${c}.tsv w]; set fk [open /work/out/sinks_${c}.tsv w]
puts $fs "name\tmaster\tkind\tx_um\ty_um\tdepth\ticg\tbelow_icg\tparent\tin_arr\tout_arr\tin_slew\tfanout"
puts $fk "pin\tmaster\tx_um\ty_um\tdepth\ticg\tbelow_icg\tdriver\tarr\tslew"
# queue: net, depth, icg, below, parent
set q [list [list $net0 0 ROOT 0 PORT]]
set ns 0; set nk 0
while {[llength $q]} {
  set e [lindex $q 0]; set q [lrange $q 1 end]
  lassign $e net d icg below parent
  foreach it [$net getITerms] {
    if {[$it isOutputSignal]} continue
    set inst [$it getInst]; set m [[$inst getMaster] getName]; set mt [[$inst getMaster] getType]
    set pin [[$it getMTerm] getName]; set iname [$inst getName]
    set bb [$inst getBBox]; set x [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}]; set y [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}]
    set kind ""
    if {[regexp {^ICG} $m] && $pin eq "CLK"} {set kind icg; set op GCLK} \
    elseif {[regexp {^(BUF|INV|CKINV|HB)} $m] && $pin eq "A"} {set kind [expr {[regexp {^INV} $m] ? "inv" : "buf"}]; set op Y}
    if {$kind ne ""} {
      set onet [[$inst findITerm $op] getNet]
      set fo [expr {$onet eq "NULL" ? 0 : [llength [$onet getITerms]] - 1}]
      if {$kind eq "icg"} {set nicg $iname; set nb 0} else {set nicg $icg; set nb [expr {$below+1}]}
      set pp [string map {\\ {}} $iname]
      puts $fs [join [list $iname $m $kind [format %.3f $x] [format %.3f $y] [expr {$d+1}] $icg $below $parent [arr $iname/[expr {$kind eq "icg" ? "CLK" : "A"}]] [arr $iname/$op] [slw $iname/[expr {$kind eq "icg" ? "CLK" : "A"}]] $fo] "\t"]
      incr ns
      if {$onet ne "NULL"} {lappend q [list $onet [expr {$d+1}] $nicg $nb $iname]}
    } else {
      puts $fk [join [list $iname/$pin $m [format %.3f $x] [format %.3f $y] $d $icg $below $parent [arr $iname/$pin] [slw $iname/$pin]] "\t"]
      incr nk
    }
  }
}
close $fs; close $fk
puts "OT_ICGM_DONE $c stages $ns sinks $nk"
