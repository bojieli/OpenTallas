# DIE-QC-38 A0: per-stage clock delay + hold-pair classification dump on the kept cts_prehold.odb (diagnostic only).
# env: ODB, OT_CORNER (TT|FF), OUT (prefix), KIT (/work), PLACE_SDC; FF also reads /work/vclk_ff.sdc (the flow's FF hold SDC).
set C $::env(OT_CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db $::env(ODB)
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_sdc $::env(PLACE_SDC)
if {$C eq "FF"} { read_sdc /work/vclk_ff.sdc }
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
puts "OT38_WS_MIN [expr {[sta::worst_slack_cmd min]*1e12}] OT38_WS_MAX [expr {[sta::worst_slack_cmd max]*1e12}]"
set blk [ord::get_db_block]
set dbu [$blk getDefUnits]
proc esc {n} { string map {[ \\[ ] \\]} $n }
proc arr {p k} { set v [get_property $p $k]; if {$v eq ""} { return NA }; return [format %.2f $v] }
proc xy {inst} { global dbu
  set d [sta::sta_to_db_inst $inst]; set b [$d getBBox]
  return [format "%.2f\t%.2f" [expr {($b xMin)/double($dbu)}] [expr {($b yMin)/double($dbu)}]] }
proc xyb {inst} { global dbu
  set d [sta::sta_to_db_inst $inst]; set b [$d getBBox]
  return [format "%.2f\t%.2f" [expr {([$b xMin]+[$b xMax])/2.0/$dbu}] [expr {([$b yMin]+[$b yMax])/2.0/$dbu}]] }
if {![info exists ::env(SKIP_TREE)] || $::env(SKIP_TREE) eq ""} {
set fo [open $::env(OUT)_tree_${c}.tsv w]
puts $fo "kind\tinst\tmaster\tparent\tdepth\tx\ty\tin_pin\tin_max_r\tin_min_r\tout_max_r\tout_min_r\tfanout"
set q [list [list [get_nets ck] port:ck 0]]
set seen [dict create]
while {[llength $q]} {
  set e [lindex $q 0]; set q [lrange $q 1 end]
  lassign $e net par d
  set loads [get_pins -quiet -of_objects $net -filter "direction==input"]
  foreach p $loads {
    set i [get_cells -of_objects $p]; set in [get_full_name $i]; set m [get_property $i ref_name]
    set pn [get_property $p lib_pin_name]
    set isbuf [expr {[regexp {^(BUF|INV|ICG|CKINV|HB)} $m] && $pn in {A CLK}}]
    if {$isbuf} {
      if {[dict exists $seen $in]} continue
      dict set seen $in 1
      set op [get_pins -of_objects $i -filter "direction==output"]
      set on [get_nets -quiet -of_objects $op]
      set fn [expr {$on eq "" ? 0 : [llength [get_pins -quiet -of_objects $on -filter "direction==input"]]}]
      puts $fo "node\t$in\t$m\t$par\t[expr {$d+1}]\t[xyb $i]\t$pn\t[arr $p arrival_max_rise]\t[arr $p arrival_min_rise]\t[arr $op arrival_max_rise]\t[arr $op arrival_min_rise]\t$fn"
      if {$on ne ""} { lappend q [list $on $in [expr {$d+1}]] }
    } else {
      puts $fo "sink\t$in\t$m\t$par\t[expr {$d+1}]\t[xyb $i]\t$pn\t[arr $p arrival_max_rise]\t[arr $p arrival_min_rise]\tNA\tNA\t0"
    }
  }
}
close $fo
}
# hold pairs: driver of each failing endpoint pin (zero-logic test) -- endpoints from the flow's diag hold_fail.tsv
if {[info exists ::env(HOLD_TSV)]} {
  set fi [open $::env(HOLD_TSV)]; gets $fi
  set fh [open $::env(OUT)_holdpairs_${c}.tsv w]
  puts $fh "endpoint\tdrv_inst\tdrv_master\tdrv_pin\tnlevels_buf\tchain"
  while {[gets $fi line] >= 0} {
    set ep [lindex [split $line \t] 2]
    if {[string first / $ep] < 0} { puts $fh "$ep\tPORT\tNA\tNA\t0"; continue }
    set p [get_pins -quiet [esc $ep]]
    if {$p eq ""} { puts $fh "$ep\tNOTFOUND\tNA\tNA\t0"; continue }
    set n [get_nets -quiet -of_objects $p]
    set k 0; set di NA; set dm NA; set dp NA; set chain {}
    while {$n ne "" && $k < 8} {
      set dpin [get_pins -quiet -of_objects $n -filter "direction==output"]
      if {$dpin eq ""} { set di PORTIN; break }
      set i [get_cells -of_objects [lindex $dpin 0]]; set di [get_full_name $i]; set dm [get_property $i ref_name]
      set dp [get_property [lindex $dpin 0] lib_pin_name]
      # walk through hold/repair-free buffers only (none expected pre-hold); stop at any non-buffer
      if {[regexp {^(BUF|HB|INV)} $dm]} { incr k; lappend chain [string map {_ASAP7_75t_R ""} $dm]; set n [get_nets -quiet -of_objects [get_pins -of_objects $i -filter "lib_pin_name==A"]]; continue }
      break
    }
    puts $fh "$ep\t$di\t$dm\t$dp\t$k\t[join $chain ,]"
  }
  close $fi; close $fh
}
puts OT38_DONE
