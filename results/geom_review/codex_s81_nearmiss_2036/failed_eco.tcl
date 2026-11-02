
proc so {k args} { puts "SO $k [join $args { }]" }
proc so_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f [sta::time_sta_ui $t]] }
# Resolve the exact libraries selected by this kit's ORFS make configuration.
# No directory glob or installed-version fallback is permitted.
proc ot_lib_json_string {value} {
  return "\"[string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $value]\""
}
proc ot_lib_validate {corner files} {
  if {$corner ni {TT FF SS}} {error "OT_TIMING_LIBS: unsupported corner $corner"}
  if {![llength $files]} {error "OT_TIMING_LIBS: empty exact library list"}
  set seen {}; set groups {}; set present {}
  foreach f $files {
    if {[file pathtype $f] ne "absolute"} {error "OT_TIMING_LIBS: relative library $f"}
    if {[regexp {[*?\[\]$]} $f] || ![file isfile $f]} {error "OT_TIMING_LIBS: missing or unresolved library $f"}
    set path [file normalize $f]
    if {[dict exists $seen $path]} {error "OT_TIMING_LIBS: duplicate library $f"}
    dict set seen $path 1
    if {[regexp {^asap7sc7p5t_([^_]+)_(RVT|LVT|SLVT)_(TT|FF|SS)_nldm_} [file tail $f] -> group vt actual]} {
      if {$actual ne $corner} {error "OT_TIMING_LIBS: wrong corner $f"}
      set key $group/$vt
      if {[dict exists $groups $key]} {error "OT_TIMING_LIBS: ambiguous installed versions for $key"}
      dict set groups $key $path
      dict set present $group 1
    } elseif {[regexp -nocase {_(tt|ff|ss|typ)\.lib(?:\.gz)?$} [file tail $f] -> actual]} {
      set actual [string toupper $actual]
      if {$actual eq "TYP"} {set actual TT}
      if {$actual ne $corner} {error "OT_TIMING_LIBS: wrong macro corner $f"}
    }
  }
  foreach group {AO INVBUF OA SEQ SIMPLE} {
    if {![dict exists $present $group]} {error "OT_TIMING_LIBS: missing standard-cell group $group"}
  }
  return $files
}
proc ot_lib_resolve {corner {config /work/config.mk}} {
  if {![file isfile $config]} {error "OT_TIMING_LIBS: missing exact ORFS config $config"}
  set field [dict get {TT TC_LIB_FILES FF BC_LIB_FILES SS WC_LIB_FILES} $corner]
  set output [exec bash -c {source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 || exit; exec make --no-print-directory -s -C /OpenROAD-flow-scripts/flow "DESIGN_CONFIG=$1" "print-$2"} otlibs $config $field]
  set records {}
  foreach line [split $output \n] {
    if {[regexp "^${field}\\s*\[:=\]\\s*(.*)$" $line -> value]} {lappend records $value}
  }
  if {[llength $records] != 1} {error "OT_TIMING_LIBS: missing or ambiguous make $field result"}
  set files [regexp -all -inline {\S+} [lindex $records 0]]
  return [ot_lib_validate $corner $files]
}
proc ot_lib_load {corner receipt {config /work/config.mk}} {
  if {[file exists $receipt]} {file rename $receipt ${receipt}.previous.[clock clicks]}
  set files [ot_lib_resolve $corner $config]
  set rows {}
  foreach f $files {
    set digest [lindex [exec sha256sum -- $f] 0]
    lappend rows "{\"path\":[ot_lib_json_string $f],\"sha256\":[ot_lib_json_string $digest]}"
  }
  set digest [lindex [exec sha256sum -- $config] 0]
  foreach f $files {read_liberty $f}
  set fp [open $receipt w]
  puts $fp "{\"status\":\"LOADED\",\"corner\":[ot_lib_json_string $corner],\"source\":\"ORFS make print corner LIB_FILES\",\"config\":[ot_lib_json_string $config],\"config_sha256\":[ot_lib_json_string $digest],\"libraries\":\[[join $rows ,]\]}"
  close $fp
  puts "OT_TIMING_LIBS $corner exact_count [llength $files] receipt $receipt"
  return $files
}

ot_lib_load FF /out/libraries.json
read_db /base/6_final.odb
# FLOW 10-26 PG: every POWER/GROUND MTerm of every instance master bound to a net of that type in the signed ODB
# (global_connect skips dont_touch cells: s8b ot_ms_* spine buffers had VDD/VSS open in 6_final.odb).
set so_pg_terms 0; set so_pg_open 0; set so_pg_first "-"
foreach so_i [[ord::get_db_block] getInsts] {
  foreach so_mt [[$so_i getMaster] getMTerms] {
    set so_r [$so_mt getSigType]
    if {$so_r ni {POWER GROUND}} continue
    incr so_pg_terms
    set so_t [$so_i findITerm [$so_mt getName]]
    set so_n NULL
    if {$so_t ne "NULL" && $so_t ne ""} { set so_n [$so_t getNet] }
    if {$so_n eq "NULL" || $so_n eq "" || [$so_n getSigType] ne $so_r} {
      incr so_pg_open
      if {$so_pg_first eq "-"} { set so_pg_first "[$so_i getName]/[$so_mt getName]" }
    }
  }
}
so PG $so_pg_terms $so_pg_open $so_pg_first
read_spef /base/6_final.spef
read_sdc /sdc/golden.sdc

# ---- OWNER 12.24b/c sign-off clock uncertainty (in-session over the golden SDC: a re-sign of a 60 / 25 kit SDC is
# timed at the policy too).  Each overridden kind on every clock and every clock pair; real <-> virtual seam pairs split half / half (counted
# once per seam, gen_phys.UNC_SPLIT).  Nothing else in the golden SDC changes. ----
proc so_unc_apply {kind v split} {
  set virt {}
  foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend virt [get_full_name $c] } }
  set_clock_uncertainty $v -$kind [all_clocks]
  foreach a [all_clocks] {
    foreach b [all_clocks] {
      set seam [expr {([get_full_name $a] in $virt) != ([get_full_name $b] in $virt)}]
      set w [expr {$seam ? ([get_full_name $a] in $virt ? $split : 1.0 - $split) * $v : $v}]
      if {[catch {set_clock_uncertainty -from $a -to $b -$kind $w} msg]} { incr ::so_unc_err; set ::so_unc_msg $msg }
    }
  }
}
set ::so_unc_err 0; set ::so_unc_msg -
if {[catch {so_unc_apply setup 0 0.5} msg]} { incr ::so_unc_err; set ::so_unc_msg $msg }
so UNC_POLICY nominal setup 0 hold 25 kinds setup errors $::so_unc_err
set_propagated_clock [all_clocks]
so CORNER FF
so PARASITICS spef
so DESIGN [current_design]
so CELLS [llength [get_cells *]]
# Inventory actual sequential endpoint masters; a Liberty loaded but unused is
# not evidence of an unexpanded child. Keep the raw pair census unchanged.
set so_endpoint_masters {}; set so_endpoint_mapping_errors 0
foreach p [all_registers -clock_pins] {
  if {[catch {
    set owners [get_cells -quiet -of_objects [list $p]]
    if {[llength $owners] != 1} {error "nonunique clock endpoint owner"}
    set master [get_property [lindex $owners 0] ref_name]
    if {$master eq ""} {error "empty clock endpoint master"}
  }]} {incr so_endpoint_mapping_errors; continue}
  dict set so_endpoint_masters $master 1
}
so CLOCK_ENDPOINT_MASTERS {*}[lsort [dict keys $so_endpoint_masters]]
so CLOCK_ENDPOINT_MAPPING_ERRORS $so_endpoint_mapping_errors
# ---- ports (for sdc_lint context) and IO virtual clock ----
set so_ck_ports {}
foreach c [all_clocks] { foreach s [get_property $c sources] { if {[llength [get_ports -quiet [get_full_name $s]]]} { lappend so_ck_ports [get_full_name $s] } } }
set so_ck_ports [lsort -unique $so_ck_ports]
so CLOCK_PORTS {*}$so_ck_ports
set so_din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $so_ck_ports} { lappend so_din $p } }
so INPUTS {*}[lsort -unique [lmap p $so_din {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
so OUTPUTS {*}[lsort -unique [lmap p [all_outputs] {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
set so_vclk {}
foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend so_vclk $c } }
so CLOCKS {*}[lmap c [all_clocks] {get_full_name $c}]
so VCLKS {*}[lmap c $so_vclk {get_full_name $c}]
foreach c [all_clocks] { so PERIOD [get_full_name $c] [get_property $c period] }
# ---- timing with the block's own SDC ----
proc so_timing {tag} {
  so ${tag}_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
  so ${tag}_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
  so ${tag}_TNS_MAX [so_ps [sta::total_negative_slack_cmd max]]
  so ${tag}_TNS_MIN [so_ps [sta::total_negative_slack_cmd min]]
  so ${tag}_NVIOL_MAX [sta::endpoint_violation_count max]
  so ${tag}_NVIOL_MIN [sta::endpoint_violation_count min]
}
so_timing SDC
puts "SO_PATH_BEGIN SDC_MAX"
report_checks -path_delay max -format full_clock_expanded -digits 2 -fields {slew cap fanout}
puts "SO_PATH_END"
# ---- standard boundary-hold overlay (4b7b2b3e64 kit standard) ----
set so_reference_ok 1

if {[llength $so_vclk] == 1} {
  set_clock_latency -source 202.500000 [lindex $so_vclk 0]
  so FF_VCLK applied mode bound_ff clock [get_full_name [lindex $so_vclk 0]] latency_ps 202.500000
} else {
  set so_reference_ok 0
  so FF_VCLK unavailable mode bound_ff vclks [llength $so_vclk]
}

if {[llength $so_vclk] == 1 && $so_reference_ok} {
  if {[llength $so_din]} { set_input_delay -min [expr {-40}] -clock [lindex $so_vclk 0] $so_din }
  if {[llength [all_outputs]]} { set_output_delay -min 0 -clock [lindex $so_vclk 0] [all_outputs] }
  so OVERLAY applied [get_full_name [lindex $so_vclk 0]] in_min -40 out_min 0
} else {
  so OVERLAY skipped vclks [llength $so_vclk]
}
so_timing STD
puts "SO_PATH_BEGIN STD_MIN"
report_checks -path_delay min -format full_clock_expanded -digits 2
puts "SO_PATH_END"
# ===== S81-CORES-KITS-13 class NEARMISS-PECO stage 1: FF hold to OT_TGT + slew chains (1 auto DRV pins, segment 40.0 um) =====
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set TGT [expr {[info exists ::env(OT_TGT)] ? $::env(OT_TGT) : 10.0}]
set CELL [expr {[info exists ::env(OT_CELL)] ? $::env(OT_CELL) : "HB1xp67_ASAP7_75t_R"}]
set blk [ord::get_db_block]
set ndt0 0; foreach n [$blk getNets] { if {[$n isDoNotTouch]} { $n setDoNotTouch 0; incr ndt0 } }; puts "ECO CLEARED_DT_IN $ndt0"
proc wsig {n} { set w [$n getWire]; if {$w eq "NULL"} { return "-" }; return [$w getLength][$w getId] }
# snapshot: inst locations + net wire signatures
set loc0 {}; foreach i [$blk getInsts] { dict set loc0 [$i getName] [$i getLocation] }
set ws0 {}; foreach n [$blk getNets] { if {[$n getSigType] in {POWER GROUND}} continue; set w [$n getWire]; dict set ws0 [$n getName] [expr {$w eq "NULL" ? "-" : "[$w getLength]/[$w length]"}] }
proc viols {tgt} {
  set r {}
  foreach p [find_timing_paths -path_delay min -group_path_count 1000 -endpoint_path_count 1 -slack_max $tgt -sort_by_slack] {
    lappend r [list [get_property $p slack] [get_full_name [get_property $p endpoint]]]
  }
  return $r
}
set ::SLEWPINS [list {_06381_/A}]
set rk 0
set RB BUFx4f_ASAP7_75t_R
proc ib {net loads x y} {
  global rk; set nm "slweco_$rk"; incr rk
  insert_buffer -buffer_cell $::RB -net $net -load_pins [get_pins $loads] -location [list $x $y] -buffer_name $nm -net_name ${nm}_n
  set b [lindex [get_cells ${nm}*] 0]; set bn [get_full_name $b]
  puts "ECO REPEATER $bn net $net at ([format %.1f $x],[format %.1f $y]) loads [llength $loads]"
  return $bn
}
proc pxy {p} { set c [sta::sta_to_db_inst [get_cells -of_objects [get_pins $p]]]; set l [$c getLocation]; return [list [expr {[lindex $l 0]/1000.0}] [expr {[lindex $l 1]/1000.0}]] }
# generic long-wire slew fix: per violating net, a BUFx4f chain (~40 um segments) from the driver to the violating loads' centroid
set bynet {}
foreach p $::SLEWPINS {
  set n [get_full_name [get_nets -of_objects [get_pins $p]]]
  if {[get_property [get_pins $p] direction] eq "output"} {
    # driver-pin violator: the whole net is the overloaded segment -> chain to all its loads
    foreach q [get_pins -of_objects [get_nets $n] -filter direction==input] { dict lappend bynet $n [get_full_name $q] }
  } else { dict lappend bynet $n $p }
}
dict for {net vl} $bynet {
  set d [get_pins -of_objects [get_nets $net] -filter direction==output]
  lassign [pxy [get_full_name $d]] dx dy
  set cx 0; set cy 0; foreach p $vl { lassign [pxy $p] x y; set cx [expr {$cx+$x}]; set cy [expr {$cy+$y}] }
  set cx [expr {$cx/[llength $vl]}]; set cy [expr {$cy/[llength $vl]}]
  set dist [expr {abs($dx-$cx)+abs($dy-$cy)}]
  set nrep [expr {max(1, int(ceil($dist/40.0))-1)}]
  puts "ECO SLEWNET $net drv [get_full_name $d] ([format %.1f $dx],[format %.1f $dy]) vloads [llength $vl] centroid ([format %.1f $cx],[format %.1f $cy]) dist [format %.1f $dist] reps $nrep"
  set cur $vl
  for {set k 0} {$k < $nrep} {incr k} {
    set f [expr {double($k+1)/($nrep+1)}]
    set b [ib $net $cur [expr {$cx+($dx-$cx)*$f}] [expr {$cy+($dy-$cy)*$f}]]
    set cur [list $b/A]
  }
}
set resized {}
set v0 [viols $TGT]
puts "ECO PRE n_below_tgt [llength $v0] worst [lindex [lindex $v0 0] 0]"
set added {}; set k 0
for {set pass 0} {$pass < 6} {incr pass} {
  set v [viols $TGT]
  if {![llength $v]} break
  puts "ECO PASS $pass below [llength $v] worst [lindex [lindex $v 0] 0]"
  foreach e $v {
    lassign $e sl pin
    if {[llength [get_ports -quiet $pin]]} {
      # output-port hold endpoint: pad before the port driver (its input pin = load)
      set bt [$blk findBTerm $pin]; set onet [$bt getNet]; set dpi ""
      foreach itm [$onet getITerms] { if {[$itm isOutputSignal]} { set dpi $itm } }
      set dinst [$dpi getInst]; set ipin ""
      foreach itm [$dinst getITerms] { if {[$itm isInputSignal]} { set ipin "[$dinst getName]/[[$itm getMTerm] getName]" } }
      set pt [get_pins $ipin]
      puts "ECO PORT_HOLD $pin -> [get_full_name $pt]"
    } else { set pt [get_pins $pin] }
    set net [get_nets -of_objects $pt]
    set inst [sta::sta_to_db_inst [get_cells -of_objects $pt]]
    set it [$inst findITerm [get_property $pt lib_pin_name]]
    set axy [$it getAvgXY]
    if {[lindex $axy 0]} { set xy [lrange $axy 1 2] } else { set xy [$inst getLocation] }
    set nm "hxeco_$k"; incr k
    insert_buffer -buffer_cell $CELL -net [get_full_name $net] -load_pins [list $pt] -location [list [expr {[lindex $xy 0]/1000.0}] [expr {[lindex $xy 1]/1000.0}]] -buffer_name $nm -net_name ${nm}_n
    lappend added $nm
  }
}
set v1 [viols $TGT]
puts "ECO ADDED [llength $added] still_below [llength $v1] worst_after [expr {[llength $v1] ? [lindex [lindex $v1 0] 0] : "none"}] (no parasitics on new nets yet)"
remove_fillers
set nlock 0
set rsn [lmap r $resized {$r getName}]
foreach i [$blk getInsts] { if {[dict exists $loc0 [$i getName]] && [$i getName] ni $rsn && [$i getPlacementStatus] ni {LOCKED FIRM COVER}} { $i setPlacementStatus FIRM; incr nlock } }
puts "ECO FIRM_EXISTING $nlock"
detailed_placement -use_diamond_legalizer -max_displacement {500 100}
check_placement -verbose
# moved insts
set moved {}; set movedo {}; set newo {}; set newn {}
foreach i [$blk getInsts] {
  set n [$i getName]
  if {[dict exists $loc0 $n] && [dict get $loc0 $n] ne [$i getLocation]} { lappend moved $n; lappend movedo $i }
  if {![dict exists $loc0 $n]} { lappend newo $i; lappend newn $n }
}
puts "ECO MOVED [llength $moved] [lrange $moved 0 20]"
# dirty nets = nets on added or moved insts
set dirty {}
puts "ECO NEW_INSTS [llength $newo] [lrange $newn 0 5]"
foreach i [concat $newo $movedo $resized] {
  foreach it [$i getITerms] { set nt [$it getNet]; if {$nt ne "NULL" && [$nt getSigType] ni {POWER GROUND}} { dict set dirty [$nt getName] 1 } }
}
puts "ECO DIRTY_NETS [dict size $dirty]"
foreach n [dict keys $dirty] { set nt [$blk findNet $n]; set w [$nt getWire]; if {$w ne "NULL"} { odb::dbWire_destroy $w } }
set_routing_layers -signal M2-M5 -clock M2-M5
set ndt 0
foreach n [$blk getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  if {[dict exists $dirty [$n getName]]} continue
  if {[$n getWire] ne "NULL"} { $n setDoNotTouch 1; incr ndt }
}
puts "ECO DONT_TOUCH_NETS $ndt"
global_route -allow_congestion
detailed_route -output_drc /out/eco_drc.rpt -verbose 1
filler_placement {FILLERxp5_ASAP7_75t_R FILLER_ASAP7_75t_R DECAPx1_ASAP7_75t_R DECAPx2_ASAP7_75t_R DECAPx4_ASAP7_75t_R DECAPx6_ASAP7_75t_R DECAPx10_ASAP7_75t_R}
check_placement -verbose
# untouched nets keep their wires?
set same 0; set chg 0; set chg_names {}
foreach n [$blk getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  set nm [$n getName]
  if {[dict exists $dirty $nm] || ![dict exists $ws0 $nm]} continue
  set w [$n getWire]; set s [expr {$w eq "NULL" ? "-" : "[$w getLength]/[$w length]"}]
  if {$s eq [dict get $ws0 $nm]} { incr same } else { incr chg; if {[llength $chg_names] < 10} { lappend chg_names $nm } }
}
puts "ECO UNTOUCHED_NETS same $same changed $chg $chg_names"
foreach n [$blk getNets] { $n setDoNotTouch 0 }
write_db /out/6_final.odb
puts "ECO DONE"
exit
