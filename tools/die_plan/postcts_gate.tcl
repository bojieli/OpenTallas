# postcts_gate.tcl -- FLOW 2026-10-25 post-CTS gate before route (GEOM-REVIEW / GEOM-REVIEW-2 [FLOW] 05:00).
# One corner per run (env OT_CORNER = TT | FF): 4_cts.odb, kit SDC with the vclk bound for THAT corner
# (OT_VCLK_TT / OT_VCLK_FF), placement parasitics on the kit's RC basis (LAYER_PARASITICS_FILE, the RCX-calibrated
# setRC_rcx.tcl by default), propagated clocks.  Pin-register set = the registers the sign-off clock check uses
# (fanout of the data inputs, fanin of the outputs).  Writes /work/postcts_gate_<corner>.json:
#   pin-reg CK arrival mean / min / max / n, bound I, |mean - bound|, setup / hold WNS (estimate), verdict.
# Verdict FAIL when |mean - bound| > OT_POSTCTS_TOL (default 20 ps): the route would carry a wrong I into sign-off.
set C $::env(OT_CORNER)
# outside make (runner calls openroad directly): take the kit exports from /work/config.mk
if {[file exists /work/config.mk]} {
  set fh [open /work/config.mk]
  foreach ln [split [read $fh] "\n"] {
    if {[regexp {^export\s+(OT_VCLK_TT|OT_VCLK_FF|LAYER_PARASITICS_FILE|OT_PINREG_GROUP_GUARD|OT_PINREG_HOLD_CENSUS|OT_TAP_GRT_PRE)\s*\??=\s*(\S+)} $ln -> k v] && ![info exists ::env($k)]} {
      set ::env($k) $v
    }
  }
  close $fh
}
set c [string tolower $C]
# BEGIN embedded exact library selector
# Resolve the exact libraries selected by this kit's ORFS make configuration.
# No directory glob or installed-version fallback is permitted.
proc ot_lib_json_string {value} {
  return "\"[string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $value]\""
}
proc ot_lib_validate {corner files} {
  if {$corner ni {TT FF SS}} {error "OT_TIMING_LIBS: unsupported corner $corner"}
  if {![llength $files]} {error "OT_TIMING_LIBS: empty exact library list"}
  set seen {}; set groups {}; set present {}
  foreach f $files {
    if {[file pathtype $f] ne "absolute"} {error "OT_TIMING_LIBS: relative library $f"}
    if {[regexp {[*?\[\]$]} $f] || ![file isfile $f]} {error "OT_TIMING_LIBS: missing or unresolved library $f"}
    set path [file normalize $f]
    if {[dict exists $seen $path]} {error "OT_TIMING_LIBS: duplicate library $f"}
    dict set seen $path 1
    if {[regexp {^asap7sc7p5t_([^_]+)_(RVT|LVT|SLVT)_(TT|FF|SS)_nldm_} [file tail $f] -> group vt actual]} {
      if {$actual ne $corner} {error "OT_TIMING_LIBS: wrong corner $f"}
      set key $group/$vt
      if {[dict exists $groups $key]} {error "OT_TIMING_LIBS: ambiguous installed versions for $key"}
      dict set groups $key $path
      dict set present $group 1
    } elseif {[regexp -nocase {_(tt|ff|ss|typ)\.lib(?:\.gz)?$} [file tail $f] -> actual]} {
      set actual [string toupper $actual]
      if {$actual eq "TYP"} {set actual TT}
      if {$actual ne $corner} {error "OT_TIMING_LIBS: wrong macro corner $f"}
    }
  }
  foreach group {AO INVBUF OA SEQ SIMPLE} {
    if {![dict exists $present $group]} {error "OT_TIMING_LIBS: missing standard-cell group $group"}
  }
  return $files
}
proc ot_lib_resolve {corner {config /work/config.mk}} {
  if {![file isfile $config]} {error "OT_TIMING_LIBS: missing exact ORFS config $config"}
  set field [dict get {TT TC_LIB_FILES FF BC_LIB_FILES SS WC_LIB_FILES} $corner]
  set output [exec bash -c {source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 || exit; exec make --no-print-directory -s -C /OpenROAD-flow-scripts/flow "DESIGN_CONFIG=$1" "print-$2"} otlibs $config $field]
  set records {}
  foreach line [split $output \n] {
    if {[regexp "^${field}\\s*\[:=\]\\s*(.*)$" $line -> value]} {lappend records $value}
  }
  if {[llength $records] != 1} {error "OT_TIMING_LIBS: missing or ambiguous make $field result"}
  set files [regexp -all -inline {\S+} [lindex $records 0]]
  return [ot_lib_validate $corner $files]
}
proc ot_lib_load {corner receipt {config /work/config.mk}} {
  if {[file exists $receipt]} {file rename $receipt ${receipt}.previous.[clock clicks]}
  set files [ot_lib_resolve $corner $config]
  set rows {}
  foreach f $files {
    set digest [lindex [exec sha256sum -- $f] 0]
    lappend rows "{\"path\":[ot_lib_json_string $f],\"sha256\":[ot_lib_json_string $digest]}"
  }
  set digest [lindex [exec sha256sum -- $config] 0]
  foreach f $files {read_liberty $f}
  set fp [open $receipt w]
  puts $fp "{\"status\":\"LOADED\",\"corner\":[ot_lib_json_string $corner],\"source\":\"ORFS make print corner LIB_FILES\",\"config\":[ot_lib_json_string $config],\"config_sha256\":[ot_lib_json_string $digest],\"libraries\":\[[join $rows ,]\]}"
  close $fp
  puts "OT_TIMING_LIBS $corner exact_count [llength $files] receipt $receipt"
  return $files
}
# END embedded exact library selector
set libtag [expr {[info exists ::env(OT_POSTCTS_TAG)] ? $::env(OT_POSTCTS_TAG) : "postcts_gate"}]
ot_lib_load $C /work/${libtag}_${c}.libraries.json
read_db $::env(ODB)
read_sdc /work/constraint.sdc
set bound [expr {$C eq "FF" ? $::env(OT_VCLK_FF) : $::env(OT_VCLK_TT)}]
set tol [expr {[info exists ::env(OT_POSTCTS_TOL)] ? $::env(OT_POSTCTS_TOL) : 20.0}]
set vck [lsearch -all -inline -not [all_clocks] [get_clocks clk]]
if {[llength $vck] == 1} { set_clock_latency -source $bound $vck }
if {[info exists ::env(LAYER_PARASITICS_FILE)] && [file exists $::env(LAYER_PARASITICS_FILE)]} {
  source $::env(LAYER_PARASITICS_FILE)
} else {
  source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
}
# 5_1_grt.odb carries the global routes: use them (the basis the RCX calibration was fitted on, est - RCX <= 5 ps);
# a CTS / placement odb falls back to the placement estimate (set_wire_rc) -> informational only.
# Propagated clocks BEFORE estimate_parasitics: rsz -placement skips nets driven from an ideal clock, so estimating
# first left the clock tree with no wire RC and read the pin-register CK ~55-62 ps early (KITS-SPARE ve_m 193 vs 316,
# FLOW 09:41 10-25; the earlier "placement reads ~75 ps early" rr_h0 note was this).  FLOW-INFRA-2 A/B 10-25 on the
# head + KV canary 5_1_grt.odb: -global_routing is order-independent (bit-identical); fixed placement reads +10..+13 ps.
set_propagated_clock [get_clocks clk]
set ot_pg_mode placement
if {[info exists ::env(OT_POSTCTS_GRT)] && $::env(OT_POSTCTS_GRT) && ![catch {estimate_parasitics -global_routing}]} {
  set ot_pg_mode global_routing
} else {
  estimate_parasitics -placement
}
set per [get_property [get_clocks clk] period]
foreach cf [list /work/clock_family.tcl [file join [file dirname [info script]] clock_family.tcl]] {
  if {[file exists $cf]} { source $cf; break }
}
if {[llength [info commands ot_cf_refresh]]} { catch {ot_cf_refresh} }
if {![llength [info commands ot_cf_pinregs]]} { error "postcts_gate: canonical pin-register collector missing" }
set bnd [ot_cf_pinregs]
set measured [ot_cf_pinreg_measure [get_clocks clk]]
set n [dict get $measured n]
set mean [dict get $measured mean]
set arr [list [dict get $measured min] [dict get $measured max]]
set limits [ot_cf_pinreg_limits [dict get $measured groups] $bound $tol]
set strict_groups [expr {([info exists ::env(OT_PINREG_GROUP_GUARD)] && $::env(OT_PINREG_GROUP_GUARD) eq "1") || ([info exists ::env(OT_TAP_GRT_PRE)] && $::env(OT_TAP_GRT_PRE) eq "1")}]
set census [dict create status NOT_RUN n -1 worst_ps -1 tns_ps -1 margin_n -1]
if {$C eq "FF" && [info exists ::env(OT_PINREG_HOLD_CENSUS)] && $::env(OT_PINREG_HOLD_CENSUS) eq "1"} {
  set census [ot_cf_output_hold_census]
  puts "OT_PINREG_HOLD_CENSUS FF $census"
}
puts "OT_PINREG_GROUPS $C strict $strict_groups $limits"
set ws [expr {[sta::worst_slack_cmd max] * 1e12}]
set hs [expr {[sta::worst_slack_cmd min] * 1e12}]
set dev [expr {$n ? abs($mean - $bound) : 1e9}]
set v [expr {$n && $dev <= $tol && (!$strict_groups || [dict get $limits verdict] eq "PASS") ? "PASS" : "FAIL"}]
set tag [expr {[info exists ::env(OT_POSTCTS_TAG)] ? $::env(OT_POSTCTS_TAG) : "postcts_gate"}]
if {![regexp {^[A-Za-z0-9_]+$} $tag]} { error "postcts_gate: unsafe output tag" }
set fh [open /work/${tag}_${c}.json w]
puts $fh [format "{\"corner\": \"%s\", \"pinreg_n\": %d, \"pinreg_mean_ps\": %.2f, \"pinreg_min_ps\": %.2f, \"pinreg_max_ps\": %.2f, \"bound_ps\": %.2f, \"dev_ps\": %.2f, \"tol_ps\": %.1f, \"setup_wns_est_ps\": %.2f, \"hold_wns_est_ps\": %.2f, \"rc\": \"%s\", \"parasitics\": \"%s\", \"verdict\": \"%s\"}" \
  $C $n $mean [expr {$n ? [lindex $arr 0] : -1}] [expr {$n ? [lindex $arr end] : -1}] $bound $dev $tol $ws $hs \
  [expr {[info exists ::env(LAYER_PARASITICS_FILE)] ? $::env(LAYER_PARASITICS_FILE) : "platform setRC.tcl"}] $ot_pg_mode $v]
close $fh
set original [open /work/${tag}_${c}.json r]; set json [read $original]; close $original
set json [string trimright [string trim $json] "}"]
append json [format ", \"group_min_ps\": %.4f, \"group_max_ps\": %.4f, \"group_spread_ps\": %.4f, \"hold_census_status\": \"%s\", \"hold_census_n\": %d, \"hold_census_worst_ps\": %.4f, \"hold_census_tns_ps\": %.4f, \"hold_census_margin_n\": %d}\n" [dict get $limits min] [dict get $limits max] [dict get $limits spread] [dict get $census status] [dict get $census n] [dict get $census worst_ps] [dict get $census tns_ps] [dict get $census margin_n]]
set original [open /work/${tag}_${c}.json w]; puts -nonewline $original $json; close $original
set detail [open /work/${tag}_${c}.groups.tsv w]
puts $detail "group\tmean_ps\tn\tmin_ps\tmax_ps"
dict for {group values} [dict get $measured groups] {
  puts $detail "$group\t[lindex $values 0]\t[lindex $values 1]\t[lindex $values 3]\t[lindex $values 4]"
}
puts $detail "# limits $limits"
puts $detail "# output_hold $census"
close $detail
puts [format "OT_POSTCTS_GATE %s (%s) pinreg n %d mean %.2f bound %.2f dev %.2f tol %.1f setup_est %.2f hold_est %.2f %s" \
  $C $ot_pg_mode $n $mean $bound $dev $tol $ws $hs $v]
