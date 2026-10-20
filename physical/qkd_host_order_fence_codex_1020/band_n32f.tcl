# Exact ORDER native-source hard band; no shared helper changes.
set pf_b [ord::get_db_block]
set pf_u [$pf_b getDbUnitsPerMicron]
set pf_name ot_order_band_n32f
if {[$pf_b findRegion $pf_name] ne "NULL"} { error "ORDER_BAND: region already exists; refuse duplicate hook" }
set pf_boxes {{2.16 216.0 343.44 300.24}}
set pf_anchor [dict create]
# These exact kits disable inhold/outhold; io_flop_at_pins owns both input
# and output anchors in this one file. No hold-file absence is waived.
set pf_path [file join $::env(RESULTS_DIR) ot_out_flop_at_pins.txt]
if {![file exists $pf_path]} { error "ORDER_BAND: missing actual pin-anchor list $pf_path" }
set pf_f [open $pf_path r]
foreach pf_n [split [read $pf_f] "\n"] {
  if {$pf_n eq ""} continue
  if {[dict exists $pf_anchor $pf_n]} { error "ORDER_BAND: duplicate anchor $pf_n" }
  set pf_i [$pf_b findInst $pf_n]
  if {$pf_i eq "NULL"} { error "ORDER_BAND: missing listed anchor $pf_n" }
  if {[$pf_i getPlacementStatus] ni {FIRM LOCKED}} { error "ORDER_BAND: listed anchor not fixed: $pf_n" }
  dict set pf_anchor $pf_n 1
}
close $pf_f
if {[file exists [file join $::env(RESULTS_DIR) ot_inhold_firm.txt]]} {
  error "ORDER_BAND: unexpected input-hold ownership file for exact inhold=false kit"
}
set pf_members {}; set pf_area 0.0
set cnt [dict create anchor 0 physical 0 macro 0 central 0]
set pf_rep [open [file join $::env(RESULTS_DIR) ot_order_band_members.tsv] w]
puts $pf_rep "instance\tmaster\tstatus\tclass"
foreach pf_i [$pf_b getInsts] {
  set nm [$pf_i getName]; set st [$pf_i getPlacementStatus]; set m [$pf_i getMaster]; set mn [$m getName]
  if {[$m isBlock]} { dict incr cnt macro; continue }
  set sig 0
  foreach it [$pf_i getITerms] { set n [$it getNet]; if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} { set sig 1; break } }
  if {[dict exists $pf_anchor $nm]} { set cls anchor
  } elseif {!$sig} { set cls physical
  } else {
    # Every non-boundary functional standard cell is fenced, including ties,
    # port buffers/inverters and clock buffers. No name-based exemption.
    if {$st in {FIRM LOCKED COVER}} { error "ORDER_BAND: unowned fixed functional cell $nm" }
    set cls central
    if {[$pf_i getGroup] ne "NULL"} { error "ORDER_BAND: preexisting group on $nm; refuse overwrite" }
    lappend pf_members $pf_i
    set pf_area [expr {$pf_area + double([$m getWidth]) * [$m getHeight] / $pf_u / $pf_u}]
  }
  dict incr cnt $cls
  puts $pf_rep "$nm\t$mn\t$st\t$cls"
}
close $pf_rep
set pf_cap 0.0
foreach bb $pf_boxes { lassign $bb x0 y0 x1 y1; set pf_cap [expr {$pf_cap + ($x1-$x0)*($y1-$y0)}] }
puts [format "ORDER_BAND n32f classes %s area_um2=%.3f capacity_um2=%.1f util=%.4f" $cnt $pf_area $pf_cap [expr {$pf_area / $pf_cap}]]
if {[dict get $cnt anchor] < 1000} { error "ORDER_BAND: only [dict get $cnt anchor] pin-anchored cells; classification implausible" }
if {[llength $pf_members] < 1500} { error "ORDER_BAND: only [llength $pf_members] central cells; classification implausible" }
if {[dict get $cnt macro] != 6} { error "ORDER_BAND: expected 6 SRAM macros, found [dict get $cnt macro]" }
if {$pf_area > 0.6 * $pf_cap} { error "ORDER_BAND: central area $pf_area exceeds 60% of the fence" }
set pf_r [odb::dbRegion_create $pf_b $pf_name]
foreach bb $pf_boxes { odb::dbBox_create $pf_r {*}[lmap v $bb {expr {round($v * $pf_u)}}] }
$pf_r setRegionType INCLUSIVE
set pf_g [odb::dbGroup_create $pf_r ${pf_name}_group]
foreach pf_i $pf_members { $pf_g addInst $pf_i }
puts "ORDER_BAND n32f fenced [llength $pf_members] cells"
