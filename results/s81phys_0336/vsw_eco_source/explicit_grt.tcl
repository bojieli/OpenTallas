# PRIVATE PREP ONLY. Exact40 DATA branch insertion. No generic repair_timing, DPL, CTS, clock/FF/SDC change.
# Caller loads canonical TT exact-library/native833ps SDC context and original finalODB+SPEF.
set b [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
if {[llength [all_clocks]] != 2 || abs([get_property [get_clocks clk] period]-833.0)>1e-6} {error "VSW_ECO wrong native clock context"}
if {![grt::have_routes]} {error "VSW_ECO original incremental guides missing; no fresh-GRT fallback"}
set m [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
if {$m eq "NULL" || [$m getWidth] != 378 || [$m getHeight] != 270} {error "VSW_ECO native HB4 master/units mismatch"}
proc resolve_inst {b n} {
  set i [$b findInst $n]
  if {$i eq "NULL"} {set i [$b findInst [string map [list "\[" "\\\[" "\]" "\\\]"] $n]]}
  if {$i eq "NULL"} {error "VSW_ECO instance missing: $n"}
  return $i
}
proc resolve_iterm {i n} {
  set it [$i findITerm $n]
  if {$it eq "NULL"} {set it [$i findITerm [string map [list "\[" "\\\[" "\]" "\\\]"] $n]]}
  if {$it eq "NULL"} {error "VSW_ECO terminal missing: [$i getName]/$n"}
  return $it
}
proc member_names {net} {
  set out {}; foreach it [$net getITerms] {lappend out "[[$it getInst] getName]/[[$it getMTerm] getName]"}
  return [lsort $out]
}
set clocks [open /work/eco/clock_names.txt w]
foreach n [$b getNets] {if {[$n getSigType] eq "CLOCK"} {puts $clocks [$n getName]}}
close $clocks
write_def /work/eco/before.def
source /work/eco/targets.tcl
if {[llength $targets] != 40} {error "VSW_ECO expected exactly40 branches"}
# Check all40 targets, homes and source fanouts before mutating the private copy.
set records {}; set filler_remove [dict create]
foreach r $targets {
  lassign $r idx inst pin oldnet x y orient expected_fanout
  set i [resolve_inst $b $inst]; set it [resolve_iterm $i $pin]; set nt [$it getNet]
  if {$nt eq "NULL" || [$nt getName] ne $oldnet || [$it getIoType] ne "INPUT" || [$nt getSigType] in {CLOCK POWER GROUND}} {error "VSW_ECO wrong capture branch $inst/$pin"}
  set nf 0; foreach jt [$nt getITerms] {if {[$jt getIoType] eq "INPUT"} {incr nf}}
  if {$nf != $expected_fanout} {error "VSW_ECO sibling fanout changed: $oldnet"}
  set xn [expr {round($x*$u)}]; set yn [expr {round($y*$u)}]
  # The read-only allocation has two-site padding. Check exact new footprints; no existing functional cell may move.
  foreach other [$b getInsts] {
    set bb [$other getBBox]
    if {[$bb xMax]<=$xn || [$bb xMin]>=$xn+378 || [$bb yMax]<=$yn || [$bb yMin]>=$yn+270} continue
    set mn [[$other getMaster] getName]
    if {![string match FILLER* $mn] && ![string match DECAP* $mn]} {error "VSW_ECO occupied HB4 footprint $idx: [$other getName]"}
    dict set filler_remove [$other getName] $other
  }
  set name [format "codex_vsw_hb4_%03d" $idx]; set newnet "${name}_out"
  if {[$b findInst $name] ne "NULL" || [$b findNet $newnet] ne "NULL"} {error "VSW_ECO already executed: $name"}
  lappend records [list $it $nt [member_names $nt] $name $newnet $xn $yn $orient]
}
source /work/setRC_rcx.tcl
set_routing_layers -signal M2-M5
set_global_routing_layer_adjustment M2-M5 0.25
global_route -start_incremental
dict for {name inst} $filler_remove {odb::dbInst_destroy $inst}
set dirty [dict create]
foreach r $records {
  lassign $r it oldnet before name nn x y orient
  set target "[[$it getInst] getName]/[[$it getMTerm] getName]"
  set i [odb::dbInst_create $b $m $name]; $i setOrient $orient; $i setLocation $x $y; $i setPlacementStatus PLACED
  set nt [odb::dbNet_create $b $nn]
  $it disconnect
  [$i findITerm A] connect $oldnet
  [$i findITerm Y] connect $nt
  $it connect $nt
  set expect [lsort [concat [lsearch -all -inline -not -exact $before $target] [list "$name/A"]]]
  if {[member_names $oldnet] ne $expect || [member_names $nt] ne [lsort [list "$name/Y" $target]]} {error "VSW_ECO sibling/branch-cut mismatch: $name"}
  dict set dirty [$oldnet getName] 1; dict set dirty $nn 1
}
source /work/pg_connect.tcl
ot_pg_connect_all VSW_EXPLICIT40
ot_pg_require_bound VSW_EXPLICIT40
check_placement -verbose
set df [open /work/eco/dirty_nets.txt w]
dict for {name unused} $dirty {
  set nt [$b findNet $name]; if {[$nt getSigType] in {CLOCK POWER GROUND}} {error "VSW_ECO attempted clock/PG reroute"}
  set wire [$nt getWire]; if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
  puts $df $name
}
close $df
# Same original-route guide strategy as hold_eco.tcl; exactly80 dirty DATA nets, all existing clock/detailed wires retained.
if {[dict size $dirty] != 80} {error "VSW_ECO dirty-net count differs"}
global_route -end_incremental -resistance_aware
write_def /work/eco/after_grt.def
write_db /work/eco/5_1_explicit_grt.odb
write_sdc /work/eco/5_1_explicit_grt.sdc
puts "VSW_EXPLICIT40_GRT_DONE noSYNTH/GPL/CTS/DPL/DRT; clock/nativecell assertions and canonicalG2 still REQUIRED"
