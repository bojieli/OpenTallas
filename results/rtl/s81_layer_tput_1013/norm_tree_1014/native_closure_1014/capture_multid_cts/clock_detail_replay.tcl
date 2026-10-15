
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_TT_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_TT_*] { if {![string match *FAKE* $l]} { read_liberty $l } }

read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]

foreach c [all_clocks] {
  if {![llength [get_property $c sources]]} continue
  set_clock_latency -source 0 $c
  puts "OT_CK_RAW_SOURCE [get_full_name $c]"
}


set ot_ck_requested {core_clk}
set ot_ck_selected [get_clocks -quiet $ot_ck_requested]
if {![llength $ot_ck_selected]} {
  set ot_ck_ports [list $ot_ck_requested]
  if {[regexp {^(.*)\[0\]$} $ot_ck_requested -> ot_ck_base]} {
    lappend ot_ck_ports $ot_ck_base
  } else {
    lappend ot_ck_ports [format {%s[0]} $ot_ck_requested]
  }
  foreach c [all_clocks] {
    foreach s [get_property $c sources] {
      set ot_ck_source [get_full_name $s]
      if {$ot_ck_source in $ot_ck_ports && [llength [get_ports -quiet $ot_ck_source]]} {
        lappend ot_ck_selected $c
      }
    }
  }
}
set ot_ck_selected [lsort -unique $ot_ck_selected]
if {[llength $ot_ck_selected] != 1} {
  error "CK_INSERTION: clock '$ot_ck_requested' must resolve to one clock, found [llength $ot_ck_selected]"
}
puts "OT_CK_SELECTED [get_full_name [lindex $ot_ck_selected 0]]"
foreach c [all_clocks] {
  foreach s [get_property $c sources] {
    set sn [get_full_name $s]
    if {![llength [get_ports -quiet $sn]]} continue
    foreach refclk [all_clocks] {
      unset_input_delay -clock $refclk [get_ports $sn]
      unset_input_delay -clock $refclk -clock_fall [get_ports $sn]
    }
    unset_input_delay [get_ports $sn]
    puts "OT_CK_CLOCK_PORT $sn: data input delays dropped"
  }
}

set regs {}
foreach p [all_registers -clock_pins -clock $ot_ck_selected] { set n [get_full_name $p]; dict set regs [regsub {/[^/]+$} $n {}] $n }
set bnd {}
set din [all_inputs -no_clocks]
if {[llength $din]} { foreach pe [find_timing_paths -path_delay max -from $din -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] { set i [regsub {/[^/]+$} [get_full_name [get_property $pe endpoint]] {}]; if {[dict exists $regs $i]} { dict set bnd $i 1 } } }
foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] { set i [regsub {/[^/]+$} [get_full_name [get_property $pe startpoint]] {}]; if {[dict exists $regs $i]} { dict set bnd $i 1 } }

set ::ot_ck_act [dict create]
proc ot_ck_active {p} {
  set c [get_cells -quiet -of_objects $p]
  if {![llength $c]} { return "" }
  set k "[get_property $c ref_name]/[get_property $p lib_pin_name]"
  if {[dict exists $::ot_ck_act $k]} { return [dict get $::ot_ck_act $k] }
  sta::redirect_string_begin
  catch {report_edges -from $p}
  set r [sta::redirect_string_end]
  set on 0; set fr {}
  foreach l [split $r "\n"] {
    if {[regexp {^\S} $l]} { set on [regexp {(Clk|En) to Q} $l]; continue }
    if {$on && [regexp {^\s+([\^v])\s+->} $l -> e]} { if {[lsearch -exact $fr $e] < 0} { lappend fr $e } }
  }
  set a [expr {[llength $fr] == 1 ? ([lindex $fr 0] eq "^" ? "r" : "f") : ""}]
  dict set ::ot_ck_act $k $a
  return $a
}
proc ot_ck_arr {p clk} {
  set half 0.0
  if {![catch {list [$clk waveform] [$clk period] [get_property $clk period]} w]} {
    lassign $w wf ps pu
    if {[llength $wf] >= 2 && $ps > 0} { set half [expr {([lindex $wf 1] - [lindex $wf 0]) * $pu / $ps}] } }
  set ar [get_property $p arrival_max_rise]; set af [get_property $p arrival_max_fall]
  set okr [string is double -strict $ar]; set okf [string is double -strict $af]
  if {!($okr && $okf)} { return [expr {$okr ? $ar : ($okf ? $af : "")}] }
  set t [ot_ck_active $p]
  set lo [expr {$ar <= $af ? "r" : "f"}]
  if {$t eq ""} { set t $lo }
  set v [expr {$t eq "r" ? $ar : $af}]
  return [expr {$t eq $lo ? $v : $v - $half}]
}


proc ot_ck_macro_owned {p selected} {
  set owners {}
  foreach c [get_property $p clocks] { lappend owners [get_full_name $c] }
  set owners [lsort -unique $owners]
  if {[llength $owners] != 1} {
    error "CK_INSERTION: macro clock pin '[get_full_name $p]' requires one timing clock, found $owners"
  }
  puts "OT_MC_SOURCE [get_full_name $p] [lindex $owners 0]"
  return [expr {[lindex $owners 0] eq [get_full_name $selected]}]
}

set ot_ck_clk [lindex $ot_ck_selected 0]
dict for {i cp} $regs {
  set a [ot_ck_arr [get_pins $cp] $ot_ck_clk]
  if {$a eq "" || $a eq "INF" || $a eq "-INF"} continue
  puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a $cp"
}
foreach inst [[ord::get_db_block] getInsts] {
  if {![[$inst getMaster] isBlock]} continue
  foreach it [$inst getITerms] {
    set n [$it getNet]
    if {$n eq "NULL" || $n eq ""} continue
    if {[[$it getMTerm] getSigType] ne "CLOCK" && [$n getSigType] ne "CLOCK"} continue
    set p [get_pins -quiet "[$inst getName]/[[$it getMTerm] getName]"]
    if {[llength $p] != 1} { error "CK_INSERTION: unresolved macro clock pin [$inst getName]/[[$it getMTerm] getName]" }
    if {![ot_ck_macro_owned $p $ot_ck_clk]} continue
    set a [ot_ck_arr $p $ot_ck_clk]
    set sl [get_property $p slew_max_rise]
    if {![string is double -strict $a] || ![string is double -strict $sl]} { error "CK_INSERTION: missing macro clock arrival/slew [get_full_name $p]" }
    puts "OT_MC [get_full_name $p] $a $sl [$n getName]"
  }
}

set block [ord::get_db_block]
foreach target {rr$_DFF_P_ ot_prs_01144_ff} {
  set inst [$block findInst $target]
  if {$inst eq "NULL"} continue
  set pin [$inst findITerm CLK]
  for {set hop 0} {$hop < 20} {incr hop} {
    set net [$pin getNet]
    puts "TRACE $target $hop [$net getName]"
    set driver ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set driver [$it getInst]; break } }
    if {$driver eq ""} break
    puts "DRIVER [$driver getName] [[$driver getMaster] getName] [$driver getLocation]"
    set pin ""
    foreach it [$driver getITerms] { if {[$it isInputSignal]} { set pin $it; break } }
    if {$pin eq ""} break
  }
}
exit
