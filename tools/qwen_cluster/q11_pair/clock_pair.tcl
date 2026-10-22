# q11 same-edge SRAM/control/capture and stage-reset clock construction.
# Source after clock_spine.tcl and the kit's insertion/arrival helper.
# Original clock sources and all data/reset connections and sequential edges are unchanged.
if {[info exists ::q11_pair_loaded]} { return }
set ::q11_pair_loaded 1
namespace eval q11_pair { variable parent; variable marked; variable clocks; variable insts }
proc q11_pair::find {n} {
  variable parent
  if {![dict exists $parent $n]} {dict set parent $n $n}
  set p [dict get $parent $n]
  if {$p ne $n} {set p [find $p]; dict set parent $n $p}
  return $p
}
proc q11_pair::join {a b} {
  variable parent; variable marked
  dict set marked $a 1; dict set marked $b 1
  set x [find $a]; set y [find $b]
  if {$x ne $y} {dict set parent $y $x}
}
proc q11_pair::logical_name {n} {
  return [string map [list [format %c 92] ""] $n]
}
proc q11_pair::data_net {net} {
  expr {$net ne "NULL" && $net ne "" && [$net getSigType] ni {POWER GROUND CLOCK}}
}
# Walk combinational data only. A first clocked primitive is a real boundary;
# do not walk through its state or infer clock ownership from instance order.
proc q11_pair::walk {seed first direction} {
  variable clocks
  set todo [list $first]; set seen [dict create]; set reached [dict create]
  while {[llength $todo]} {
    set net [lindex $todo end]; set todo [lrange $todo 0 end-1]
    if {![data_net $net] || [dict exists $seen $net]} continue
    dict set seen $net 1
    foreach it [$net getITerms] {
      set io [$it getIoType]
      if {$direction eq "back" && $io ne "OUTPUT"} continue
      if {$direction eq "forward" && $io ne "INPUT"} continue
      set inst [$it getInst]; set name [$inst getName]
      if {[dict exists $clocks $name]} {
        if {$name ne $seed} {join $seed $name; dict set reached $name 1}
        continue
      }
      if {[[$inst getMaster] isBlock]} {error "Q11 unowned data macro $name"}
      foreach next [$inst getITerms] {
        if {$direction eq "back" && [$next getIoType] eq "INPUT"} {lappend todo [$next getNet]}
        if {$direction eq "forward" && [$next getIoType] eq "OUTPUT"} {lappend todo [$next getNet]}
      }
    }
  }
  return [dict keys $reached]
}
proc q11_pair::new_leaf {rows group} {
  set sx 0.0; set sy 0.0; set members {}
  foreach row $rows {lassign $row it x y; set sx [expr {$sx+$x}]; set sy [expr {$sy+$y}]; lappend members $it}
  set n [llength $members]; set id "Q11L[incr ::q11_pair_leaf_id]"
  dict set ::ot_sp_members $id $members
  dict set ::ot_sp_cnt $id $n
  dict set ::ot_sp_pos $id [ot_sp_free [expr {int($sx/$n)}] [expr {int($sy/$n)}]]
  dict set ::q11_pair_leaf_group $id $group
  return $id
}
# The stock builder has discovered the exact native clock endpoints and legal
# sites. Regroup its endpoints before emitting any clock cell or clock net.
rename ot_sp_sym_build q11_pair_stock_sym_build
proc ot_sp_sym_build {ids lins rx ry} {
  set ::q11_pair::parent [dict create]; set ::q11_pair::marked [dict create]
  set ::q11_pair::clocks [dict create]; set ::q11_pair::insts [dict create]
  set all {}; set macros {}
  foreach id $ids {
    if {[dict exists $lins $id] && [dict get $lins $id] != 0} {error "Q11 expects raw SRAM clock terminals, not inherited child insertion"}
    foreach it [dict get $::ot_sp_members $id] {
      set inst [$it getInst]; set n [$inst getName]; set pin [[$it getMTerm] getName]
      if {![regexp -nocase {^(clk|ck|c|rclk|wclk)$} $pin]} {error "Q11 nonclock endpoint $n/$pin on unbuilt source clock"}
      dict lappend ::q11_pair::clocks $n $it; dict set ::q11_pair::insts $n $inst
      lappend all $it
      if {[[$inst getMaster] isBlock]} {
        if {![string match ot_sram_1r1w2c_* [[$inst getMaster] getName]]} {error "Q11 unexpected clocked hard macro $n"}
        dict set macros $n $inst
      }
    }
  }
  if {[dict size $macros] != 12} {error "Q11 expected 12 authentic q10 SRAMs, found [dict size $macros]"}
  set launches [dict create]; set captures [dict create]
  dict for {n inst} $macros {
    q11_pair::join $n $n
    foreach it [$inst getITerms] {
      if {[lsearch -exact [dict get $::q11_pair::clocks $n] $it] >= 0} continue
      if {[$it getIoType] eq "INPUT"} {
        foreach r [q11_pair::walk $n [$it getNet] back] {dict set launches $r 1}
      } elseif {[$it getIoType] eq "OUTPUT"} {
        foreach r [q11_pair::walk $n [$it getNet] forward] {dict set captures $r 1}
      }
    }
  }
  set reset_count 0; set reset_targets 0
  dict for {n inst} $::q11_pair::insts {
    if {![regexp {g_rsg\[[0-9]+\].*u_rs[/\.]s\[1\]} [q11_pair::logical_name $n]]} continue
    incr reset_count; q11_pair::join $n $n
    foreach it [$inst getITerms] {
      if {[$it getIoType] eq "OUTPUT"} {incr reset_targets [llength [q11_pair::walk $n [$it getNet] forward]]}
    }
  }
  set cc 0; set od 0
  foreach n [dict keys $launches] {if {[regexp {(^|[/\.])cc\[[0-9]+\]} [q11_pair::logical_name $n]]} {incr cc}}
  foreach n [dict keys $captures] {if {[regexp {(^|[/\.])(out_data|od_q)\[[0-9]+\]} [q11_pair::logical_name $n]]} {incr od}}
  puts "Q11_ROLE_TRACE clock_instances=[dict size $::q11_pair::clocks] launches=[dict size $launches] captures=[dict size $captures]"
  if {$cc != 9 || $od != 128 || !$reset_count || !$reset_targets} {
    error "Q11 incomplete exact source coverage: cc=$cc out_data=$od reset_sources=$reset_count reset_targets=$reset_targets"
  }
  set bins [dict create]; set bin [expr {60*$::ot_sp_dbu}]
  foreach it $all {
    set inst [$it getInst]; set n [$inst getName]
    set group REST
    if {[dict exists $::q11_pair::marked $n]} {set group [q11_pair::find $n]}
    lassign [$it getAvgXY] ok x y
    if {!$ok} {lassign [$inst getLocation] x y}
    if {[[$inst getMaster] isBlock]} {set key [list $group M $n [[$it getMTerm] getName]]} else {set key [list $group S [expr {int($x/$bin)}] [expr {int($y/$bin)}]]}
    dict lappend bins $key [list $it $x $y]
  }
  # Keep every real endpoint exactly once; raw SRAM rclk/wclk get separate
  # bounded-load leaves within the same coupled component as their controls.
  set ::ot_sp_members [dict create]; set ::ot_sp_cnt [dict create]; set ::ot_sp_pos [dict create]
  set ::ot_sp_kids [dict create]; set ::q11_pair_leaf_group [dict create]; set ::q11_pair_leaf_id 0
  set groups [dict create]; set lmax [ot_sp_env OT_SPINE_LEAF_N 8]
  dict for {key rows} $bins {
    set group [lindex $key 0]; set rows [lsort -real -index 1 $rows]
    for {set i 0} {$i<[llength $rows]} {incr i $lmax} {
      set leaf [q11_pair::new_leaf [lrange $rows $i [expr {$i+$lmax-1}]] $group]
      dict lappend groups $group $leaf
    }
  }
  set roots {}
  dict for {group leaves} $groups {
    # No collapse across these roots: a functional memory/reset neighborhood
    # owns a common clock branch even when another cell is geometrically nearer.
    lappend roots [ot_sp_split_bb $leaves]
    puts "Q11_PAIR_GROUP $group leaves=[llength $leaves]"
  }
  set sub [ot_sp_split_bb $roots]; set top "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $top [list $rx $ry]; dict set ::ot_sp_cnt $top [llength $all]
  dict set ::ot_sp_kids $top [list $sub]
  uplevel 1 [list set nl [dict size $::ot_sp_members]]
  puts "Q11_PAIR_COVERAGE endpoints=[llength $all] SRAMs=[dict size $macros] counter_bits=$cc output_bits=$od reset_sources=$reset_count reset_targets=$reset_targets components=[dict size $groups]"
  return $top
}
# Diagnostic only: report real sink arrivals within each paired component.
# Neither this measurement nor the design target changes a signoff criterion.
rename ot_sp_leaf_arrivals q11_pair_stock_leaf_arrivals
proc ot_sp_leaf_arrivals {} {
  set a [q11_pair_stock_leaf_arrivals]
  if {![info exists ::q11_pair_leaf_group]} {return $a}
  set ranges [dict create]
  dict for {leaf net} $::ot_sp_leafnet {
    set g [dict get $::q11_pair_leaf_group $leaf]
    foreach pin [get_pins -quiet -of_objects [get_nets -quiet [$net getName]] -filter "direction==input"] {
      set v [get_property $pin arrival_max_rise]
      if {$v eq "" || $v in {INF -INF}} continue
      dict lappend ranges $g $v
    }
  }
  dict for {g values} $ranges {
    set lo [tcl::mathfunc::min {*}$values]; set hi [tcl::mathfunc::max {*}$values]
    puts [format "Q11_PAIR_ARRIVAL group=%s sinks=%d min=%.3f max=%.3f spread=%.3f ps (diagnostic)" $g [llength $values] $lo $hi [expr {$hi-$lo}]]
  }
  return $a
}
puts "Q11 clock pairs installed: authentic same-edge SRAM/control/capture and local reset groups"
