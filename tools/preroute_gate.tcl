# Pre-route timing gate (OWNER 2026-10-08, stream preroute-gate): per-path-class setup summary right after placement.
#
# Runs inside OpenROAD on a placed design with placement parasitics (ORFS POST DETAIL_PLACE: 3_4 resizer repair_design +
# detailed placement done, ideal clocks, estimate_parasitics -placement) or offline on 3_place.odb + 3_place.sdc:
#   read_lef/liberty ...; read_db 3_place.odb; read_sdc 3_place.sdc; source setRC.tcl; estimate_parasitics -placement
#   source tools/preroute_gate.tcl; ot_preroute_dump out.json
# The dump holds, per path class (reg2reg / macro / io), the worst setup slack, a slack histogram of every endpoint's worst
# path down to OT_PREROUTE_SLACK_CAP (default +300 ps) and the worst paths; tools/preroute_gate.py judges it.
# In the flow (closure loop, OT_PREROUTE_GATE=1) tools/orfs_hold_mm.py patches ORFS util.tcl so that the POST DETAIL_PLACE
# hook calls ot_preroute_gate_flow: dump, judge, and on a FAIL stop the flow with "PREROUTE_MARGIN: <summary>" (the loop
# turns that into verdict PREROUTE_MARGIN).  OT_PREROUTE_GATE_ADVISORY=1 (or a judge that only warns) reports, never stops.

set ::ot_prg_dir [file dirname [file normalize [info script]]]

proc ot_prg_q {s} { return "\"[string map {\\ \\\\ \" \\\" \n " "} $s]\"" }

proc ot_prg_macro_names {} {
  # STA full names of BLOCK-master (macro) instances
  set out [dict create]
  foreach inst [[ord::get_db_block] getInsts] {
    if {[[$inst getMaster] isBlock]} {
      dict set out [$inst getName] 1
    }
  }
  return $out
}

proc ot_prg_kind {pin macros} {
  # port / macro / reg for a path start or end pin
  set n [get_full_name $pin]
  if {[get_property $pin is_port]} { return port }
  set i [string last "/" $n]
  if {$i > 0 && [dict exists $macros [string range $n 0 [expr {$i - 1}]]]} { return macro }
  return reg
}

proc ot_preroute_dump {out} {
  set t0 [clock milliseconds]
  set cap [expr {[info exists ::env(OT_PREROUTE_SLACK_CAP)] ? $::env(OT_PREROUTE_SLACK_CAP) : 300.0}]
  set maxn [expr {[info exists ::env(OT_PREROUTE_MAX_PATHS)] ? $::env(OT_PREROUTE_MAX_PATHS) : 300000}]
  set bin 25.0
  # time unit scale: sta reports in the user unit (ps for ASAP7); convert a 1 ns probe to know
  set ::ot_prg_scale 1.0
  if {![catch {sta::unit_scale time} u] && [string is double -strict $u] && $u > 0} { set ::ot_prg_scale [expr {$u * 1e12}] }
  set capu [expr {$cap / $::ot_prg_scale}]
  set macros [ot_prg_macro_names]
  set period ""
  foreach c [all_clocks] {
    set p [expr {[get_property $c period] * $::ot_prg_scale}]
    if {$period eq "" || $p < $period} { set period $p }
  }
  set paths [find_timing_paths -path_delay max -group_path_count $maxn -endpoint_path_count 1 -slack_max $capu]
  set t1 [clock milliseconds]
  array set ws {}; array set hist {}; array set cnt {}; array set worst {}
  set seen [dict create]
  set n 0
  foreach p $paths {
    set s [get_property $p slack]
    if {$s eq "INF"} { continue }
    set s [expr {double($s) * $::ot_prg_scale}]
    set sp [get_property $p startpoint]
    set ep [get_property $p endpoint]
    set en [get_full_name $ep]
    # one endpoint may sit in several path groups: keep its worst
    if {[dict exists $seen $en] && [dict get $seen $en] <= $s} { continue }
    set sk [ot_prg_kind $sp $macros]
    set ek [ot_prg_kind $ep $macros]
    if {$sk eq "port" || $ek eq "port"} {
      set cls io
    } elseif {$sk eq "macro" || $ek eq "macro"} {
      set cls macro
    } else {
      set cls reg2reg
    }
    if {[dict exists $seen $en]} {
      # replaced: drop the earlier (better) entry's histogram count
      lassign [dict get $seen ${en},meta] ocls obin
      incr hist($ocls,$obin) -1
      incr cnt($ocls) -1
    }
    set b [expr {int(floor($s / $bin))}]
    dict set seen $en $s
    dict set seen ${en},meta [list $cls $b]
    incr hist($cls,$b)
    incr cnt($cls)
    incr n
    if {![info exists ws($cls)] || $s < $ws($cls)} { set ws($cls) $s }
    lappend worst($cls) [list $s [get_full_name $sp] $en $sk $ek [get_property [get_property $p endpoint_clock] full_name]]
  }
  set t2 [clock milliseconds]
  set f [open $out w]
  puts $f "\{\"period_ps\": [expr {$period eq "" ? "null" : $period}], \"slack_cap_ps\": $cap, \"bin_ps\": $bin,"
  puts $f " \"paths\": [llength $paths], \"max_paths\": $maxn, \"truncated\": [expr {[llength $paths] >= $maxn ? "true" : "false"}],"
  puts $f " \"macros\": [dict size $macros], \"find_ms\": [expr {$t1 - $t0}], \"classify_ms\": [expr {$t2 - $t1}],"
  foreach v {OT_MM_SETUP_CORNER CORNER OT_ORFS_CORNER DESIGN_NAME DESIGN_NICKNAME} {
    if {[info exists ::env($v)]} { puts $f " [ot_prg_q env_$v]: [ot_prg_q $::env($v)]," }
  }
  set cs {}
  foreach cls {reg2reg macro io} {
    set h {}
    foreach k [lsort [array names hist "$cls,*"]] {
      set v $hist($k)
      if {$v > 0} { lappend h "\"[lindex [split $k ,] 1]\": $v" }
    }
    set wl {}
    if {[info exists worst($cls)]} {
      foreach w [lrange [lsort -real -index 0 $worst($cls)] 0 9] {
        lassign $w s a e sk ek ck
        lappend wl "\{\"slack_ps\": [format %.1f $s], \"start\": [ot_prg_q $a], \"end\": [ot_prg_q $e], \"start_kind\": \"$sk\", \"end_kind\": \"$ek\", \"clock\": [ot_prg_q $ck]\}"
      }
    }
    lappend cs "[ot_prg_q $cls]: \{\"ws_ps\": [expr {[info exists ws($cls)] ? [format %.1f $ws($cls)] : "null"}], \"endpoints\": [expr {[info exists cnt($cls)] ? $cnt($cls) : 0}], \"hist\": \{[join $h ,]\}, \"worst\": \[[join $wl ,]\]\}"
  }
  puts $f " \"classes\": \{[join $cs ,\n]\}\}"
  close $f
  puts "OT_PREROUTE_GATE: dump $out ([llength $paths] paths <= +$cap ps, find [expr {$t1 - $t0}] ms, classify [expr {$t2 - $t1}] ms)"
}

proc ot_preroute_gate_flow {} {
  if {![info exists ::env(OT_PREROUTE_GATE)] || $::env(OT_PREROUTE_GATE) in {"" 0 false}} { return }
  set py [expr {[info exists ::env(OT_PREROUTE_GATE_PY)] ? $::env(OT_PREROUTE_GATE_PY) : "$::ot_prg_dir/preroute_gate.py"}]
  set outdir $::env(REPORTS_DIR)
  set dump $outdir/preroute_gate_dump.json
  set rep $outdir/preroute_gate.json
  set t0 [clock milliseconds]
  if {[catch {ot_preroute_dump $dump} msg]} {
    puts "OT_PREROUTE_GATE: dump failed ($msg): gate skipped"
    return
  }
  set args [list python3 $py check $dump --out $rep --dump-ms [expr {[clock milliseconds] - $t0}]]
  if {[info exists ::env(OT_PREROUTE_GATE_ARGS)]} { lappend args {*}$::env(OT_PREROUTE_GATE_ARGS) }
  set rc [catch {exec {*}$args 2>@1} res]
  puts $res
  puts "OT_PREROUTE_GATE: [expr {([clock milliseconds] - $t0) / 1000.0}] s"
  if {[file isdirectory /ot_fplint]} { catch {file copy -force $rep /ot_fplint/preroute_gate.json} }
  if {$rc && [regexp {PREROUTE_MARGIN} $res]} {
    if {[info exists ::env(OT_PREROUTE_GATE_ADVISORY)] && $::env(OT_PREROUTE_GATE_ADVISORY) ni {"" 0 false}} {
      puts "OT_PREROUTE_GATE: advisory only, flow continues"
      return
    }
    if {[file isdirectory /ot_fplint]} {
      set fh [open /ot_fplint/PREROUTE_FAIL w]; puts $fh $res; close $fh
    }
    error "PREROUTE_MARGIN: pre-route timing gate failed after placement (see $rep)"
  } elseif {$rc} {
    puts "OT_PREROUTE_GATE: judge error (not a verdict), flow continues: $res"
  }
}
