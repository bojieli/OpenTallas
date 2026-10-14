define_corners WC BC

foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] { read_liberty -corner WC $l }
read_liberty -corner WC /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_tt.lib
read_liberty -corner WC /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] {read_liberty -corner BC $l}
read_liberty -corner BC /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ff.lib
read_liberty -corner BC /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_ff.lib
read_db /probe/before_repair.odb
read_sdc /probe/before_repair.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]

set ot_ck_requested {clk}
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

set ot_ck_clk [lindex $ot_ck_selected 0]
dict for {i cp} $regs {
  set a [ot_ck_arr [get_pins $cp] $ot_ck_clk]
  if {$a eq "" || $a eq "INF" || $a eq "-INF"} continue
  puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a"
}
foreach inst [[ord::get_db_block] getInsts] {
  if {![[$inst getMaster] isBlock]} continue
  foreach it [$inst getITerms] {
    set n [$it getNet]
    if {$n eq "NULL" || $n eq ""} continue
    if {[[$it getMTerm] getSigType] ne "CLOCK" && [$n getSigType] ne "CLOCK"} continue
    set p [get_pins -quiet "[$inst getName]/[[$it getMTerm] getName]"]
    if {![llength $p]} continue
    set a [ot_ck_arr $p $ot_ck_clk]
    set sl [get_property $p slew_max_rise]
    if {$a eq "" || $a eq "INF" || $a eq "-INF" || ![string is double -strict $sl]} continue
    puts "OT_MC [get_full_name $p] $a $sl [$n getName]"
  }
}

proc ot_domain {net} {
 set seen [dict create]
 for {set d 0} {$d<1000} {incr d} {
  if {$net eq "NULL" || $net eq ""} {return unknown}
  set nn [$net getName]
  if {[dict exists $seen $nn]} {return cycle}
  dict set seen $nn 1
  foreach b [$net getBTerms] {if {[$b getIoType] eq "INPUT"} {return "primary:[$b getName]"}}
  set up ""
  foreach it [$net getITerms] {
   if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
   set inst [$it getInst];set master [[$inst getMaster] getName]
   if {[string match *ICG* $master]} {return "gated:[$inst getName]"}
   set in [$inst findITerm A]
   if {$in ne "NULL" && $in ne ""} {set up [$in getNet];break}
  }
  if {$up eq ""} {return "unknown:$nn"}
  set net $up
 }
 return depth
}
foreach c [all_clocks] {
 set srcs {};foreach p [get_property $c sources] {lappend srcs [get_full_name $p]}
 puts "OT_CLOCK_MAP [get_full_name $c] $srcs [$c waveform] [get_property $c period]"
}
set block [ord::get_db_block]
puts "OT_CONVERT_PROCS [info procs *sta_to_db_pin*] [info procs sta::*db*pin*]"
set shown 0
foreach ii [$block getInsts] {if {[string match *cmd_data* [$ii getName]] && $shown<3} {puts "OT_DB_NAME [$ii getName]";incr shown}}
set shown 0
foreach pp [all_registers -clock_pins] {if {[string match *cmd_data* [get_full_name $pp]] && $shown<3} {puts "OT_STA_NAME [get_full_name $pp]";incr shown}}
set dbnames [dict create]
foreach ii [$block getInsts] {dict set dbnames [string map [list {\[} {[} {\]} {]}] [$ii getName]] $ii}
puts "OT_REG_COUNT [dict size $regs] ALL [llength [all_registers -clock_pins]]"
set seq [dict create]
foreach ii [$block getInsts] {set m [[$ii getMaster] getName];if {[string match *DFF* $m] || [string match *SDFF* $m]} {dict incr seq $m}}
puts "OT_DB_FF $seq"
dict for {i cp} $regs {
 set rawi [string map [list {[} {\[} {]} {\]}] $i]
 set inst [$block findInst $rawi]
 if {$inst eq "NULL" || $inst eq ""} {set inst [$block findInst $i]}
 if {$inst eq "NULL" || $inst eq ""} {
  set ci [string map [list {\[} {[} {\]} {]}] $i]
  if {[dict exists $dbnames $ci]} {set inst [dict get $dbnames $ci]} else {puts "OT_MISSING $i";continue}
 }
 set pn [regsub {^.*/} $cp {}];set it [$inst findITerm $pn]
 if {$it eq "NULL" || $it eq ""} continue
 set a [ot_ck_arr [get_pins $cp] $ot_ck_clk]
 if {$a eq "" || $a eq "INF" || $a eq "-INF"} continue
 puts "OT_DOMAIN [ot_domain [$it getNet]] [expr {[dict exists $bnd $i]?1:0}] $a $cp"
}
foreach inst [$block getInsts] {
 if {![[$inst getMaster] isBlock]} continue
 foreach it [$inst getITerms] {
  set net [$it getNet]
  if {$net eq "NULL" || $net eq "" || [$net getSigType] ne "CLOCK"} continue
  set cp "[$inst getName]/[[$it getMTerm] getName]";set p [get_pins -quiet $cp]
  if {![llength $p]} continue
  puts "OT_DOMAIN_MACRO [ot_domain $net] [ot_ck_arr $p $ot_ck_clk] $cp"
 }
}

foreach n {CLK ENA GCLK} {
 set p [get_pins -quiet "u_cg.u_icg/$n"]
 if {[llength $p]} {puts "OT_ICG_PIN $n max_rise [get_property $p arrival_max_rise] min_rise [get_property $p arrival_min_rise] max_fall [get_property $p arrival_max_fall] min_fall [get_property $p arrival_min_fall]"}
}
report_checks -to [get_pins {u_cg.u_icg/ENA}] -path_delay max -group_path_count 1 -format full_clock_expanded
report_checks -to [get_pins {u_cg.u_icg/ENA}] -path_delay min -group_path_count 1 -format full_clock_expanded
puts "OT_PW_ROW2_PATH"
report_checks -to [get_pins {u_shadow.g_psram.pw_row2[0]$_DFF_P_/D}] -path_delay max -group_path_count 1 -format full_clock_expanded
puts "OT_WORST_PATH"
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
exit
