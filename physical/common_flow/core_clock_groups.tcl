# Explicit grouped-core network only. No source-time activation and no CTS of the frozen group.
namespace eval ::ot_ccg { variable groups {}; variable protected {}; variable placements {}; variable protected_inst {} }
proc ::ot_ccg::bounds {inst} { set b [$inst getBBox]; return [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] }
proc ::ot_ccg::supply {blk inst} {
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getSigType] ni {POWER GROUND}} continue
    set net [$blk findNet [$mt getName]]
    if {$net eq "NULL"} { error "OT_CCG missing supply [$mt getName]" }
    $it connect $net
  }
}
proc ::ot_ccg::legal {blk master x y orient} {
  set w [$master getWidth]; set h [$master getHeight]; set legal 0
  foreach r [$blk getRows] {
    lassign [$r getOrigin] rx ry
    if {$ry != $y || [$r getOrient] ne $orient} continue
    set pitch [$r getSpacing]
    if {$x >= $rx && ($x-$rx)%$pitch == 0 && $x+$w <= $rx+$pitch*[$r getSiteCount] && $h <= [[$r getSite] getHeight]} { set legal 1; break }
  }
  if {!$legal} { error "OT_CCG clock node outside legal row/site/orientation: $x $y $orient" }
  foreach i [$blk getInsts] {
    if {[$i getPlacementStatus] ni {PLACED FIRM LOCKED COVER}} continue
    lassign [bounds $i] a b c d
    if {$x < $c && $x+$w > $a && $y < $d && $y+$h > $b} { error "OT_CCG node overlaps [$i getName]" }
  }
}
proc ::ot_ccg::audit {blk} {
  variable protected; variable placements; variable protected_inst
  dict for {name state} $placements {
    set i [$blk findInst $name]
    if {$i eq "NULL" || [list [bounds $i] [$i getOrient] [[$i getMaster] getName]] ne $state} { error "OT_CCG moved/resized existing cell $name" }
  }
  dict for {name unused} $protected_inst {
    set i [$blk findInst $name]
    if {![$i isDoNotTouch] || [$i getPlacementStatus] ne "FIRM"} { error "OT_CCG planned node protection changed $name" }
  }
  dict for {net expected} $protected {
    set actual {}
    foreach it [$net getITerms] { if {[$it isInputSignal]} { lappend actual $it } }
    if {[lsort $actual] ne [lsort $expected] || ![$net isDoNotTouch]} { error "OT_CCG protected clock graph changed at [$net getName]" }
  }
  puts "OT_CCG AUDIT PASS protected_nets=[dict size $protected] existing_placements=[dict size $placements]"
}
# nodes = {name parent cell LLx_um LLy_um orient}; endpoints = {inst pin parent whole_core_tap}.
proc ::ot_ccg::setup {blk port nodes endpoints} {
  variable groups; variable protected; variable placements; variable protected_inst
  if {[dict exists $groups $port] || ![llength $nodes] || ![llength $endpoints]} { error "OT_CCG duplicate/empty group $port" }
  set bt [$blk findBTerm $port]
  if {$bt eq "NULL"} { error "OT_CCG missing group BTerm $port" }
  set root [$bt getNet]
  if {$root eq "NULL"} { error "OT_CCG unconnected group input $port" }
  set wanted {}; set resolved {}; set declared {}; set actual_clocks {}; set whole {}
  foreach e $endpoints {
    lassign $e name pin parent whole_core_tap
    set inst [$blk findInst $name]
    if {$inst eq "NULL" || ![[$inst getMaster] isBlock]} { error "OT_CCG group endpoint must be actual hard core $name" }
    set it [$inst findITerm $pin]
    if {$it eq "NULL" || ![$it isInputSignal] || [$it getNet] ne $root} { error "OT_CCG wrong/missing actual clock endpoint $name/$pin" }
    # The source plan names clock pins exactly; Liberty must confirm their role.
    set sp [get_pins -quiet [list $name/$pin]]
    set clock_pin 0; set clock_names {}
    if {[llength $sp] == 1} {
      set lc [get_lib_cells -quiet -of_objects [get_cells -quiet -of_objects $sp]]
      foreach lp [get_lib_pins -quiet -of_objects $lc] {
        if {[get_property $lp is_clock]} {
          set lp_name [get_property $lp name]; lappend clock_names $lp_name
          if {$lp_name eq $pin} { set clock_pin 1 }
        }
      }
    }
    if {!$clock_pin} { error "OT_CCG endpoint is not an actual Liberty clock $name/$pin" }
    dict lappend declared $name $pin
    dict set actual_clocks $name [lsort $clock_names]
    if {$whole_core_tap} { dict set whole $name 1 }
    lappend wanted $it; lappend resolved [list $it $parent]
  }
  dict for {name unused} $whole {
    if {[lsort [dict get $declared $name]] ne [dict get $actual_clocks $name]} { error "OT_CCG original whole-core tap clock coverage differs from actual Liberty $name" }
  }
  set actual {}
  foreach it [$root getITerms] { if {[$it isInputSignal]} { lappend actual $it } }
  if {[lsort $actual] ne [lsort $wanted]} { error "OT_CCG group physical membership differs from manifest $port" }
  if {![dict size $placements]} {
    foreach i [$blk getInsts] {
      if {[$i getPlacementStatus] in {PLACED FIRM LOCKED COVER}} { dict set placements [$i getName] [list [bounds $i] [$i getOrient] [[$i getMaster] getName]] }
    }
  }
  set nets [dict create @root $root];set created {};set dbu [$blk getDbUnitsPerMicron]
  foreach node $nodes {
    lassign $node name parent cell xu yu orient
    if {![dict exists $nets $parent] || [$blk findInst $name] ne "NULL" || [$blk findNet ${name}_Y] ne "NULL"} { error "OT_CCG invalid physical node/parent $name" }
    set master [[ord::get_db] findMaster $cell]
    if {$master eq "NULL"} { error "OT_CCG missing master $cell" }
    set x [expr {round($xu*$dbu)}];set y [expr {round($yu*$dbu)}]
    legal $blk $master $x $y $orient
    set inst [odb::dbInst_create $blk $master $name];$inst setOrient $orient;$inst setLocation $x $y;$inst setPlacementStatus FIRM
    if {[lrange [bounds $inst] 0 1] ne [list $x $y]} { error "OT_CCG node LL mismatch $name" }
    dict set placements $name [list [bounds $inst] [$inst getOrient] [[$inst getMaster] getName]]
    set ip {};set op {}
    foreach it [$inst getITerms] {
      if {[$it isInputSignal]} { lappend ip $it }
      if {[$it isOutputSignal]} { lappend op $it }
    }
    if {[llength $ip] != 1 || [llength $op] != 1} { error "OT_CCG node is not a single buffer $name" }
    set net [odb::dbNet_create $blk ${name}_Y];$net setSigType CLOCK
    set pn [dict get $nets $parent];[lindex $ip 0] connect $pn;[lindex $op 0] connect $net
    supply $blk $inst
    dict lappend protected $pn [lindex $ip 0]
    dict set protected $net {}
    dict set nets $name $net;lappend created $inst
  }
  foreach e $resolved {
    lassign $e it parent
    if {![dict exists $nets $parent] || $parent eq "@root"} { error "OT_CCG unbuffered/missing endpoint parent $parent" }
    set net [dict get $nets $parent];$it disconnect;$it connect $net;dict lappend protected $net $it
  }
  # All node/endpoint connections precede every dont_touch flag (ODB0373).
  foreach inst $created { $inst setDoNotTouch true; dict set protected_inst [$inst getName] 1 }
  dict for {node net} $nets { $net setDoNotTouch true }
  dict set groups $port $root
  audit $blk
  if {![llength [info commands ::ot_ccg::cts_orig]]} {
    rename ::clock_tree_synthesis ::ot_ccg::cts_orig
    proc ::clock_tree_synthesis {args} { return [::ot_ccg::cts {*}$args] }
  }
}
proc ::ot_ccg::bind_new_pg {blk} {
  variable placements
  foreach inst [$blk getInsts] {
    if {[dict exists $placements [$inst getName]]} continue
    if {![regexp {^(BUF|INV|HB|CKBUF|CKINV)} [[$inst getMaster] getName]]} { error "OT_CCG unexpected new non-clock cell [$inst getName]" }
    supply $blk $inst
  }
}
proc ::ot_ccg::cts {args} {
  variable groups
  set blk [ord::get_db_block];audit $blk
  set keep {}; set repair_requested 0
  for {set k 0} {$k < [llength $args]} {incr k} {
    set a [lindex $args $k]
    if {$a eq "-repair_clock_nets"} { set repair_requested 1; continue }
    if {$a eq "-clk_nets"} { incr k;continue }
    lappend keep $a
  }
  set ordinary {}
  foreach clk [all_clocks] {
    foreach source [get_property $clk sources] {
      set name [get_full_name $source]
      if {[dict exists $groups $name]} continue
      set bt [$blk findBTerm $name]
      if {$bt ne "NULL"} { lappend ordinary [[$bt getNet] getName] }
    }
  }
  set ordinary [lsort -unique $ordinary]
  set result ""
  if {[llength $ordinary]} { set result [cts_orig {*}$keep -clk_nets [join $ordinary " "]] }
  bind_new_pg $blk
  if {$repair_requested && [llength $ordinary]} {
    estimate_parasitics -placement
    est::check_parasitics
    set max_wire [rsz::check_max_wire_length 0 true]
    foreach name $ordinary {
      set net [$blk findNet $name]
      if {$net eq "NULL"} { error "OT_CCG ordinary CTS root disappeared $name" }
      rsz::repair_net_cmd [sta::db_net_to_sta $net] $max_wire 0 0
    }
    bind_new_pg $blk
  }
  audit $blk
  puts "OT_CCG CTS PASS groups=[dict size $groups] ordinary_roots=[llength $ordinary]"
  return $result
}
