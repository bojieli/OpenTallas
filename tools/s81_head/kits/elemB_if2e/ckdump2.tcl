# PATH-S81/ELEMB diag: per-sink clock arrival + clock ancestry, and hold census (one corner per process).
# env C=TT|FF, ODB, MODE=grt (estimate_parasitics -global_routing with /work/setRC_rcx.tcl) | spef (SPEF=...), OUT dir
set C $::env(C); set c [string tolower $C]
read_db $::env(ODB)
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*] { read_liberty $f }
read_liberty /work/macros/ot_rom_4096x274_m8_${c}.lib
read_sdc /work/constraint.sdc
if {$C eq "FF"} { read_sdc /work/vclk_ff.sdc }
set_propagated_clock [get_clocks clk]
if {$::env(MODE) eq "spef"} { read_spef $::env(SPEF) } else { source /work/setRC_rcx.tcl; estimate_parasitics -global_routing }
report_worst_slack -max
set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set per 833.0
proc anc {inst} {
  set out {}; set cur $inst
  for {set k 0} {$k < 60} {incr k} {
    set ckit ""
    foreach it [$cur getITerms] { set n [$it getNet]; if {$n eq "NULL"} continue
      if {[$n getSigType] ne "CLOCK"} continue; if {[[$it getMTerm] getIoType] ne "INPUT"} continue; set ckit $it; break }
    if {$ckit eq ""} break
    set drv ""; foreach it [[$ckit getNet] getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT"} { set drv [$it getInst]; break } }
    if {$drv eq ""} break
    lappend out [$drv getName]; set cur $drv
  }
  return $out
}
set fh [open $::env(OUT)/ck_$c.tsv w]
foreach inst [$blk getInsts] {
  set m [$inst getMaster]; set mn [$m getName]
  set isreg [regexp {DFF|DHL|DLL|SDF|ICG} $mn]; set isbuf [regexp {^(BUF|CLKBUF|INV|HB|CKINV)} $mn]; set ismac [$m isBlock]
  if {!($isreg || $isbuf || $ismac)} continue
  set ckp ""
  foreach it [$inst getITerms] { set n [$it getNet]; if {$n eq "NULL"} continue
    if {[$n getSigType] ne "CLOCK"} continue; if {[[$it getMTerm] getIoType] ne "INPUT"} continue; set ckp $it; break }
  if {$ckp eq ""} continue
  set p [get_pins -quiet "[$inst getName]/[[$ckp getMTerm] getName]"]
  set a NA; if {$p ne ""} { catch {set a [get_property $p arrival_max_rise]} }
  if {[string is double -strict $a] && $a >= $per/2.0 && $a < $per} { set a [expr {$a - $per/2.0}] }
  set bb [$inst getBBox]
  set x [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}]; set y [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}]
  set kind [expr {$ismac ? "MAC" : ($isreg ? "REG" : "BUF")}]
  set an [anc $inst]
  puts $fh [join [list $kind [$inst getName] $mn [format %.2f $x] [format %.2f $y] $a [llength $an] [join $an ,]] "\t"]
}
close $fh
puts [format "STA_$C setup_wns %.2f viol %d hold_wns %.2f viol %d" [sta::time_sta_ui [sta::worst_slack_cmd max]] [sta::endpoint_violation_count max] [sta::time_sta_ui [sta::worst_slack_cmd min]] [sta::endpoint_violation_count min]]
report_checks -path_delay min -slack_max 0 -group_path_count 5000 -endpoint_path_count 1 -format end > $::env(OUT)/hold_end_$C.rpt
report_checks -path_delay min -slack_max 0 -group_path_count 3000 -endpoint_path_count 1 -fields {} -format full > $::env(OUT)/hold_paths_$C.rpt
puts DONE_$C
