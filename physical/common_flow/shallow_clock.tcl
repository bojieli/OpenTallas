# Explicit opt-in only: source defines commands; setup is the sole entry point.
# Planned trunk on free legal rows -> existing density taps -> local TritonCTS.
# All coordinates passed to node are lower-left DBU. No data/FF movement is allowed.
if {[info exists ::ot_dtsh::version]} { return }
namespace eval ::ot_dtsh {
  variable version 1
  variable active 0
  variable ndr ""
  variable blk
  variable root
  variable master
  variable taps {}
  variable nodes {}
  variable leaves {}
  variable rows {}
  variable occupied {}
  variable original {}
  variable ff_data {}
  variable root_extra {}
  variable ymin
  variable rowheight
}
proc ::ot_dtsh::sigpins {inst dir} {
  set result {}
  foreach it [$inst getITerms] {
    if {[$it getSigType] ne "SIGNAL" && [$it getSigType] ne "CLOCK"} continue
    if {[[$it getMTerm] getIoType] eq $dir} { lappend result $it }
  }
  return $result
}
proc ::ot_dtsh::box {inst} {
  set b [$inst getBBox]
  return [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}
proc ::ot_dtsh::occ_add {name bounds} {
  variable occupied; variable ymin; variable rowheight
  lassign $bounds x0 y0 x1 y1
  set lo [expr {int(floor(double($y0-$ymin)/$rowheight))}]
  set hi [expr {int(floor(double($y1-1-$ymin)/$rowheight))}]
  for {set k $lo} {$k <= $hi} {incr k} { dict lappend occupied $k [list $name $x0 $y0 $x1 $y1] }
}
proc ::ot_dtsh::pg {inst} {
  variable blk
  set n 0
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getSigType] ni {POWER GROUND}} continue
    set net [$blk findNet [$mt getName]]
    if {$net eq "NULL" || $net eq ""} { error "OT_DTSH missing actual supply [$mt getName]" }
    $it connect $net
    incr n
  }
  if {!$n} { error "OT_DTSH no PG pins for [$inst getName]" }
}
proc ::ot_dtsh::capture {} {
  variable blk; variable rows; variable occupied; variable original; variable ff_data
  variable ymin; variable rowheight
  set core [$blk getCoreArea]
  set ymin [$core yMin]
  set rows {}; set occupied {}; set original {}; set ff_data {}
  foreach row [$blk getRows] {
    lassign [$row getOrigin] x y
    set s [$row getSite]
    set h [$s getHeight]
    if {![info exists rowheight]} { set rowheight $h }
    if {$h != $rowheight} { error "OT_DTSH mixed row heights need explicit planner/runtime support" }
    dict lappend rows $y [list $x [$row getSpacing] [$row getSiteCount] $h [$row getOrient]]
  }
  if {![dict size $rows]} { error "OT_DTSH no physical rows" }
  foreach inst [$blk getInsts] {
    if {[$inst getPlacementStatus] ni {PLACED FIRM LOCKED COVER}} continue
    set name [$inst getName]
    set bounds [box $inst]
    dict set original $name [list $bounds [$inst getOrient] [[$inst getMaster] getName]]
    occ_add $name $bounds
    if {[string match *DFF* [[$inst getMaster] getName]]} {
      foreach it [$inst getITerms] {
        set mt [$it getMTerm]; set pin [$mt getName]
        if {[$mt getSigType] in {POWER GROUND CLOCK} || $pin in {CLK CK CP}} continue
        set net [$it getNet]
        dict set ff_data [list $name $pin] [expr {$net eq "NULL" || $net eq "" ? "" : [$net getName]}]
      }
    }
  }
}
proc ::ot_dtsh::export {path} {
  variable blk; variable root; variable master; variable taps
  set f [open $path w]
  puts $f "DBU\t[$blk getDbUnitsPerMicron]"
  set b [$blk getCoreArea]
  puts $f "CORE\t[$b xMin]\t[$b yMin]\t[$b xMax]\t[$b yMax]"
  set bt [$root getBTerms]
  if {[llength $bt] != 1} { close $f; error "OT_DTSH root net needs one actual source BTerm" }
  set bt [lindex $bt 0]; set b [$bt getBBox]
  puts $f "ROOT\t[expr {([$b xMin]+[$b xMax])/2}]\t[expr {([$b yMin]+[$b yMax])/2}]"
  puts $f "ROOT_NAME\t[$bt getName]"
  puts $f "MASTER\t[$master getName]\t[$master getWidth]\t[$master getHeight]"
  foreach row [$blk getRows] {
    lassign [$row getOrigin] x y
    set site [$row getSite]
    puts $f "ROW\t$x\t$y\t[$site getWidth]\t[$site getHeight]\t[$row getSiteCount]"
    puts $f "ROW_ORIENT\t[$row getName]\t$x\t$y\t[$row getOrient]\t[$row getSpacing]\t[$row getDirection]"
  }
  foreach inst [$blk getInsts] {
    if {[$inst getPlacementStatus] ni {PLACED FIRM LOCKED COVER}} continue
    set b [$inst getBBox]
    puts $f "CELL\t[$inst getName]\t[$b xMin]\t[$b yMin]\t[$b xMax]\t[$b yMax]\t[expr {[[$inst getMaster] isBlock] ? 1 : 0}]"
  }
  dict for {name info} $taps {
    set inst [$blk findInst $name]; set b [$inst getBBox]
    puts $f "TAP\t$name\t[expr {([$b xMin]+[$b xMax])/2}]\t[expr {([$b yMin]+[$b yMax])/2}]\t[[[dict get $info input] getNet] getName]\t[[dict get $info output] getName]"
  }
  close $f
}
proc ::ot_dtsh::parent_net {parent} {
  variable root; variable nodes
  if {$parent eq "@root"} { return $root }
  if {![dict exists $nodes $parent]} { error "OT_DTSH parent $parent not already emitted" }
  return [dict get $nodes $parent net]
}
proc ::ot_dtsh::check_site {x y orient} {
  variable rows; variable occupied; variable master; variable ymin; variable rowheight
  if {![string is integer -strict $x] || ![string is integer -strict $y]} { error "OT_DTSH node needs integer DBU coordinates" }
  set w [$master getWidth]; set h [$master getHeight]
  set legal 0
  if {[dict exists $rows $y]} {
    foreach row [dict get $rows $y] {
      lassign $row rx pitch count rh ro
      if {$orient eq $ro && $h <= $rh && $x >= $rx && ($x-$rx)%$pitch == 0 && $x+$w <= $rx+$pitch*$count} { set legal 1; break }
    }
  }
  if {!$legal} { error "OT_DTSH planned node is not row/site/orientation legal: $x $y $orient" }
  set lo [expr {int(floor(double($y-$ymin)/$rowheight))}]
  set hi [expr {int(floor(double($y+$h-1-$ymin)/$rowheight))}]
  for {set k $lo} {$k <= $hi} {incr k} {
    if {![dict exists $occupied $k]} continue
    foreach b [dict get $occupied $k] {
      lassign $b nm x0 y0 x1 y1
      if {$x < $x1 && $x+$w > $x0 && $y < $y1 && $y+$h > $y0} { error "OT_DTSH planned node overlaps $nm: $x $y" }
    }
  }
}
proc ::ot_dtsh::node {name x y orient parent} {
  variable blk; variable master; variable nodes
  if {[$blk findInst $name] ne "NULL" || [$blk findNet ${name}_Y] ne "NULL"} { error "OT_DTSH planned name already exists: $name" }
  set pn [parent_net $parent]
  check_site $x $y $orient
  set inst [odb::dbInst_create $blk $master $name]
  $inst setOrient $orient; $inst setLocation $x $y
  set bounds [box $inst]
  if {[lrange $bounds 0 1] ne [list $x $y]} { error "OT_DTSH lower-left location mismatch for $name" }
  $inst setPlacementStatus FIRM
  set net [odb::dbNet_create $blk ${name}_Y]
  $net setSigType CLOCK
  set ip [sigpins $inst INPUT]; set op [sigpins $inst OUTPUT]
  if {[llength $ip] != 1 || [llength $op] != 1} { error "OT_DTSH trunk master is not a single-input/single-output buffer" }
  [lindex $ip 0] connect $pn
  [lindex $op 0] connect $net
  pg $inst
  $inst setDoNotTouch true; $net setDoNotTouch true
  dict set nodes $name [dict create inst $inst net $net parent $pn input [lindex $ip 0] output [lindex $op 0] box $bounds orient $orient]
  occ_add $name $bounds
}
proc ::ot_dtsh::leaf {name parent} {
  variable taps; variable leaves; variable blk
  if {![dict exists $taps $name] || [dict exists $leaves $name]} { error "OT_DTSH missing/duplicate selected tap $name" }
  set pn [parent_net $parent]
  set ip [dict get $taps $name input]
  $ip disconnect; $ip connect $pn
  set inst [$blk findInst $name]
  # Preserve the already legalised tap position and its own local tree interface.
  pg $inst
  $inst setPlacementStatus FIRM; $inst setDoNotTouch true
  dict set leaves $name $pn
}
proc ::ot_dtsh::audit {} {
  variable blk; variable nodes; variable leaves; variable taps; variable original; variable ff_data; variable root; variable root_extra; variable ndr
  if {$ndr ne ""} {
    if {[$root getNonDefaultRule] ne $ndr} { error "OT_DTSH root NDR changed" }
    dict for {name info} $nodes {
      if {[[dict get $info net] getNonDefaultRule] ne $ndr} { error "OT_DTSH trunk NDR changed at $name" }
    }
  }
  if {[lsort [dict keys $leaves]] ne [lsort [dict keys $taps]]} { error "OT_DTSH incomplete density-tap coverage" }
  dict for {name state} $original {
    set inst [$blk findInst $name]
    if {$inst eq "NULL" || [list [box $inst] [$inst getOrient] [[$inst getMaster] getName]] ne $state} { error "OT_DTSH moved/resized existing cell $name" }
  }
  dict for {key expected} $ff_data {
    lassign $key name pin
    set it [[$blk findInst $name] findITerm $pin]; set n [$it getNet]
    set got [expr {$n eq "NULL" || $n eq "" ? "" : [$n getName]}]
    if {$got ne $expected} { error "OT_DTSH changed FF data/control pin $name/$pin" }
  }
  set expected $root_extra
  dict for {name info} $nodes {
    set inst [dict get $info inst]; set net [dict get $info net]; set pn [dict get $info parent]
    if {[box $inst] ne [dict get $info box] || [$inst getOrient] ne [dict get $info orient]
        || ![$inst isDoNotTouch] || [$inst getPlacementStatus] ne "FIRM"
        || [[dict get $info input] getNet] ne $pn || [[dict get $info output] getNet] ne $net} { error "OT_DTSH planned trunk changed at $name" }
    set want {}
    dict for {child ci} $nodes { if {[dict get $ci parent] eq $net} { lappend want [dict get $ci input] } }
    dict for {leaf ln} $leaves { if {$ln eq $net} { lappend want [dict get $taps $leaf input] } }
    set got {}
    foreach it [$net getITerms] { if {[$it isInputSignal]} { lappend got $it } }
    if {[lsort $got] ne [lsort $want]} { error "OT_DTSH insertion/removal on planned net [$net getName]" }
    if {$pn eq $root} { lappend expected [dict get $info input] }
  }
  set got {}
  foreach it [$root getITerms] { if {[$it isInputSignal]} { lappend got $it } }
  dict for {name pn} $leaves { if {$pn eq $root} { lappend expected [dict get $taps $name input] } }
  if {[lsort $got] ne [lsort $expected]} { error "OT_DTSH root trunk connectivity changed" }
  dict for {name pn} $leaves {
    if {[[dict get $taps $name input] getNet] ne $pn || [[dict get $taps $name output_pin] getNet] ne [dict get $taps $name output]} { error "OT_DTSH density-tap interface changed at $name" }
  }
  puts "OT_DTSH AUDIT PASS: [dict size $nodes] frozen planned nodes, [dict size $leaves] existing taps; all [dict size $original] existing placements and FF data/control unchanged"
}
# Explicit prototype opt-in: leave local CTS nets on their normal routing rule.
proc ::ot_dtsh::trunk_ndr {} {
  variable blk; variable root; variable nodes; variable ndr
  if {![info exists ::env(OT_DTSH_NDR)] || $::env(OT_DTSH_NDR) eq ""} { return }
  if {$::env(OT_DTSH_NDR) ne "4w"} { error "OT_DTSH unknown NDR option $::env(OT_DTSH_NDR)" }
  set tech [[ord::get_db] getTech]
  set dbu [$blk getDbUnitsPerMicron]
  set widths {}; set spacings {}
  foreach name {M2 M3 M4 M5 M6 M7} {
    set layer [$tech findLayer $name]
    if {$layer eq "NULL"} { error "OT_DTSH NDR missing layer $name" }
    lappend widths $name [expr {4.0*[$layer getWidth]/$dbu}]
    lappend spacings $name [expr {2.0*[$layer getSpacing]/$dbu}]
  }
  set name ot_dtsh_4w2s
  if {[$tech findNonDefaultRule $name] ne "NULL"} { error "OT_DTSH NDR name already exists: $name" }
  create_ndr -name $name -width $widths -spacing $spacings
  set ndr [$tech findNonDefaultRule $name]
  if {$ndr eq "NULL"} { error "OT_DTSH NDR was not created" }
  $root setNonDefaultRule $ndr
  dict for {node info} $nodes { [dict get $info net] setNonDefaultRule $ndr }
  puts "OT_DTSH NDR: 4x technology width / 2x spacing M2-M7, planned root/trunk only"
}
proc ::ot_dtsh::bind_new_pg {} {
  variable blk; variable original; variable nodes
  foreach inst [$blk getInsts] {
    set name [$inst getName]
    if {[dict exists $original $name] || [dict exists $nodes $name]} continue
    if {![regexp {^(BUF|INV|HB|CKBUF|CKINV)} [[$inst getMaster] getName]]} { error "OT_DTSH unexpected non-clock new instance $name" }
    pg $inst
  }
}
proc ::ot_dtsh::cts {args} {
  variable active; variable taps; variable blk
  if {!$active} { error "OT_DTSH CTS wrapper without completed explicit setup" }
  audit
  set nets {}
  dict for {name info} $taps { lappend nets [[dict get $info output] getName] }
  set keep {}
  for {set k 0} {$k < [llength $args]} {incr k} {
    set arg [lindex $args $k]
    if {$arg eq "-repair_clock_nets"} continue
    if {$arg eq "-clk_nets"} {
      incr k
      if {$k >= [llength $args]} { error "OT_DTSH -clk_nets value missing" }
      continue
    }
    lappend keep $arg
  }
  set result [cts_orig {*}$keep -clk_nets [join $nets " "]]
  # New trunk cells are PG-connected before any RC estimation. Only local roots
  # may receive wire/slew repair; global repair_clock_nets would touch the trunk.
  bind_new_pg
  estimate_parasitics -placement
  est::check_parasitics
  set max_wire [rsz::check_max_wire_length 0 true]
  foreach name $nets {
    set net [$blk findNet $name]
    if {$net eq "NULL"} { error "OT_DTSH local CTS net disappeared: $name" }
    rsz::repair_net_cmd [sta::db_net_to_sta $net] $max_wire 0 0
  }
  bind_new_pg
  audit
  puts "OT_DTSH CTS PASS: selected [llength $nets] existing density-tap output nets; no planned-trunk insertion before POST_CTS"
  return $result
}
proc ::ot_dtsh::setup {block tap_list root_net cell} {
  variable active; variable blk; variable root; variable master; variable taps; variable nodes; variable leaves; variable root_extra
  if {$active || [llength [info commands ::ot_dtsh::cts_orig]]} { error "OT_DTSH setup may run only once per database/process" }
  set blk $block; set root $root_net
  set master [[ord::get_db] findMaster $cell]
  if {$root eq "NULL" || $master eq "NULL" || ![llength $tap_list]} { error "OT_DTSH explicit root/master/taps missing" }
  set taps {}; set nodes {}; set leaves {}; set root_extra {}
  foreach t $tap_list {
    set name ot_dtap_[lindex $t 0]
    set inst [$blk findInst $name]
    if {$inst eq "NULL" || [dict exists $taps $name]} { error "OT_DTSH missing/duplicate actual tap $name" }
    set ip [sigpins $inst INPUT]; set op [sigpins $inst OUTPUT]
    if {[llength $ip] != 1 || [llength $op] != 1 || [[lindex $op 0] getNet] ne [lindex $t 3]} { error "OT_DTSH actual tap interface mismatch $name" }
    dict set taps $name [dict create input [lindex $ip 0] output_pin [lindex $op 0] output [lindex $t 3]]
  }
  foreach it [$root getITerms] {
    if {![$it isInputSignal]} continue
    set istap 0
    dict for {name info} $taps { if {[dict get $info input] eq $it} { set istap 1; break } }
    if {!$istap} { lappend root_extra $it }
  }
  capture
  set dir [expr {[info exists ::env(OT_SHALLOW_CLOCK_DIR)] ? $::env(OT_SHALLOW_CLOCK_DIR) : ([info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : "/work")}]
  file mkdir $dir
  set geom [file join $dir ot_dtsh_geometry.tsv]
  set plan [file join $dir ot_dtsh_plan.json]
  set apply [file join $dir ot_dtsh_apply.tcl]
  export $geom
  puts [exec python3 /work/shallow_clock.py $geom --out $plan --apply $apply]
  # The planner emits only node/leaf calls. Guard all names, free footprints,
  # row orientations and complete tap coverage as each operation is applied.
  uplevel #0 [list source $apply]
  if {![dict size $nodes]} { error "OT_DTSH planner emitted no physical trunk nodes" }
  $root setDoNotTouch true
  trunk_ndr
  audit
  rename ::clock_tree_synthesis ::ot_dtsh::cts_orig
  proc ::clock_tree_synthesis {args} { return [::ot_dtsh::cts {*}$args] }
  set active 1
  puts "OT_DTSH SETUP PASS: geometry $geom plan $plan; planned trunk frozen, default flow unchanged until explicit setup"
}
