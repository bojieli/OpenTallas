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
    if {[regexp {^export\s+(OT_VCLK_TT|OT_VCLK_FF|LAYER_PARASITICS_FILE)\s*\??=\s*(\S+)} $ln -> k v] && ![info exists ::env($k)]} {
      set ::env($k) $v
    }
  }
  close $fh
}
set c [string tolower $C]
# Private gate state (PATH-QC 2026-10-25): every external file sourced below (LAYER_PARASITICS_FILE, clock_family.tcl,
# pinreg_measure.tcl, SDC) runs at global scope.  A kit RC wrapper's `foreach {l r c}` layer loop left c = 1.62979E-01,
# so TT and FF both wrote /work/postcts_gate_1.62979E-01.json and FF overwrote the TT evidence (VMR vmr_readiness 10-25).
# The corner, its file tag, bound and tol are captured here once and only these ot_pg_* copies are used afterwards.
if {$C ni {TT FF SS}} {error "postcts: OT_CORNER must be TT, FF or SS, got $C"}
set ot_pg_C $C
set ot_pg_c $c
# The exact staged plan may declare the mean insertion band a design target
# (12.3a); missing/malformed measurements remain fatal in either policy.
set ot_pg_band_policy [exec python3 -c {
import sys
sys.path.insert(0, "/work")
import core_clock_band
print(core_clock_band.band_policy("/work"))
}]
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
ot_lib_load $ot_pg_C /work/postcts_gate_${ot_pg_c}.libraries.json

# ROOT authorized diagnostic only: existing saved PG0 CTS; no repair/new cells.
source /out/tools/native_pg_binding.tcl
proc route_guard {b} {
  set instances {};set nets {};set data {};set terms {}
  foreach i [$b getInsts] {
    lappend instances [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]
    foreach t [$i getITerms] {
      if {[[$t getMTerm] getSigType] in {POWER GROUND}} continue
      set n [$t getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]}
      lappend data [list [$i getName] [[$t getMTerm] getName] $nn]
    }
  }
  foreach n [$b getNets] {
    lappend nets [list [$n getName] [$n getSigType] [$n isSpecial] [$n isDoNotTouch] [$n getNonDefaultRule]]
  }
  foreach t [$b getBTerms] {
    set n [$t getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]}
    set pins {};foreach p [$t getBPins] {
      set boxes {};foreach box [$p getBoxes] {lappend boxes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}
      lappend pins [list [$p getPlacementStatus] [lsort $boxes]]
    }
    lappend terms [list [$t getName] [$t getSigType] [$t getIoType] $nn [lsort $pins]]
  }
  return [dict create instances [lsort $instances] net_flags [lsort $nets] data_clock_connectivity [lsort $data] bterm_geometry [lsort $terms]]
}
read_db $::env(ODB)
set route_block [ord::get_db_block]
set route_before [route_guard $route_block]
set f [open /out/before_guard.tcl {WRONLY CREAT EXCL}];puts $f $route_before;close $f
ot_pg_audit_snapshot $route_block /out/before_pg.json
ot_pg_assert_all_native $route_block [ot_pg_prepare $route_block]
read_sdc /work/run/results/asap7/hbc_ot_hnx_fused_tnode/base/4_cts.sdc
foreach c [all_clocks] {if {[llength [get_property $c sources]]} {set_propagated_clock $c}}
# Fail on any accidental cell-creating recipe call; stock global routing creates routes only.
foreach command {buffer_ports repair_clock_inverters clock_tree_synthesis repair_timing repair_design global_placement detailed_placement repair_antennas repair_tie_fanout} {
 if {[info commands $command] ne ""} {rename $command routeonly_forbidden_$command;proc ::$command {args} {error "ROUTE_ONLY_NO_CELL_BIRTH"}}
}
set nc 0;set ns 0;set special_clock 0
foreach n [$route_block getNets] {
 if {[$n getSigType] eq "CLOCK"} {incr nc;if {[$n isSpecial]} {incr special_clock}}
 if {[$n getSigType] eq "SIGNAL"} {incr ns}
}
if {$nc==0 || $special_clock!=0} {error "ROUTE_ONLY_FULL_CLOCKS_REQUIRED clocks=$nc special=$special_clock"}
puts "ROUTE_ONLY_FULL_NATIVE clocks=$nc signals=$ns layers=M2-M5 adjustment=0.25 iterations=50 repair=NONE"
source /work/setRC_rcx.tcl
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment M2-M5 0.25
pin_access
global_route -congestion_iterations 50 -congestion_report_file /out/cong.rpt -allow_congestion -resistance_aware -verbose
set route_after [route_guard $route_block]
set f [open /out/after_guard.tcl {WRONLY CREAT EXCL}];puts $f $route_after;close $f
if {$route_before ne $route_after} {error "ROUTE_ONLY_TOPOLOGY_POSE_MASTER_STATUS_FLAGS_MUTATION"}
ot_pg_audit_snapshot $route_block /out/after_pg.json
ot_pg_assert_all_native $route_block [ot_pg_prepare $route_block]
write_db /work/route_only.odb
puts "ROUTE_ONLY_SAVED_FULL_CLOCK_SIGNAL NO_NEW_CELLS DATA_CLOCK_POSES_MASTERS_STATUS_UNCHANGED PG0"
