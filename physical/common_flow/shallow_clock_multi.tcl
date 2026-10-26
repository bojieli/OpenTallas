# Explicit opt-in multi-port root controller. Source alongside shallow_clock.tcl.
# Each port has separate planner state; local TritonCTS is called ONCE globally.
if {[namespace exists ::ot_dtsh_multi]} { return }
namespace eval ::ot_dtsh_multi {
  variable source_dir [file dirname [file normalize [info script]]]
  variable active 0
  variable cts_called 0
  variable contexts {}
  variable owners {}
  variable original {}
  variable ff_data {}
  variable block
}
if {![llength [info commands ::ot_dtsh::node]]} {
  source [file join $::ot_dtsh_multi::source_dir shallow_clock.tcl]
}
proc ::ot_dtsh_multi::clone_context {ns} {
  namespace eval $ns {}
  foreach p [info procs ::ot_dtsh::*] {
    set name [namespace tail $p]
    if {$name in {setup cts cts_orig}} continue
    set args {}
    foreach arg [info args $p] {
      if {[info default $p $arg value]} { lappend args [list $arg $value] } else { lappend args $arg }
    }
    set body [info body $p]
    set body [string map [list ::ot_dtsh:: ${ns}:: ot_dtsh:: ${ns}::] $body]
    if {$name eq "closed_loop"} {
      if {[string first {uplevel #0 [list source $moves]} $body] < 0} {
        error "OT_DTSH_MULTI unsupported closed-loop apply interface"
      }
      set body [string map [list {uplevel #0 [list source $moves]} {source_apply $moves}] $body]
    }
    proc ${ns}::$name $args $body
  }
  # Generated commands keep numeric globally unique IDs in JSON and TSV.
  # Only their command namespace is retargeted, never node or tap identities.
  proc ${ns}::source_apply {path} {
    set f [open $path]; set text [read $f]; close $f
    foreach line [split $text \n] {
      set line [string trim $line]
      if {$line eq "" || [string index $line 0] eq "#"} continue
      if {![regexp {^ot_dtsh::(node|leaf|relocate_begin|relocate|relocate_end)( |$)} $line]} {
        error "OT_DTSH_MULTI unexpected generated command"
      }
    }
    set text [string map [list ot_dtsh:: [namespace current]::] $text]
    uplevel #0 $text
  }
  rename ${ns}::measure_sinks ${ns}::measure_sinks_raw
  proc ${ns}::measure_sinks {path} {
    variable sink_targets; variable root_port
    measure_sinks_raw ${path}.raw.tsv
    ::ot_dtsh_multi::normalize_measurement $path $sink_targets $root_port
  }
  foreach {name value} {active 0 ndr {} taps {} nodes {} leaves {} rows {} occupied {} original {} ff_data {} root_extra {} sink_targets {} root_port {}} {
    set ${ns}::$name $value
  }
}
proc ::ot_dtsh_multi::finite {value} {
  return [expr {[string is double -strict $value] && ![regexp -nocase {nan|inf} $value]}]
}
proc ::ot_dtsh_multi::validate_targets {cfg names} {
  if {![dict exists $cfg sink_targets_ps]} { return {} }
  set targets [dict get $cfg sink_targets_ps]
  if {[lsort [dict keys $targets]] ne [lsort $names]} { error "OT_DTSH_MULTI target membership must exactly cover the root's taps" }
  dict for {name profile} $targets {
    foreach corner {tt ff} {
      if {![dict exists $profile $corner] || ![finite [dict get $profile $corner]] || [dict get $profile $corner] <= 0} {
        error "OT_DTSH_MULTI target $name needs explicit finite positive TT AND FF"
      }
    }
    if {![dict exists $profile basis] || [dict get $profile basis] ni {BUDGET MEASURED}} { error "OT_DTSH_MULTI target $name needs explicit BUDGET/MEASURED basis" }
  }
  return $targets
}
proc ::ot_dtsh_multi::normalize_measurement {path targets port} {
  set raw [open ${path}.raw.tsv r]; set lines [split [read $raw] \n];close $raw
  set normalized {};set seen {}
  set report [open ${path}.targets.tsv w]
  puts $report "root\ttap\traw_tt_ps\traw_ff_ps\ttarget_tt_ps\ttarget_ff_ps\tbasis\tobjective_tt_ps\tobjective_ff_ps\tqualification"
  foreach line $lines {
    if {[string trim $line] eq ""} continue
    set fields [split [string trim $line]]
    if {[llength $fields] != 4 || [lindex $fields 0] ni {T B} || ![finite [lindex $fields 2]] || ![finite [lindex $fields 3]]} { close $report;error "OT_DTSH_MULTI malformed actual measurement" }
    lassign $fields kind name tt ff
    if {$kind eq "T" && [dict size $targets]} {
      if {![dict exists $targets $name] || [dict exists $seen $name]} { close $report;error "OT_DTSH_MULTI measured target membership mismatch" }
      dict set seen $name 1
      set profile [dict get $targets $name]
      set target_tt [dict get $profile tt];set target_ff [dict get $profile ff]
      set objective_tt [expr {$tt-$target_tt+250.0}]
      set objective_ff [expr {$ff-$target_ff+202.5}]
      puts $report "$port\t$name\t$tt\t$ff\t$target_tt\t$target_ff\t[dict get $profile basis]\t$objective_tt\t$objective_ff\tPROVISIONAL_OBJECTIVE_ONLY"
      lappend normalized "T $name $objective_tt $objective_ff"
    } else { lappend normalized $line }
  }
  close $report
  if {[dict size $targets] && [lsort [dict keys $targets]] ne [lsort [dict keys $seen]]} { error "OT_DTSH_MULTI incomplete actual target measurement" }
  set output [open $path w];puts $output [join $normalized \n];close $output
}
proc ::ot_dtsh_multi::clock_for_port {port} {
  set found {}
  foreach clock [all_clocks] {
    foreach source [get_property $clock sources] {
      if {[get_full_name $source] eq $port} { lappend found [get_full_name $clock] }
    }
  }
  set found [lsort -unique $found]
  if {[llength $found] != 1} { error "OT_DTSH_MULTI port $port must have one actual timing clock" }
  return [lindex $found 0]
}
proc ::ot_dtsh_multi::validate_roots {blk roots} {
  if {![dict size $roots]} { error "OT_DTSH_MULTI empty explicit roots" }
  set nets {}; set taps {}; set outputs {}; set clocks {}
  dict for {port cfg} $roots {
    if {![regexp {^[A-Za-z_][A-Za-z0-9_]*$} $port]} { error "OT_DTSH_MULTI unsafe port identity" }
    set root [dict get $cfg root_net]
    set bt [$blk findBTerm $port]
    if {$bt eq "NULL" || $root eq "NULL" || [$bt getNet] ne $root || [$bt getIoType] ne "INPUT"} {
      error "OT_DTSH_MULTI root does not match actual input BTerm $port"
    }
    if {[dict exists $nets $root] || [llength [$root getBTerms]] != 1} { error "OT_DTSH_MULTI aliased/nonexclusive root BTerms" }
    dict set nets $root $port
    lappend clocks [clock_for_port $port]
    set list [dict get $cfg tap_list]
    if {![llength $list]} { error "OT_DTSH_MULTI root $port has no selected density taps" }
    set selected {}
    foreach tap $list {
      if {[llength $tap] != 4 || ![string is integer -strict [lindex $tap 0]]} { error "OT_DTSH_MULTI malformed tap tuple" }
      set name ot_dtap_[lindex $tap 0]
      if {[dict exists $taps $name]} { error "OT_DTSH_MULTI tap owned by two roots: $name" }
      set inst [$blk findInst $name]
      if {$inst eq "NULL"} { error "OT_DTSH_MULTI missing tap $name" }
      set ip [::ot_dtsh::sigpins $inst INPUT]; set op [::ot_dtsh::sigpins $inst OUTPUT]
      if {[llength $ip] != 1 || [llength $op] != 1 || [[lindex $ip 0] getNet] ne $root
          || [[lindex $op 0] getNet] ne [lindex $tap 3]} { error "OT_DTSH_MULTI tap/root or output ownership mismatch $name" }
      set output [lindex $tap 3]
      if {$output eq "NULL" || [dict exists $outputs $output]} { error "OT_DTSH_MULTI duplicate/missing local output net" }
      dict set taps $name $port; dict set outputs $output $name
      lappend selected $name
    }
    validate_targets $cfg $selected
  }
  if {[llength [lsort -unique $clocks]] != 1} { error "OT_DTSH_MULTI roots must belong to the same actual timing clock" }
  # Every existing selected-root density buffer must have an explicit owner.
  dict for {root port} $nets {
    foreach it [$root getITerms] {
      if {![$it isInputSignal]} continue
      set name [[$it getInst] getName]
      if {[string match ot_dtap_* $name] && ![dict exists $taps $name]} { error "OT_DTSH_MULTI unowned density tap $name" }
    }
  }
  return $taps
}
proc ::ot_dtsh_multi::refresh_occupancy {ns} {
  variable original; variable ff_data
  ${ns}::capture
  # Other roots' planned nodes remain occupied, but are not immutable original
  # cells. One baseline is shared by all contexts throughout both phases.
  set ${ns}::original $original
  set ${ns}::ff_data $ff_data
}
proc ::ot_dtsh_multi::refresh_geometry {ns geom} {
  # The Python placer must see other roots and local CTS buffers at their
  # current positions, but must be free to relocate this root's own nodes.
  ${ns}::export $geom
  set input [open $geom r];set lines [split [read $input] \n];close $input
  set output [open $geom w]
  foreach line $lines {
    set fields [split $line \t]
    if {[lindex $fields 0] eq "CELL" && [dict exists [set ${ns}::nodes] [lindex $fields 1]]} continue
    if {$line ne ""} { puts $output $line }
  }
  close $output
}
proc ::ot_dtsh_multi::audit {} {
  variable contexts; variable owners; variable block
  set seen {}; set allnodes {}
  dict for {port cfg} $contexts {
    set ns [dict get $cfg namespace]
    set bt [$block findBTerm $port]
    if {$bt eq "NULL" || [$bt getNet] ne [dict get $cfg root_net] || [llength [[dict get $cfg root_net] getBTerms]] != 1} { error "OT_DTSH_MULTI physical root source changed: $port" }
    if {[set ${ns}::root] ne [dict get $cfg root_net]} { error "OT_DTSH_MULTI root state overwritten: $port" }
    dict for {name info} [set ${ns}::taps] {
      if {[dict exists $seen $name] || ![dict exists $owners $name] || [dict get $owners $name] ne $port} { error "OT_DTSH_MULTI lost/disjoint ownership at $name" }
      dict set seen $name $port
    }
    foreach name [dict keys [set ${ns}::nodes]] {
      if {[dict exists $allnodes $name]} { error "OT_DTSH_MULTI planned node identity collision" }
      dict set allnodes $name $port
    }
    ${ns}::audit
  }
  if {[lsort [dict keys $seen]] ne [lsort [dict keys $owners]]} { error "OT_DTSH_MULTI incomplete global tap coverage" }
  puts "OT_DTSH_MULTI AUDIT PASS: [dict size $contexts] separate roots, [dict size $seen] disjoint taps, [dict size $allnodes] unique nodes; one immutable placement/FF baseline"
}
proc ::ot_dtsh_multi::phase {metric tag} {
  variable contexts
  dict for {port cfg} $contexts {
    set ns [dict get $cfg namespace]
    refresh_occupancy $ns
    refresh_geometry $ns [lindex [dict get $cfg cl_args] 1]
    ${ns}::closed_loop {*}[dict get $cfg cl_args] $metric $tag
  }
}
proc ::ot_dtsh_multi::cts {args} {
  variable active; variable contexts; variable block; variable cts_called
  if {$cts_called} { error "OT_DTSH_MULTI global CTS may run only once" }
  if {!$active} { error "OT_DTSH_MULTI CTS before completed explicit setup" }
  audit
  set nets {}
  dict for {port cfg} $contexts {
    set ns [dict get $cfg namespace]
    dict for {name info} [set ${ns}::taps] { lappend nets [[dict get $info output] getName] }
  }
  if {[llength $nets] != [llength [lsort -unique $nets]]} { error "OT_DTSH_MULTI local CTS net aliases" }
  set keep {}
  for {set k 0} {$k < [llength $args]} {incr k} {
    set arg [lindex $args $k]
    if {$arg eq "-repair_clock_nets"} continue
    if {$arg eq "-clk_nets"} { incr k; if {$k >= [llength $args]} { error "OT_DTSH_MULTI -clk_nets missing value" }; continue }
    lappend keep $arg
  }
  set cts_called 1
  set result [cts_orig {*}$keep -clk_nets [join $nets " "]]
  dict for {port cfg} $contexts { [dict get $cfg namespace]::bind_new_pg }
  estimate_parasitics -placement
  est::check_parasitics
  set maxwire [rsz::check_max_wire_length 0 true]
  foreach name $nets {
    set net [$block findNet $name]
    if {$net eq "NULL"} { error "OT_DTSH_MULTI local net disappeared" }
    rsz::repair_net_cmd [sta::db_net_to_sta $net] $maxwire 0 0
  }
  dict for {port cfg} $contexts { [dict get $cfg namespace]::bind_new_pg }
  if {[info exists ::env(OT_DTSH_CL_SINK)] && $::env(OT_DTSH_CL_SINK) eq "1"} {
    phase measure_sinks _sink
  }
  audit
  puts "OT_DTSH_MULTI CTS PASS: ONE global CTS call, [dict size $contexts] roots, [llength $nets] selected local output nets; cross-root TT/FF CPPR and port-referred insertion still require actual STA"
  return $result
}
proc ::ot_dtsh_multi::setup {blk roots cell} {
  variable active; variable contexts; variable owners; variable original; variable ff_data; variable block; variable source_dir
  if {$active || $::ot_dtsh::active || [llength [info commands ::ot_dtsh::cts_orig]] || [llength [info commands ::ot_dtsh_multi::cts_orig]]} {
    error "OT_DTSH_MULTI one controller per database; single-root setup already active"
  }
  set owners [validate_roots $blk $roots]
  set block $blk
  set master [[ord::get_db] findMaster $cell]
  if {$master eq "NULL"} { error "OT_DTSH_MULTI missing physical trunk master" }
  set base [expr {[info exists ::env(OT_SHALLOW_CLOCK_DIR)] ? $::env(OT_SHALLOW_CLOCK_DIR) : ([info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : "/work")}]
  set next_id 0; set ordinal 0
  dict for {port cfg} $roots {
    set ns ::ot_dtsh_multi::r$ordinal
    clone_context $ns
    set ${ns}::blk $blk; set ${ns}::root [dict get $cfg root_net]; set ${ns}::master $master
    set ${ns}::root_port $port
    set names {};foreach tap [dict get $cfg tap_list] { lappend names ot_dtap_[lindex $tap 0] }
    set ${ns}::sink_targets [validate_targets $cfg $names]
    foreach tap [dict get $cfg tap_list] {
      set name ot_dtap_[lindex $tap 0]; set inst [$blk findInst $name]
      dict set ${ns}::taps $name [dict create input [lindex [::ot_dtsh::sigpins $inst INPUT] 0] output_pin [lindex [::ot_dtsh::sigpins $inst OUTPUT] 0] output [lindex $tap 3]]
    }
    foreach it [[dict get $cfg root_net] getITerms] {
      if {![$it isInputSignal]} continue
      set istap 0
      dict for {name info} [set ${ns}::taps] { if {[dict get $info input] eq $it} { set istap 1; break } }
      if {!$istap} { lappend ${ns}::root_extra $it }
    }
    ${ns}::capture
    if {!$ordinal} { set original [set ${ns}::original]; set ff_data [set ${ns}::ff_data] }
    set ${ns}::original $original; set ${ns}::ff_data $ff_data
    set dir [file join $base ot_dtsh_root$ordinal]; file mkdir $dir
    set geom [file join $dir geometry.tsv]; set plan [file join $dir plan.json]; set apply [file join $dir apply.tcl]
    ${ns}::export $geom
    set cl [expr {[info exists ::env(OT_DTSH_CLOSED_LOOP)] && $::env(OT_DTSH_CLOSED_LOOP) eq "1"}]
    set output [exec python3 [file join $source_dir shallow_clock_multi.py] $geom --out $plan --apply $apply --node-offset $next_id {*}[expr {$cl ? "--closed-loop" : ""}]]
    puts $output
    if {![regexp {OT_DTSH_MULTI_NODE_IDS offset ([0-9]+) next ([0-9]+)} $output -> old next] || $old != $next_id || $next <= $next_id} { error "OT_DTSH_MULTI invalid global node allocation" }
    set next_id $next
    ${ns}::source_apply $apply
    if {![dict size [set ${ns}::nodes]]} { error "OT_DTSH_MULTI empty physical trunk" }
    dict set contexts $port [dict create namespace $ns root_net [dict get $cfg root_net] cl_args [list $dir $geom $plan]]
    incr ordinal
  }
  # One actual shared NDR, propagated to every root and every planned trunk net.
  set first [dict get $contexts [lindex [dict keys $contexts] 0] namespace]
  ${first}::trunk_ndr
  set ndr [set ${first}::ndr]
  dict for {port cfg} $contexts {
    set ns [dict get $cfg namespace]; set ${ns}::ndr $ndr
    if {$ndr ne ""} {
      [set ${ns}::root] setNonDefaultRule $ndr
      dict for {name info} [set ${ns}::nodes] { [dict get $info net] setNonDefaultRule $ndr }
    }
  }
  if {$cl} { phase measure {} }
  dict for {port cfg} $contexts { [dict get $cfg namespace]::freeze }
  audit
  rename ::clock_tree_synthesis ::ot_dtsh_multi::cts_orig
  proc ::clock_tree_synthesis {args} { return [::ot_dtsh_multi::cts {*}$args] }
  set active 1
  set ::ot_dtsh::active 1  ;# reserve the controller against a later singleton setup
  puts "OT_DTSH_MULTI SETUP PASS: [dict size $contexts] separately owned roots, one global CTS controller; default single-root behavior unchanged"
}
