# Shared die-net repeater step (DIE-FLOW 2026-10-17; owner ruling HANDOFF 0cl, memory reach-405-repeaters-1016).
#
# One step for every die flow (S81 dietop_grt_sta, Qwen qwen_kv_die/chain grt.tcl, HBM die_case_v16, die_cluster
# cluster tops).  Sourced inside the caller's OpenROAD session after the die is placed and the libraries are read,
# before global_route.  Generated call: tools/die_repeaters/step.py (tcl_call / `step.py tcl`).
#
# What it does, and only this:
#   * repair_design on die nets with -max_wire_length MAX_WIRE (default 160 um: H-REACH measured an unrepeated hop
#     slew-limited at ~175 um at the native ot_inhold first cell; repeated BUFx8-class every ~160 um gives 600-750 um
#     per cycle) and set_max_transition = the native receiver input slew (default 260 ps, the closed views'
#     max_transition at the first native cell; a per-master table may only LOWER it).  The ETM pin models hide that
#     first cell, so the limit is set here, not taken from the ETM pins.
#   * buffers only (BUFx4..BUFx8 by default): every other lib cell is dont_use for the step (restored afterwards), so
#     the resizer can neither insert nor resize-into anything else -- never a register, never a hold cell.
#   * clock / reset distribution nets are untouched (dont_touch): every net on a register clock / clock lib pin, every
#     net whose odb sig type is CLOCK / POWER / GROUND or that is special, and the caller's name globs.
#   * relay stages unchanged by construction and CHECKED: every pre-existing instance survives with its master, every
#     new instance is an allowed buffer.  Any violation fails the step (caller exits non-zero).
#   * die nets longer than the die reach (planning defect: a missing relay register, standard 1) are measured before
#     repair from report_long_wires and reported; policy 'fail' makes them a step violation.
#   * legalisation of the new buffers: 'snap' (ot_cluster_snap_legalize of tools/die_cluster/cluster_bounds.tcl --
#     die-scale safe), 'dpl' (detailed_placement; small dies only), or 'none' (caller legalises).
# Output: the JSON report (schema opentallas.die_repeaters.v1).  Returns the number of violations.

proc ot_die_rep_log {msg} { puts "OT_DIE_REP $msg"; flush stdout }

proc ot_die_rep_inst_map {blk} {
  set m [dict create]
  foreach inst [$blk getInsts] { dict set m [$inst getName] [[$inst getMaster] getName] }
  return $m
}

proc ot_die_rep_json_str {s} { return "\"[string map {\\ \\\\ \" \\\"} $s]\"" }

# cfg: Tcl dict; keys (defaults): report (required), max_wire_um 160, slew_ps 260, receiver_slew {} (master ps ...),
# buffers {BUFx4_ASAP7_75t_R ...}, skip_nets {} (globs), repeat_nets {} (globs: forwarded-clock nets repeated WITH their
# data bits -- DIE-CLOCK accepts fclk repeaters matched to the data to +-1 stage; they override the clock skips), skip_sigtypes {CLOCK POWER GROUND}, skip_clock_pins 1,
# reach_um 0, over_reach report|fail, long_wire_scan 5000, rc_layer M4 ("" = keep caller's), repair_args "",
# legalize snap|dpl|none, bounds_tcl /work/cluster_bounds.tcl, libs {} (liberty files to read first), std_corner ""
# (TT|FF|SS: read the ASAP7 RVT std libs of that corner), design ""
proc ot_die_repeaters {cfg} {
  set t0 [clock seconds]
  set d [dict create max_wire_um 160 slew_ps 260 receiver_slew {} \
           buffers {BUFx4_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx8_ASAP7_75t_R} \
           skip_nets {} repeat_nets {} skip_sigtypes {CLOCK POWER GROUND} skip_clock_pins 1 reach_um 0 over_reach report \
           long_wire_scan 5000 rc_layer M4 repair_args "" legalize snap bounds_tcl /work/cluster_bounds.tcl \
           libs {} std_corner "" design ""]
  set d [dict merge $d $cfg]
  dict with d {}
  if {![info exists report]} { error "ot_die_repeaters: cfg has no report path" }
  set viol 0; set notes {}
  foreach l $libs { if {![file exists $l]} { error "ot_die_repeaters: liberty missing $l" }; read_liberty $l }
  if {$std_corner ne ""} {
    foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${std_corner}_nldm_*.lib*] { read_liberty $l }
  }
  set blk [ord::get_db_block]
  foreach b $buffers { if {![llength [get_lib_cells -quiet $b]]} { error "ot_die_repeaters: buffer $b not in any liberty" } }

  # ---- pre-state
  set pre [ot_die_rep_inst_map $blk]
  set masters [lsort -unique [dict values $pre]]
  ot_die_rep_log "pre instances=[dict size $pre] masters=[llength $masters]"
  # fail closed: a master without liberty hides its pins from the resizer (its nets would silently stay unrepeated)
  set nolib {}
  foreach mst $masters {
    if {[llength [get_lib_cells -quiet $mst]]} { continue }
    set dm [[ord::get_db] findMaster $mst]; set nsig 0
    if {$dm ne "NULL" && $dm ne ""} { foreach mt [$dm getMTerms] { if {[$mt getSigType] eq "SIGNAL"} { incr nsig } } }
    if {$nsig > 0} { lappend nolib $mst }
  }
  if {[llength $nolib]} { incr viol [llength $nolib]; lappend notes "masters without liberty (nets invisible to repair): [lrange $nolib 0 19]" }

  # ---- native receiver slew: the global limit, lowered by any present master's own first-cell limit
  set slew $slew_ps; set slew_src default
  foreach {mst ps} $receiver_slew { if {[lsearch -exact $masters $mst] >= 0 && $ps < $slew} { set slew $ps; set slew_src $mst } }

  # ---- nets the step must not touch
  set skip [dict create]
  if {[llength $skip_nets]} { foreach n [get_nets -quiet $skip_nets] { dict set skip [get_full_name $n] glob } }
  set n_sig 0
  if {[llength $skip_sigtypes]} {
    foreach net [$blk getNets] {
      if {[$net isSpecial] || [lsearch -exact $skip_sigtypes [$net getSigType]] >= 0} { dict set skip [$net getName] sigtype; incr n_sig }
    }
  }
  set n_ck 0
  if {$skip_clock_pins} {
    set ckp [dict create]
    foreach mst $masters {
      set lc [lindex [get_lib_cells -quiet $mst] 0]
      if {$lc eq ""} { continue }
      set ps {}
      foreach lp [get_lib_pins -quiet -of_objects $lc] {
        set isck 0
        catch {set isck [expr {[get_property $lp is_register_clock] || [get_property $lp is_clock]}]}
        if {$isck} { lappend ps [get_name $lp] }
      }
      if {[llength $ps]} { dict set ckp $mst $ps }
    }
    foreach inst [$blk getInsts] {
      set mst [[$inst getMaster] getName]
      if {![dict exists $ckp $mst]} { continue }
      foreach p [dict get $ckp $mst] {
        set it [$inst findITerm $p]
        if {$it eq "NULL" || $it eq ""} { continue }
        set net [$it getNet]
        if {$net eq "NULL" || $net eq ""} { continue }
        if {![dict exists $skip [$net getName]]} { dict set skip [$net getName] clock_pin; incr n_ck }
      }
    }
  }
  set n_rep 0
  if {[llength $repeat_nets]} {
    foreach n [get_nets -quiet $repeat_nets] { set nm [get_full_name $n]; if {[dict exists $skip $nm] && [dict get $skip $nm] ne "glob"} { dict unset skip $nm; incr n_rep } }
  }
  set skip_names [dict keys $skip]
  set dt {}
  foreach n $skip_names { set o [get_nets -quiet [string map {\[ \\[ \] \\]} $n]]; if {[llength $o]} { lappend dt {*}$o } }
  if {[llength $dt]} { set_dont_touch $dt }
  set skip_iterms [dict create]
  foreach n $skip_names { set net [$blk findNet $n]; if {$net ne "NULL" && $net ne ""} { dict set skip_iterms $n [llength [$net getITerms]] } }
  ot_die_rep_log "skip nets=[llength $skip_names] (sigtype $n_sig, clock pins $n_ck; repeated forwarded clocks $n_rep) dont_touch=[llength $dt]"

  # ---- RC + limits
  if {$rc_layer ne ""} {
    source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
    set_wire_rc -signal -layer $rc_layer
  }
  set_max_transition $slew [current_design]
  estimate_parasitics -placement

  # ---- standard 1: die nets longer than the reach (no relay register) -- measured before any buffer goes in
  set over {}; set longest 0.0; set scanned 0
  if {$long_wire_scan > 0} {
    set lw [file rootname $report].long_wires.rpt
    report_long_wires $long_wire_scan > $lw
    set fh [open $lw]; set txt [read $fh]; close $fh
    foreach line [split $txt "\n"] {
      if {![regexp {^(\S+)\s+manhtn\s+([0-9.]+)\s+steiner\s+([0-9.]+)} $line -> drv man st]} { continue }
      incr scanned
      set net ""
      set k [string last / $drv]
      if {$k > 0} {
        set inst [$blk findInst [string range $drv 0 [expr {$k - 1}]]]
        if {$inst ne "NULL" && $inst ne ""} {
          set it [$inst findITerm [string range $drv [expr {$k + 1}] end]]
          if {$it ne "NULL" && $it ne ""} { set n_ [$it getNet]; if {$n_ ne "NULL" && $n_ ne ""} { set net [$n_ getName] } }
        }
      } else {
        set bt [$blk findBTerm $drv]
        if {$bt ne "NULL" && $bt ne ""} { set n_ [$bt getNet]; if {$n_ ne "NULL" && $n_ ne ""} { set net [$n_ getName] } }
      }
      if {$net ne "" && [dict exists $skip $net]} { continue }
      if {$st > $longest} { set longest $st }
      if {$reach_um > 0 && $st > $reach_um} { lappend over [list $net $drv $st] }
    }
    ot_die_rep_log "long wires scanned=$scanned longest_um=[format %.1f $longest] over_reach($reach_um)=[llength $over]"
    if {[llength $over] && $over_reach eq "fail"} { incr viol [llength $over]; lappend notes "over_reach nets: missing relay registers" }
  }

  # ---- buffers only: everything else dont_use for this step (restored after)
  set flagged {}
  foreach lc [get_lib_cells -quiet *] {
    if {[lsearch -exact $buffers [get_name $lc]] >= 0} { continue }
    if {![get_property $lc dont_use]} { lappend flagged $lc }
  }
  foreach lc $flagged { set_dont_use $lc }
  foreach b $buffers { unset_dont_use [get_lib_cells -quiet $b] }

  set r0 [clock seconds]
  set rc [catch {eval repair_design -max_wire_length $max_wire_um -slew_margin 0 -cap_margin 0 $repair_args} err]
  foreach lc $flagged { unset_dont_use $lc }
  if {$rc} { ot_die_rep_log "FAIL repair_design: $err"; error "ot_die_repeaters: repair_design: $err" }
  set repair_s [expr {[clock seconds] - $r0}]

  # ---- legalise the new buffers
  set legal "none"
  if {$legalize eq "snap"} {
    if {![llength [info procs ot_cluster_snap_legalize]]} { source $bounds_tcl }
    set left [ot_cluster_snap_legalize [file rootname $report].snap.json]
    set legal "snap still_on_macro=$left"
    if {$left != 0} { incr viol $left; lappend notes "repeaters left on a hard macro: $left" }
  } elseif {$legalize eq "dpl"} {
    if {[catch {detailed_placement} e]} { incr viol; lappend notes "detailed_placement: $e"; set legal "dpl FAIL" } else { set legal dpl }
  }

  # ---- post-state checks: relay stages / registers unchanged, buffers only, skip nets untouched
  set post [ot_die_rep_inst_map $blk]
  set removed 0; set changed 0; set bad_new 0; set by_master [dict create]; set examples {}
  dict for {n m} $pre {
    if {![dict exists $post $n]} { incr removed; if {[llength $examples] < 10} { lappend examples "removed $n" } } \
    elseif {[dict get $post $n] ne $m} { incr changed; if {[llength $examples] < 10} { lappend examples "resized $n $m->[dict get $post $n]" } }
  }
  dict for {n m} $post {
    if {[dict exists $pre $n]} { continue }
    dict incr by_master $m
    if {[lsearch -exact $buffers $m] < 0} { incr bad_new; if {[llength $examples] < 10} { lappend examples "inserted $n $m" } }
  }
  set skip_changed 0
  dict for {n c} $skip_iterms { set net [$blk findNet $n]; if {$net eq "NULL" || $net eq "" || [llength [$net getITerms]] != $c} { incr skip_changed } }
  set repeaters [expr {[dict size $post] - [dict size $pre] + $removed}]
  incr viol [expr {$removed + $changed + $bad_new + $skip_changed}]
  if {$removed} { lappend notes "pre-existing instances removed" }
  if {$changed} { lappend notes "pre-existing instances resized (registers / relay stages must stay unchanged)" }
  if {$bad_new} { lappend notes "non-buffer cells inserted" }
  if {$skip_changed} { lappend notes "clock/reset/skip nets modified" }
  set verdict [expr {$viol == 0 ? "PASS" : "FAIL"}]

  set f [open $report w]
  set bm {}; dict for {m c} $by_master { lappend bm "[ot_die_rep_json_str $m]: $c" }
  set ov {}; foreach o [lrange [lsort -real -decreasing -index 2 $over] 0 49] { lappend ov "\[[ot_die_rep_json_str [lindex $o 0]], [ot_die_rep_json_str [lindex $o 1]], [lindex $o 2]\]" }
  set nt {}; foreach n $notes { lappend nt [ot_die_rep_json_str $n] }
  set ex {}; foreach n $examples { lappend ex [ot_die_rep_json_str $n] }
  puts $f "{\"schema\": \"opentallas.die_repeaters.v1\", \"design\": [ot_die_rep_json_str $design], \"verdict\": \"$verdict\", \"violations\": $viol,"
  puts $f " \"rule\": \"repair_design on die nets only, buffers only, between relay registers; one repeater from ~175 um then every ~160 um (owner 0cl, H-REACH)\","
  puts $f " \"max_wire_um\": $max_wire_um, \"max_transition_ps\": $slew, \"max_transition_source\": [ot_die_rep_json_str $slew_src], \"rc_layer\": [ot_die_rep_json_str $rc_layer],"
  puts $f " \"repair_args\": [ot_die_rep_json_str $repair_args], \"legalize\": [ot_die_rep_json_str $legal],"
  puts $f " \"instances_pre\": [dict size $pre], \"instances_post\": [dict size $post], \"repeaters\": $repeaters, \"repeaters_by_master\": {[join $bm {, }]},"
  puts $f " \"removed\": $removed, \"resized\": $changed, \"non_buffer_inserted\": $bad_new, \"skip_nets\": [llength $skip_names], \"skip_nets_modified\": $skip_changed,"
  puts $f " \"skip_by\": {\"sigtype\": $n_sig, \"clock_pin\": $n_ck, \"glob\": [expr {[llength $skip_names] - $n_sig - $n_ck + $n_rep}]}, \"repeated_clock_nets\": $n_rep, \"masters_without_liberty\": [llength $nolib],"
  puts $f " \"reach_um\": $reach_um, \"over_reach_policy\": [ot_die_rep_json_str $over_reach], \"long_wires_scanned\": $scanned, \"longest_um\": $longest, \"over_reach_nets\": [llength $over], \"over_reach_top\": \[[join $ov {, }]\],"
  puts $f " \"notes\": \[[join $nt {, }]\], \"examples\": \[[join $ex {, }]\], \"repair_s\": $repair_s, \"seconds\": [expr {[clock seconds] - $t0}]}"
  close $f
  ot_die_rep_log "$verdict repeaters=$repeaters violations=$viol over_reach=[llength $over] legalize=($legal) s=[expr {[clock seconds] - $t0}]"
  return $viol
}
