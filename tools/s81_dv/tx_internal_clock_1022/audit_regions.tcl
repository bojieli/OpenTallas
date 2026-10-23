# Read-only physical coverage / arrival audit for the exact new TX root map.
# Caller loads exact candidate Liberty/ODB/SDC/parasitics, source clock_spine.tcl,
# source clock_family.tcl, and source the candidate's regional_roots.tcl first.
# Run independently at TT and FF. No timing constraints are changed here.
proc tx_audit_regions {} {
  set block [ord::get_db_block]
  ot_cf_refresh
  set clocks {}
  foreach c [all_clocks] {foreach s [get_property $c sources] {if {[get_full_name $s] eq "ck"} {lappend clocks $c}}}
  if {[llength $clocks] != 1} {error "TX_REGION: ck must own exactly one clock"}
  set clock [lindex $clocks 0]
  lassign [ot_cf_pins $clock] pins owners
  set expected {}
  foreach p $pins {dict set expected [get_full_name $p] soft}
  # Hard child input-clock pins are separate named boundary obligations. Their
  # internal clock insertion remains in their exported ETM timing arcs.
  foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} continue
    foreach it [$inst getITerms] {
      if {[$it getIoType] ne "INPUT" || [[$it getMTerm] getSigType] ne "CLOCK"} continue
      set name "[$inst getName]/[[$it getMTerm] getName]"
      set p [get_pins -quiet $name]
      set cs [get_property $p clocks]
      if {[llength $p] != 1 || [llength $cs] != 1 || [get_full_name $cs] ne [get_full_name $clock]} {
        error "TX_REGION: wrong or missing hard-clock owner $name"
      }
      dict set expected $name hard
    }
  }
  set roots [dict create parent [[$block findBTerm ck] getNet]]
  set stops {}
  dict for {region row} $::ot_sp_internal_roots {
    lassign $row output master input source
    set net [lindex [ot_sp_internal_root $region $row] 0]
    dict set roots $region $net
    set inst [[$block findITerm $output] getInst]
    dict set stops "[$inst getName]/$input" $region
  }
  if {[lsort [dict keys $roots]] ne {ga gb parent}} {error "TX_REGION: exact parent/ga/gb map required"}
  set ownership {}; set netowners {}; set frontiers {}
  dict for {region root} $roots {
    set queue [list $root]; set seen {}; set arrivals {}; set soft 0; set hard 0
    while {[llength $queue]} {
      set net [lindex $queue 0]; set queue [lrange $queue 1 end]
      if {$net in $seen} {error "TX_REGION: clock cycle or reconvergence in $region"}
      lappend seen $net
      if {[dict exists $netowners $net]} {error "TX_REGION: physical root overlap $region"}
      dict set netowners $net $region
      set drivers {}
      foreach it [$net getITerms] {if {[$it getIoType] eq "OUTPUT"} {lappend drivers $it}}
      if {$net eq [dict get $roots parent]} {
        if {[llength $drivers] || [llength [$net getBTerms]] != 1} {error "TX_REGION: ambiguous parent source net"}
      } elseif {[llength $drivers] != 1 || [llength [$net getBTerms]]} {
        error "TX_REGION: multiple drivers or exported internal clock net"
      }
      foreach it [$net getITerms] {
        if {[$it getIoType] ne "INPUT"} continue
        set name "[[$it getInst] getName]/[[$it getMTerm] getName]"
        if {[dict exists $stops $name]} {
          if {$region ne "parent"} {error "TX_REGION: regional root nested in $region"}
          dict incr frontiers [dict get $stops $name]
          continue
        }
        if {[dict exists $expected $name]} {
          if {[dict exists $ownership $name]} {error "TX_REGION: duplicate clock leaf $name"}
          dict set ownership $name $region
          set p [get_pins -quiet $name]
          set a [ot_cf_wire $p $clock]
          if {![string is double -strict $a] || $a in {Inf -Inf NaN}} {error "TX_REGION: missing physical arrival $name"}
          lappend arrivals $a
          if {[dict get $expected $name] eq "hard"} {incr hard} else {incr soft}
          puts "TX_REGION_PIN $region [dict get $expected $name] $name $a"
          continue
        }
        set c [get_cells -quiet [[$it getInst] getName]]
        set lc [get_lib_cells -quiet -of_objects $c]
        set inputs [get_pins -quiet -of_objects $c -filter {direction == input}]
        set outputs [get_pins -quiet -of_objects $c -filter {direction == output}]
        if {[llength $c] != 1 || [llength $lc] != 1 || ![get_property $lc is_buffer]
            || [llength $inputs] != 1 || [llength $outputs] != 1} {
          error "TX_REGION: non-clock leaf or non-unary clock logic $name"
        }
        set next [$block findITerm [get_full_name $outputs]]
        set onet [$next getNet]
        if {$onet eq "NULL" || $onet eq ""} {error "TX_REGION: open clock buffer $name"}
        lappend queue $onet
      }
    }
    if {!$soft || ![llength $arrivals]} {error "TX_REGION: empty actual register population $region"}
    set lo [tcl::mathfunc::min {*}$arrivals]; set hi [tcl::mathfunc::max {*}$arrivals]
    puts "TX_REGION_SUMMARY $region soft=$soft hard=$hard nets=[llength $seen] min=$lo max=$hi spread=[expr {$hi-$lo}]"
  }
  if {[dict size $ownership] != [dict size $expected]} {
    set missing {}; dict for {name kind} $expected {if {![dict exists $ownership $name]} {lappend missing $name}}
    error "TX_REGION: unowned sequential or hard clock pins $missing"
  }
  if {[dict size $frontiers] != 2 || [dict get $frontiers ga] != 1 || [dict get $frontiers gb] != 1} {
    error "TX_REGION: exact regional source coverage missing"
  }
  puts "TX_REGION_COVERAGE PASS sinks=[dict size $ownership] regions=3"
}
