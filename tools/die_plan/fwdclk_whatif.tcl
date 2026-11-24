# KV-HG-CAP ENTRYFOOT what-if (from kv-sender-skew eco3.tcl): rings with source hop > 300 um -> PASS-th nearest kit tap within 300 um; min/max data-fclk before/after, placement RC; read-only
# KV-SENDER-SKEW read-only what-if v2: every fclk_out whose source tap is > 150 um away and not nearest -> sink of the nearest
# tap's own (non-regs) leaf level; per ring min AND max of (data - fclk_out) before/after, placement RC.  Nothing written back.
source $::env(SCRIPTS_DIR)/load.tcl
load_design $::env(VIS_ODB) $::env(VIS_SDC)
set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set m [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]; set ca [$blk getCoreArea]
proc ctr {o} { set b [$o getBBox]; list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}] }
proc md {a b} { global dbu; expr {(abs([lindex $a 0]-[lindex $b 0])+abs([lindex $a 1]-[lindex $b 1]))/double($dbu)} }
proc upport {net} {
  for {set n 0} {$n < 300 && $net ne "NULL"} {incr n} {
    foreach b [$net getBTerms] { if {[$b getIoType] eq "INPUT"} { return [$b getName] } }
    set drv ""; foreach it [$net getITerms] { if {[$it isOutputSignal]} { set drv $it } }
    if {$drv eq ""} { return "" }
    set up "NULL"; foreach it [[$drv getInst] getITerms] { if {[$it isInputSignal]} { set up [$it getNet] } }
    set net $up
  }
  return ""
}
# signal nets hold the hook for each tap: leaf nets by name
array set leafs {}
foreach nn [$blk getNets] {
  if {[$nn getSigType] ne "CLOCK"} continue
  if {[regexp {leaf.*_(clk_t\d+)$|leaf.*_(clk)$} [$nn getName] - a b]} { lappend leafs([expr {$a ne "" ? $a : $b}]) $nn }
}
set taps {}
foreach b [$blk getBTerms] { if {[regexp {^clk(_t\d+)?$} [$b getName]] && [$b getIoType] eq "INPUT"} { lappend taps [list [$b getName] [ctr $b]] } }
catch {estimate_parasitics -placement}; catch {set_propagated_clock [all_clocks]}
proc rings {} {
  set out {}
  foreach c [all_clocks] {
    set cn [get_name $c]; if {![string match fclk_out_* $cn]} continue
    set bus [string range $cn 9 end]; set ps {}
    foreach pat [list $bus "$bus\[*\]" "cland_fstart_out_$bus" "cland_fstart_out_$bus\[*\]"] { foreach p [get_ports -quiet $pat] { if {[get_property $p direction] in {output out}} { lappend ps $p } } }
    if {[llength $ps]} { lappend out $cn; set ::rp($cn) $ps }
  }
  return $out
}
proc meas {cns tag} {
  foreach cn $cns {
    foreach {k d} {min min max max} {
      set w ""; set e ""
      foreach pe [find_timing_paths -path_delay $d -to $::rp($cn) -group_path_count 4000 -unique_paths_to_endpoint] {
        set tn ""; catch {set tn [get_name [$pe target_clk]]}; if {$tn ne $cn} continue
        set v [expr {([$pe data_arrival_time]-[$pe target_clk_delay])*1e12}]
        if {$w eq "" || ($d eq "min" ? $v < $w : $v > $w)} { set w $v; set e [expr {[$pe target_clk_delay]*1e12}] }
      }
      set ::R($tag,$cn,$k) $w; set ::R($tag,$cn,f) $e
    }
  }
}
set cns [rings]
foreach cn $cns { set c [get_clocks $cn]; catch {set_output_delay -min 0 -clock $c -add_delay $::rp($cn)}; catch {set_output_delay -max 0 -clock $c -add_delay $::rp($cn)} }
meas $cns b
set k 0
foreach cn $cns {
  set pn $cn; set dst [$blk findBTerm $cn]; if {$dst eq "NULL"} { set pn "$cn\[0\]"; set dst [$blk findBTerm $pn] }
  if {$dst eq "NULL"} continue
  set s [upport [$dst getNet]]; set at($cn) $s; set st($cn) KEEP
  set dx [ctr $dst]; set best ""; set bd 1e9
  foreach t $taps { set d [md $dx [lindex $t 1]]; if {$d < $bd && [lindex $t 0] ne "clk"} { set bd $d; set best [lindex $t 0] } }
  if {$s eq "" || [$blk findBTerm $s] eq "NULL"} { set st($cn) NOSRC; continue }
  set sd0 [md $dx [ctr [$blk findBTerm $s]]]
  if {$sd0 <= 300.0} continue
  set cl {}; foreach t $taps { set d [md $dx [lindex $t 1]]; if {$d <= 300.0 && [lindex $t 0] ne "clk"} { lappend cl [list $d [lindex $t 0]] } }
  set cl [lsort -real -index 0 $cl]
  if {$::env(PASS) >= [llength $cl]} { set st($cn) NOCAND; continue }
  set best [lindex [lindex $cl $::env(PASS)] 1]; set bd [md $dx [ctr [$blk findBTerm $best]]]
  set sd [md $dx [ctr [$blk findBTerm $s]]]; set hop($cn) "$sd $bd [expr {[lindex [ctr [$blk findBTerm $best]] 0]/double($dbu)}] [expr {[lindex [ctr [$blk findBTerm $best]] 1]/double($dbu)}] [expr {[lindex $dx 0]/double($dbu)}] [expr {[lindex $dx 1]/double($dbu)}]"
    if {![info exists leafs($best)]} { set st($cn) "NOLEAF:$best"; continue }
  set tx [ctr [$blk findBTerm $best]]; set ln ""; set ld 1e18
  foreach nn $leafs($best) { foreach it [$nn getITerms] { if {[$it isOutputSignal]} { set d [md [ctr [$it getInst]] $dx]; if {$d < $ld} { set ld $d; set ln $nn; set tx [ctr [$it getInst]] } } } }
  if {$ln eq ""} { set st($cn) "NOLEAFDRV:$best"; continue }
  $dst disconnect
  set i [odb::dbInst_create $blk $m ss_fwd_$cn]
  $i setLocation [expr {min(max([lindex $tx 0],[$ca xMin]),[$ca xMax]-[$m getWidth])}] [expr {min(max([lindex $tx 1]+($k%7)*[$m getHeight],[$ca yMin]),[$ca yMax]-[$m getHeight])}]
  $i setPlacementStatus PLACED; incr k
  [$i findITerm A] connect $ln
  set n [odb::dbNet_create $blk ss_fwd_net_$cn]; [$i findITerm Y] connect $n; $dst connect $n; $n setSigType CLOCK
  set st($cn) "MOVED:$best"
  catch {delete_generated_clock [get_clocks $cn]} 
  create_generated_clock -name $cn -master_clock clk -source [get_ports $best] -divide_by 1 [get_ports $pn]
  set_output_delay -min 0 -clock [get_clocks $cn] -add_delay $::rp($cn); set_output_delay -max 0 -clock [get_clocks $cn] -add_delay $::rp($cn)
}
catch {estimate_parasitics -placement}; catch {set_propagated_clock [all_clocks]}
meas $cns a
set o [open /out/eco3.tsv w]
puts $o "clk\tstate\told_tap\thops\tmin_b\tmax_b\tfclk_b\tmin_a\tmax_a\tfclk_a"
foreach cn $cns { catch {puts $o "$cn\t$st($cn)\t$at($cn)\t[expr {[info exists hop($cn)] ? $hop($cn) : {}}]\t$R(b,$cn,min)\t$R(b,$cn,max)\t$R(b,$cn,f)\t$R(a,$cn,min)\t$R(a,$cn,max)\t$R(a,$cn,f)"} }
close $o; puts OT_ECO2_DONE
