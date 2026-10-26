
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_TT_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_TT_*] { if {![string match *FAKE* $l]} { read_liberty $l } }

read_db /base/6_final.odb
read_sdc /base/6_final.sdc
read_spef /base/6_final.spef
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
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc grp_in {pat} { set s {}; set ps [get_ports -quiet $pat]; if {![llength $ps]} {return $s}; foreach pe [find_timing_paths -path_delay max -from $ps -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1 -unique_paths_to_endpoint] { dict set s [regsub {/[^/]+$} [get_full_name [get_property $pe endpoint]] {}] 1 }; return $s }
proc grp_out {pat} { set s {}; set ps [get_ports -quiet $pat]; if {![llength $ps]} {return $s}; foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to $ps -group_path_count 200000 -endpoint_path_count 2000 -unique_paths_to_endpoint] { dict set s [regsub {/[^/]+$} [get_full_name [get_property $pe startpoint]] {}] 1 }; return $s }
set G [dict create]
for {set k 0} {$k < 4} {incr k} {
 set ports [list [format {rgx_v[%d]} $k]]
 for {set bit [expr {$k*40}]} {$bit < ($k+1)*40} {incr bit} {lappend ports [format {rgx_addr[%d]} $bit]}
 for {set bit [expr {$k*512}]} {$bit < ($k+1)*512} {incr bit} {lappend ports [format {rgx_data[%d]} $bit]}
 dict set G in:rgx$k [grp_in $ports]
}
dict set G in:tkw [grp_in {tkw_*}]
dict set G in:meta [grp_in {sid* rgx_vm ingress_slot* slot_valid* slot_owner* rst_n}]
for {set k 0} {$k < 8} {incr k} {
 set ports {}
 for {set bit [expr {$k*281}]} {$bit < ($k+1)*281} {incr bit} {lappend ports [format {kq[%d]} $bit]}
 dict set G out:kq$k [grp_out $ports]
}
dict set G out:status [grp_out {launch_done* fault}]
set blk [ord::get_db_block]
set IX [dict create]
foreach inst [$blk getInsts] { dict set IX [string map {\\ {}} [$inst getName]] $inst }
foreach p [all_registers -clock_pins -clock $ot_ck_selected] {
  set n [get_full_name $p]; set i [regsub {/[^/]+$} $n {}]
  set a [ot_ck_arr $p $ot_ck_clk]
  set k [string map {\\ {}} $i]
  if {![dict exists $IX $k]} { set xy "? ?" } else { set bb [[dict get $IX $k] getBBox]; set xy "[expr {(([$bb xMin]+[$bb xMax])/2)/double($dbu)}] [expr {(([$bb yMin]+[$bb yMax])/2)/double($dbu)}]" }
  set gs {}
  dict for {g s} $G { if {[dict exists $s $i]} { lappend gs $g } }
  puts "OT_REG $i $xy $a [join $gs ,]"
}
foreach bt [$blk getBTerms] { set bp [lindex [$bt getBPins] 0]; if {$bp eq ""} continue; set bb [$bp getBBox]; puts "OT_PIN [$bt getName] [expr {(([$bb xMin]+[$bb xMax])/2)/double($dbu)}] [expr {(([$bb yMin]+[$bb yMax])/2)/double($dbu)}]" }
foreach inst [$blk getInsts] { if {[string match *clkbuf* [string tolower [[$inst getMaster] getName]]] || [string match clkbuf* [$inst getName]] || [string match *CKINV* [[$inst getMaster] getName]]} { set bb [$inst getBBox]; puts "OT_CKB [$inst getName] [[$inst getMaster] getName] [expr {(([$bb xMin]+[$bb xMax])/2)/double($dbu)}] [expr {(([$bb yMin]+[$bb yMax])/2)/double($dbu)}]" } }
exit
