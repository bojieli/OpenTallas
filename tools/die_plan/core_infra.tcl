# Shared core-netlist infrastructure. Never place parent cells or carve LEF holes.
# Every location/sink identity is emitted from the plan before the build.
proc ot_ci_begin {} {
  set ::ot_ci_b [ord::get_db_block]
  set ::ot_ci_u [[ord::get_db_tech] getDbUnitsPerMicron]
  set ::ot_ci_cells {}; set ::ot_ci_ports {}; set ::ot_ci_arcs {}
  set ::ot_ci_fixed {}; set ::ot_ci_tree_expected {}; set ::ot_ci_tree_seen {}
  set ::ot_ci_tree_out [dict create]; set ::ot_ci_tree_open {}
  set ::ot_ci_occ [dict create]; set ::ot_ci_occ_order [dict create]
  set ::ot_ci_occ_next 0
  set ::ot_ci_occ_pitch [expr {10 * $::ot_ci_u}]
  foreach i [$::ot_ci_b getInsts] {
    dict set ::ot_ci_occ_order $i $::ot_ci_occ_next
    incr ::ot_ci_occ_next
    if {[[$i getMaster] isBlock] || [$i getPlacementStatus] in {FIRM LOCKED COVER}} {
      ot_ci_occ_add $i
    }
  }
}
# Bucket only the bodies the original fixed-overlap guard inspects. Existing
# entries may remain after this owner moves a body: queries still read its live
# bbox, and adding the new buckets prevents misses without an expensive rebuild.
proc ot_ci_occ_add {i} {
  if {![dict exists $::ot_ci_occ_order $i]} {
    dict set ::ot_ci_occ_order $i $::ot_ci_occ_next
    incr ::ot_ci_occ_next
  }
  set r [$i getBBox]; set p $::ot_ci_occ_pitch
  for {set x [expr {int(floor([$r xMin]/double($p)))}]} {$x <= int(floor([$r xMax]/double($p)))} {incr x} {
    for {set y [expr {int(floor([$r yMin]/double($p)))}]} {$y <= int(floor([$r yMax]/double($p)))} {incr y} {
      dict set ::ot_ci_occ $x,$y $i 1
    }
  }
}
proc ot_ci_occ_candidates {x0 y0 x1 y1} {
  set found [dict create]; set p $::ot_ci_occ_pitch
  for {set x [expr {int(floor($x0/double($p)))}]} {$x <= int(floor($x1/double($p)))} {incr x} {
    for {set y [expr {int(floor($y0/double($p)))}]} {$y <= int(floor($y1/double($p)))} {incr y} {
      if {![dict exists $::ot_ci_occ $x,$y]} continue
      foreach i [dict keys [dict get $::ot_ci_occ $x,$y]] {
        dict set found $i [dict get $::ot_ci_occ_order $i]
      }
    }
  }
  set ordered {}
  dict for {i ordinal} $found {lappend ordered [list $ordinal $i]}
  return [lmap pair [lsort -integer -index 0 $ordered] {lindex $pair 1}]
}
proc ot_ci_net {name} {
  set n [$::ot_ci_b findNet $name]
  if {$n eq "NULL"} {set n [odb::dbNet_create $::ot_ci_b $name]}
  return $n
}
proc ot_ci_clock_entry {name x y} {
  set bt [$::ot_ci_b findBTerm $name]
  if {$bt eq "NULL" || [$bt getIoType] ne "INPUT"} {error "OT_CORE_INFRA_CLOCK_ENTRY_PORT $name"}
  place_pin -pin_name $name -layer M5 -location [list $x $y] -pin_size {0.048 0.48}
}
proc ot_ci_port {name direction x y {shape {0.032 0.192}}} {
  set bt [$::ot_ci_b findBTerm $name]
  if {$bt eq "NULL"} {
    set bt [odb::dbBTerm_create [ot_ci_net $name] $name]
    $bt setIoType $direction
  } elseif {[$bt getIoType] ne $direction} {error "OT_CORE_INFRA_PORT_DIRECTION $name"}
  place_pin -pin_name $name -layer M5 -location [list $x $y] -pin_size $shape
  lappend ::ot_ci_ports $name
}
# Coordinates are core-local centres; only deterministic technology row/site
# quantisation is allowed. No search, sliding, or post-measurement relocation.
proc ot_ci_place {i x y rect} {
  set m [$i getMaster]; set w [$m getWidth]; set h [$m getHeight]
  set row ""; set best 1e99
  foreach r [$::ot_ci_b getRows] {
    lassign [$r getOrigin] rx ry
    set d [expr {abs($ry + $h / 2.0 - $y * $::ot_ci_u)}]
    if {$d < $best} {set best $d; set row $r}
  }
  if {$row eq ""} {error "OT_CORE_INFRA_NO_ROWS [$i getName]"}
  lassign [$row getOrigin] rx ry
  set sw [[$row getSite] getWidth]
  set xx [expr {$rx + int(round(($x * $::ot_ci_u - $w / 2.0 - $rx) / $sw)) * $sw}]
  set yy $ry
  lassign $rect x0 y0 x1 y1
  if {$xx < $x0*$::ot_ci_u || $yy < $y0*$::ot_ci_u || $xx+$w > $x1*$::ot_ci_u || $yy+$h > $y1*$::ot_ci_u} {
    error "OT_CORE_INFRA_ISLAND_FIT [$i getName] at $xx $yy size $w $h outside $rect"
  }
  if {[$i isDoNotTouch]} {
    lassign [$i getLocation] ox oy
    if {$ox != $xx || $oy != $yy || [$i getOrient] ne [$row getOrient]} {
      error "OT_CORE_INFRA_STALE_FIXED_LOCATION [$i getName]"
    }
  } else {
    $i setOrient [$row getOrient]; $i setLocation $xx $yy
    $i setPlacementStatus FIRM
  }
  ot_ci_occ_add $i
  foreach j [ot_ci_occ_candidates $xx $yy [expr {$xx+$w}] [expr {$yy+$h}]] {
    if {$i eq $j} continue
    if {![[ $j getMaster] isBlock] && [$j getPlacementStatus] ni {FIRM LOCKED COVER}} continue
    set r [$j getBBox]
    if {$xx < [$r xMax] && $xx+$w > [$r xMin] && $yy < [$r yMax] && $yy+$h > [$r yMin]} {
      error "OT_CORE_INFRA_PLANNED_OVERLAP [$i getName] [$j getName]"
    }
  }
}
proc ot_ci_cell {name master x y rect} {
  set m [[ord::get_db] findMaster $master]
  if {$m eq "NULL"} {error "OT_CORE_INFRA_MISSING_MASTER $master"}
  set i [$::ot_ci_b findInst $name]
  if {$i eq "NULL"} {set i [odb::dbInst_create $::ot_ci_b $m $name]} elseif {[$i getMaster] ne $m} {
    error "OT_CORE_INFRA_STALE_MASTER $name"
  }
  foreach pin {A Y} {if {[$i findITerm $pin] eq "NULL"} {error "OT_CORE_INFRA_BUFFER_PIN $name/$pin"}}
  ot_ci_place $i $x $y $rect
  lappend ::ot_ci_cells $i
}
proc ot_ci_origin_assert {name x y orient} {
  set i [$::ot_ci_b findInst $name];lassign [$i getLocation] xx yy
  if {$xx != round($x*$::ot_ci_u) || $yy != round($y*$::ot_ci_u) || [$i getOrient] ne $orient} {
    error "OT_CORE_INFRA_FROZEN_ORIGIN_MISMATCH $name"
  }
}
proc ot_ci_connect {term net} {
  set old [$term getNet]
  if {$old ne "NULL" && $old ne $net} {error "OT_CORE_INFRA_STALE_CONNECTION [$term getInst]/[$term getMTerm]"}
  if {$old eq "NULL"} {$term connect $net}
}
proc ot_ci_arc {cell source sink} {
  set i [$::ot_ci_b findInst $cell]
  set bi [$::ot_ci_b findBTerm $source]; set bo [$::ot_ci_b findBTerm $sink]
  set ni [$bi getNet]; set no [$bo getNet]
  ot_ci_connect [$i findITerm A] $ni; ot_ci_connect [$i findITerm Y] $no
  if {[string match *_ck_i $source]} {$ni setSigType CLOCK; $no setSigType CLOCK}
  dict lappend ::ot_ci_arcs $source [$i findITerm A]
  dict lappend ::ot_ci_arcs $sink [$i findITerm Y]
}
proc ot_ci_tree_begin {clock_port} {
  set bt [$::ot_ci_b findBTerm $clock_port]
  if {$bt eq "NULL" || [$bt getIoType] ne "INPUT"} {error "OT_CORE_INFRA_CLOCK_PORT $clock_port"}
  set n [$bt getNet]
  dict set ::ot_ci_tree_out port:$clock_port $n
  # Preserve this census before adding tree drivers. The planned leaf list must
  # contain every original clock sink; no silent dropped macro/gate clocks.
  foreach it [$n getITerms] {
    if {[$it isInputSignal] || [[$it getMTerm] getSigType] eq "CLOCK"} {
      lappend ::ot_ci_tree_expected $it
    }
  }
}
proc ot_ci_tree_node {cell parent} {
  set i [$::ot_ci_b findInst $cell]
  set n [ot_ci_net ${cell}_out]; $n setSigType CLOCK
  ot_ci_connect [$i findITerm A] [dict get $::ot_ci_tree_out $parent]
  ot_ci_connect [$i findITerm Y] $n
  dict set ::ot_ci_tree_out $cell $n
}
proc ot_ci_tree_sink {node path} {
  set cut [string last / $path]
  if {$cut < 1} {error "OT_CORE_INFRA_SINK_NAME $path"}
  set i [$::ot_ci_b findInst [string range $path 0 [expr {$cut-1}]]]
  if {$i eq "NULL"} {error "OT_CORE_INFRA_SINK_INSTANCE $path"}
  set it [$i findITerm [string range $path [expr {$cut+1}] end]]
  if {$it eq "NULL"} {error "OT_CORE_INFRA_SINK_PIN $path"}
  set target [dict get $::ot_ci_tree_out $node]
  if {[$it getNet] ne $target} {
    if {[lsearch -exact $::ot_ci_tree_expected $it] < 0} {error "OT_CORE_INFRA_UNPLANNED_CLOCK_SINK $path"}
    # Boundary flops retain dont_touch identity through placement. Standard CTS
    # must still attach their CLOCK terminal. Only this explicitly enumerated
    # source-clock sink may reconnect, and cell protection is restored even on
    # an OpenDB error. No data terminal or PG binding uses this path.
    set inst [$it getInst];set protected [$inst isDoNotTouch]
    if {$protected} {$inst setDoNotTouch 0}
    try {
      $it disconnect; $it connect $target
    } finally {
      if {$protected} {$inst setDoNotTouch 1}
    }
  }
  lappend ::ot_ci_tree_seen $it
}
# Preserve an already signed hard core's original early feed. This routine has
# no connect/disconnect or placement operation: it only verifies and records an
# actual hard-block Liberty clock pin in the complete original root census.
proc ot_ci_tree_preserve_hard {clock_port path master} {
  set cut [string last / $path]
  if {$cut < 1} {error "OT_CORE_INFRA_PRESERVED_CLOCK_PIN $path"}
  set i [$::ot_ci_b findInst [string range $path 0 [expr {$cut-1}]]]
  if {$i eq "NULL" || ![[$i getMaster] isBlock] || [[$i getMaster] getName] ne $master} {
    error "OT_CORE_INFRA_PRESERVED_CLOCK_MASTER $path $master"
  }
  set pin [string range $path [expr {$cut+1}] end]
  set it [$i findITerm $pin]
  if {$it eq "NULL" || ![$it isInputSignal]} {error "OT_CORE_INFRA_PRESERVED_CLOCK_INPUT $path"}
  set root [dict get $::ot_ci_tree_out port:$clock_port]
  if {[$it getNet] ne $root || [lsearch -exact $::ot_ci_tree_expected $it] < 0} {
    error "OT_CORE_INFRA_PRESERVED_CLOCK_ROOT $path"
  }
  if {[lsearch -exact $::ot_ci_tree_seen $it] >= 0} {error "OT_CORE_INFRA_PRESERVED_CLOCK_DUPLICATE $path"}
  set typed 0
  set ps [get_pins -quiet [list $path]]
  if {[llength $ps] == 1} {
    set cells [get_lib_cells -quiet -of_objects [get_cells -quiet -of_objects $ps]]
    foreach lp [get_lib_pins -quiet -of_objects $cells] {
      if {[get_property $lp name] eq $pin && [get_property $lp is_clock]} {set typed 1}
    }
  }
  if {!$typed} {error "OT_CORE_INFRA_PRESERVED_CLOCK_LIBERTY $path"}
  lappend ::ot_ci_tree_seen $it
  puts "OT_CORE_INFRA_PRESERVED_HARD_CLOCK $path master=$master original_root=$clock_port unchanged"
}
# ICG-aware tree (12.8b): an existing RTL clock gate is a planned stage. Its CLK pin moves from the core clock net
# (census-checked) to its plan parent; it is placed at the plan region root; its gated output net keeps every
# original gated sink (count asserted against the plan census) and is left open for the local CTS tree.
proc ot_ci_tree_gate {inst master parent clk_pin out_pin x y rect} {
  set i [$::ot_ci_b findInst $inst]
  if {$i eq "NULL"} {error "OT_CORE_INFRA_GATE_INSTANCE $inst"}
  if {[[$i getMaster] getName] ne $master} {error "OT_CORE_INFRA_GATE_MASTER $inst [[$i getMaster] getName] != $master"}
  set ck [$i findITerm $clk_pin]; set go [$i findITerm $out_pin]
  if {$ck eq "NULL" || $go eq "NULL"} {error "OT_CORE_INFRA_GATE_PIN $inst"}
  set target [dict get $::ot_ci_tree_out $parent]
  if {[$ck getNet] ne $target} {
    if {[lsearch -exact $::ot_ci_tree_expected $ck] < 0} {error "OT_CORE_INFRA_GATE_NOT_ON_CORE_CLOCK $inst"}
    set protected [$i isDoNotTouch]
    if {$protected} {$i setDoNotTouch 0}
    try {$ck disconnect; $ck connect $target} finally {if {$protected} {$i setDoNotTouch 1}}
  }
  lappend ::ot_ci_tree_seen $ck
  set n [$go getNet]
  if {$n eq "NULL"} {error "OT_CORE_INFRA_GATE_NO_DOMAIN $inst"}
  $n setSigType CLOCK
  ot_ci_place $i $x $y $rect
  lappend ::ot_ci_fixed $i
  dict set ::ot_ci_tree_out $inst $n
}
# CLOCK-GATE COPY (S81-CORE-LAT-R7): a new ICG of the original's master; every enable pin reads the SAME net as the
# original's pin (same registered enable), CLK from the plan parent, own GCLK net; the named members move from the
# original's gated domain (each must be on it now). Exact membership: the domain census equals the member count.
proc ot_ci_tree_gate_copy {inst master orig parent clk_pin out_pin x y rect pins members} {
  set o [$::ot_ci_b findInst $orig]
  if {$o eq "NULL" || ![dict exists $::ot_ci_tree_out $orig]} {error "OT_CORE_INFRA_GATE_COPY_ORIG $inst $orig"}
  if {[[$o getMaster] getName] ne $master} {error "OT_CORE_INFRA_GATE_COPY_MASTER $inst"}
  if {[$::ot_ci_b findInst $inst] ne "NULL"} {error "OT_CORE_INFRA_GATE_COPY_EXISTS $inst"}
  set m [[ord::get_db] findMaster $master]
  set i [odb::dbInst_create $::ot_ci_b $m $inst]
  foreach p $pins {
    set n [[$o findITerm $p] getNet]
    if {$n eq "NULL"} {error "OT_CORE_INFRA_GATE_COPY_ENABLE_UNCONNECTED $orig/$p"}
    [$i findITerm $p] connect $n
  }
  [$i findITerm $clk_pin] connect [dict get $::ot_ci_tree_out $parent]
  set og [dict get $::ot_ci_tree_out $orig]
  set n [ot_ci_net ${inst}_gclk]; $n setSigType CLOCK
  [$i findITerm $out_pin] connect $n
  foreach path $members {
    set cut [string last / $path]
    set s [$::ot_ci_b findInst [string range $path 0 [expr {$cut-1}]]]
    if {$cut < 1 || $s eq "NULL"} {error "OT_CORE_INFRA_GATE_COPY_MEMBER $path"}
    set it [$s findITerm [string range $path [expr {$cut+1}] end]]
    if {$it eq "NULL" || [$it getNet] ne $og} {error "OT_CORE_INFRA_GATE_COPY_MEMBER_NOT_IN_DOMAIN $path $orig"}
    set protected [$s isDoNotTouch]
    if {$protected} {$s setDoNotTouch 0}
    try {$it disconnect; $it connect $n} finally {if {$protected} {$s setDoNotTouch 1}}
  }
  ot_ci_place $i $x $y $rect
  lappend ::ot_ci_cells $i
  dict set ::ot_ci_tree_out $inst $n
  puts "OT_CORE_INFRA_GATE_COPY $inst of=$orig members=[llength $members]"
}
# FORM C (CORES-EARLY-5): a planned-domain gate drives planned nodes; every sink now on its GCLK net becomes an
# expected tree sink (ot_ci_tree_sink may move it to its planned leaf; ot_ci_tree_finish asserts all were assigned).
proc ot_ci_tree_gate_planned {inst} {
  set n [dict get $::ot_ci_tree_out $inst]
  set k 0
  foreach it [$n getITerms] {if {[$it isInputSignal]} {lappend ::ot_ci_tree_expected $it; incr k}}
  if {$k < 1} {error "OT_CORE_INFRA_GATE_PLANNED_EMPTY $inst"}
  puts "OT_CORE_INFRA_GATE_PLANNED $inst sinks=$k"
}
proc ot_ci_lec_netlist {path} {
  write_verilog $path
  puts "OT_CORE_INFRA_LEC_NETLIST $path (gate copies: kit LEC must run lec.py --netlist on it)"
}
proc ot_ci_tree_domain {inst expected} {
  set n [dict get $::ot_ci_tree_out $inst]
  set k 0
  foreach it [$n getITerms] {if {[$it isInputSignal]} {incr k}}
  # plan census is a pre-synthesis estimate; the gated domain must exist and stay within 10% of it
  if {$k < 1 || abs($k - $expected) > 0.10 * $expected + 1} {
    error "OT_CORE_INFRA_GATE_DOMAIN_CENSUS $inst sinks=$k plan=$expected"
  }
  lappend ::ot_ci_tree_open $n
  puts "OT_CORE_INFRA_GATE $inst domain_sinks=$k plan=$expected"
}
proc ot_ci_tree_open {node} {
  lappend ::ot_ci_tree_open [dict get $::ot_ci_tree_out $node]
}
proc ot_ci_tree_finish {} {
  # On a repeated hook the original clock root now drives only planned nodes;
  # these are excluded from the source census, while leaves stay checked by name.
  foreach it $::ot_ci_tree_expected {
    if {[lsearch -exact $::ot_ci_cells [$it getInst]] >= 0} continue
    if {[lsearch -exact $::ot_ci_tree_seen $it] < 0} {
      error "OT_CORE_INFRA_UNASSIGNED_CLOCK_SINK [[$it getInst] getName]/[[$it getMTerm] getName]"
    }
  }
}
proc ot_ci_union_contains {rect regions} {
  lassign $rect x0 y0 x1 y1
  foreach r $regions {lassign $r a b c d;if {$a <= $x0 && $b <= $y0 && $c >= $x1 && $d >= $y1} {return 1}}
  set cuts [list $x0 $x1]
  foreach r $regions {foreach x [list [lindex $r 0] [lindex $r 2]] {if {$x>$x0 && $x<$x1} {lappend cuts $x}}}
  set cuts [lsort -real -unique $cuts]
  for {set k 1} {$k<[llength $cuts]} {incr k} {
    set x [expr {([lindex $cuts $k]+[lindex $cuts [expr {$k-1}]])/2.0}];set intervals {}
    foreach r $regions {lassign $r a b c d;if {$a <= $x && $c >= $x} {lappend intervals [list $b $d]}}
    set end $y0
    foreach iv [lsort -real -index 0 $intervals] {lassign $iv a b;if {$a>$end} break;if {$b>$end} {set end $b}}
    if {$end<$y1} {return 0}
  }
  return 1
}
proc ot_ci_bay_cell {name x y rect {regions {}}} {
  set i [$::ot_ci_b findInst $name]
  if {$i eq "NULL"} {error "OT_CORE_INFRA_BAY_CELL $name"}
  ot_ci_place $i $x $y $rect
  if {[llength $regions]} {
    set r [$i getBBox];set shape {}
    foreach v [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] {lappend shape [expr {$v/double($::ot_ci_u)}]}
    if {![ot_ci_union_contains $shape $regions]} {error "OT_CORE_INFRA_BAY_UNION_FIT $name"}
  }
  lappend ::ot_ci_fixed $i
}
proc ot_ci_clock_ndr {name width_mult space_mult} {
  set nd [$::ot_ci_b findNonDefaultRule $name]
  set widths {};set spaces {}
  foreach ln {M4 M5} {
    set l [[ord::get_db_tech] findLayer $ln]
    lappend widths $ln [expr {$width_mult*[$l getWidth]/double($::ot_ci_u)}]
    lappend spaces $ln [expr {$space_mult*[$l getSpacing]/double($::ot_ci_u)}]
  }
  if {$nd eq "NULL"} {create_ndr -name $name -width $widths -spacing $spaces;set nd [$::ot_ci_b findNonDefaultRule $name]}
  if {$nd eq "NULL"} {error "OT_CORE_INFRA_CLOCK_NDR_MISSING $name"}
  set count 0
  dict for {node net} $::ot_ci_tree_out {
    if {[$net getNonDefaultRule] ne $nd} {$net setNonDefaultRule $nd}
    $net setSigType CLOCK;incr count
  }
  puts "OT_CORE_CLOCK_NDR $name widths=$widths spaces=$spaces nets=$count"
}
proc ot_ci_entry {name x y} {
  if {[$::ot_ci_b findBTerm $name] eq "NULL"} {error "OT_CORE_INFRA_ENTRY_PIN $name"}
  place_pin -pin_name $name -layer M7 -location [list $x $y] -pin_size $shape
}
proc ot_ci_finish {} {
  # Dedicated FT pins have ONLY their declared buffer terminals. Parent links
  # connect the FT output to the independent core clk/rst input outside the core.
  foreach p $::ot_ci_ports {
    set n [[$::ot_ci_b findBTerm $p] getNet]
    if {[lsort [$n getITerms]] ne [lsort [dict get $::ot_ci_arcs $p]] || [llength [$n getBTerms]] != 1} {
      error "OT_CORE_INFRA_FT_NOT_ISOLATED $p"
    }
  }
  # Bind power BEFORE dont_touch. Native PG rules decide the domain; no guessed
  # VDD/VSS regex or temporary clearing of protection is used.
  ot_pg_bind_batch_before_protect $::ot_ci_b $::ot_ci_cells
  foreach i [concat $::ot_ci_cells $::ot_ci_fixed] {$i setDoNotTouch 1}
  foreach p $::ot_ci_ports {[[ $::ot_ci_b findBTerm $p] getNet] setDoNotTouch 1}
  # CTS-open leaf / gated-domain nets stay buildable: the local tree below the planned stage is CTS-built.
  dict for {node net} $::ot_ci_tree_out {if {[lsearch -exact $::ot_ci_tree_open $net] < 0} {$net setDoNotTouch 1}}
  puts "OT_CORE_INFRA cells=[llength $::ot_ci_cells] ports=[llength $::ot_ci_ports] bay_cells=[llength $::ot_ci_fixed] added_data_cycles=0 added_reset_cycles=0"
}
