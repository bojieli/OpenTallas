# postcts_gate.tcl -- FLOW 2026-10-25 post-CTS gate before route (GEOM-REVIEW / GEOM-REVIEW-2 [FLOW] 05:00).
# One corner per run (env OT_CORNER = TT | FF): 4_cts.odb, kit SDC with the vclk bound for THAT corner
# (OT_VCLK_TT / OT_VCLK_FF), placement parasitics on the kit's RC basis (LAYER_PARASITICS_FILE, the RCX-calibrated
# setRC_rcx.tcl by default), propagated clocks.  Pin-register set = the registers the sign-off clock check uses
# (fanout of the data inputs, fanin of the outputs).  Writes /out/placement_only_<corner>.json:
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
# so TT and FF both wrote /out/placement_only_1.62979E-01.json and FF overwrote the TT evidence (VMR vmr_readiness 10-25).
# The corner, its file tag, bound and tol are captured here once and only these ot_pg_* copies are used afterwards.
if {$C ni {TT FF SS}} {error "postcts: OT_CORNER must be TT, FF or SS, got $C"}
set ot_pg_C $C
set ot_pg_c $c
# The exact staged plan may declare the mean insertion band a design target
# (12.3a); missing/malformed measurements remain fatal in either policy.
set ot_pg_band_policy gate
if {[file exists /work/master_slice.json]} {
  set ot_pg_band_policy [exec python3 -c {
import json, sys
s = json.load(open(sys.argv[1]))
p = s.get("core_tree", {}).get("model_qualification", {}).get("band_policy", "gate")
if p not in ("gate", "info"):
    raise ValueError("invalid model_qualification band_policy")
print(p)
} /work/master_slice.json]
}
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
ot_lib_load $ot_pg_C /out/placement_only_${ot_pg_c}.libraries.json
foreach f {
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_TT_nldm_211120.lib.gz
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_TT_nldm_211120.lib.gz
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_TT_nldm_211120.lib.gz
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz
} {if {![file isfile $f]} {error "missing exact official LVT library $f"};read_liberty $f}
read_db $::env(ODB)
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
proc master_pins {m} {set ps {};foreach t [$m getMTerms] {lappend ps "[$t getName]:[$t getIoType]:[$t getSigType]"};return [lsort $ps]}
read_sdc /work/constraint.sdc
set ot_core_tap_fd [open /work/constraint.sdc]
set ot_core_tap_sdc [read $ot_core_tap_fd]; close $ot_core_tap_fd
set ot_core_tap_markers [regexp -all -inline -line {^# OT_CORE_TAP_CORNER_FILE[^\n]*$} $ot_core_tap_sdc]
if {[llength $ot_core_tap_markers]} {
  if {[llength $ot_core_tap_markers] != 1 || [string trim [lindex $ot_core_tap_markers 0]] ne "# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc"} {error "postcts: malformed core-tap FF overlay marker"}
  if {$ot_pg_C eq "FF"} {
    if {![file isfile /work/core_taps_ff.sdc]} {error "postcts: missing marked core_taps_ff.sdc"}
    read_sdc /work/core_taps_ff.sdc
  }
}

set ot_pg_bound [expr {$ot_pg_C eq "FF" ? $::env(OT_VCLK_FF) : $::env(OT_VCLK_TT)}]
set ot_pg_tol [expr {[info exists ::env(OT_POSTCTS_TOL)] ? $::env(OT_POSTCTS_TOL) : 20.0}]
set bound $ot_pg_bound
set tol $ot_pg_tol
# Forwarded/landing clock roots are real clocks too. Select the IO reference by
# its absent source rather than by excluding a single real clock named clk.
set ot_pg_virtual {}
foreach ot_pg_clock [all_clocks] {
  if {![llength [get_property $ot_pg_clock sources]]} {lappend ot_pg_virtual $ot_pg_clock}
}
if {[llength $ot_pg_virtual] != 1} {error "postcts: expected exactly one source-less virtual IO clock"}
set_clock_latency -source $ot_pg_bound $ot_pg_virtual
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
# A saved ODB retains wires/guides, not STA parasitic annotations. Explicit
# frozen-clock consumers must restore the qualified clock-only RC in THIS process.
set ot_pg_frozen_rc [expr {[info exists ::env(OT_POSTCTS_FROZEN_CLOCK_SPEFS)] && $::env(OT_POSTCTS_FROZEN_CLOCK_SPEFS) ne ""}]
if {$ot_pg_frozen_rc} {
  set ot_pg_clock_maps $::env(OT_POSTCTS_FROZEN_CLOCK_SPEFS)
  if {[catch {dict size $ot_pg_clock_maps} ot_pg_size] || $ot_pg_size != 1} {error "postcts: exactly one explicit native parasitic dataset is required"}
  foreach key {OT_POSTCTS_FROZEN_CLOCK_IDENTITY OT_POSTCTS_FROZEN_CLOCK_HELPER OT_POSTCTS_FROZEN_CLOCK_CHECKER OT_POSTCTS_FROZEN_CLOCK_GUARD} {
    if {![info exists ::env($key)] || ![file readable $::env($key)]} {error "postcts: missing frozen-clock input $key"}
  }
  if {![info exists ::env(OT_POSTCTS_GRT)] || !$::env(OT_POSTCTS_GRT)} {error "postcts: frozen clock RC requires native global-route estimation"}
  source $::env(OT_POSTCTS_FROZEN_CLOCK_HELPER)
  source $::env(OT_POSTCTS_FROZEN_CLOCK_GUARD)
  # Current graph is frozen only to protect its existing routed wires in memory;
  # the immutable qualified ORIGINAL dump remains the identity authority below.
  ot_clk_freeze
  estimate_parasitics -global_routing
  ::ot_clock_rc_restore_checked $ot_pg_clock_maps $::env(OT_POSTCTS_FROZEN_CLOCK_IDENTITY) $::env(OT_POSTCTS_FROZEN_CLOCK_CHECKER) /work/postcts_frozen_clock_$ot_pg_c postcts_$ot_pg_c
  set ot_pg_mode global_routing_frozen_clock
} else {
set ot_pg_mode placement
if {[info exists ::env(OT_POSTCTS_GRT)] && $::env(OT_POSTCTS_GRT) && ![catch {estimate_parasitics -global_routing}]} {
  set ot_pg_mode global_routing
} else {
  estimate_parasitics -placement
}
}



set ep {}
foreach p [all_registers -data_pins] {if {[get_full_name $p] eq {u_fcore.core.quant.s1_m[1][28]$_DFF_P_/D}} {lappend ep $p}}
if {[llength $ep]!=1} {error "exact native critical endpoint missing"}
puts "QUERY_RVT_BASELINE"
report_checks -path_delay max -to $ep -group_path_count 1 -digits 3 -fields {slew cap fanout}
set i [[ord::get_db_block] findInst {_071893_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "INVx1_ASAP7_75t_R"} {error "wrong exact DATA driver _071893_"}
set mm [[ord::get_db] findMaster INVx1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */INVx1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell INVx1_ASAP7_75t_L"}
replace_cell [get_cells {_071893_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_118175_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "HAxp5_ASAP7_75t_R"} {error "wrong exact DATA driver _118175_"}
set mm [[ord::get_db] findMaster HAxp5_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster HAxp5_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */HAxp5_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell HAxp5_ASAP7_75t_L"}
replace_cell [get_cells {_118175_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_070742_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OR5x1_ASAP7_75t_R"} {error "wrong exact DATA driver _070742_"}
set mm [[ord::get_db] findMaster OR5x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OR5x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OR5x1_ASAP7_75t_L"}
replace_cell [get_cells {_070742_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_070743_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OR4x1_ASAP7_75t_R"} {error "wrong exact DATA driver _070743_"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OR4x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OR4x1_ASAP7_75t_L"}
replace_cell [get_cells {_070743_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_070746_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OR4x1_ASAP7_75t_R"} {error "wrong exact DATA driver _070746_"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OR4x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OR4x1_ASAP7_75t_L"}
replace_cell [get_cells {_070746_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_070778_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "AO21x1_ASAP7_75t_R"} {error "wrong exact DATA driver _070778_"}
set mm [[ord::get_db] findMaster AO21x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster AO21x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */AO21x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell AO21x1_ASAP7_75t_L"}
replace_cell [get_cells {_070778_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_070779_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OA211x2_ASAP7_75t_R"} {error "wrong exact DATA driver _070779_"}
set mm [[ord::get_db] findMaster OA211x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA211x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA211x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OA211x2_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OA211x2_ASAP7_75t_L"}
replace_cell [get_cells {_070779_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_070785_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OA211x2_ASAP7_75t_R"} {error "wrong exact DATA driver _070785_"}
set mm [[ord::get_db] findMaster OA211x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA211x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA211x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OA211x2_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OA211x2_ASAP7_75t_L"}
replace_cell [get_cells {_070785_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_070788_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OAI21x1_ASAP7_75t_R"} {error "wrong exact DATA driver _070788_"}
set mm [[ord::get_db] findMaster OAI21x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OAI21x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OAI21x1_ASAP7_75t_L"}
replace_cell [get_cells {_070788_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_071990_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "AND2x2_ASAP7_75t_R"} {error "wrong exact DATA driver _071990_"}
set mm [[ord::get_db] findMaster AND2x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */AND2x2_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell AND2x2_ASAP7_75t_L"}
replace_cell [get_cells {_071990_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_071991_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "AOI21x1_ASAP7_75t_R"} {error "wrong exact DATA driver _071991_"}
set mm [[ord::get_db] findMaster AOI21x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */AOI21x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell AOI21x1_ASAP7_75t_L"}
replace_cell [get_cells {_071991_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_119409_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "HAxp5_ASAP7_75t_R"} {error "wrong exact DATA driver _119409_"}
set mm [[ord::get_db] findMaster HAxp5_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster HAxp5_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */HAxp5_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell HAxp5_ASAP7_75t_L"}
replace_cell [get_cells {_119409_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084259_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OR4x1_ASAP7_75t_R"} {error "wrong exact DATA driver _084259_"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OR4x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OR4x1_ASAP7_75t_L"}
replace_cell [get_cells {_084259_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084260_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OR4x1_ASAP7_75t_R"} {error "wrong exact DATA driver _084260_"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OR4x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OR4x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OR4x1_ASAP7_75t_L"}
replace_cell [get_cells {_084260_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084261_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OA21x2_ASAP7_75t_R"} {error "wrong exact DATA driver _084261_"}
set mm [[ord::get_db] findMaster OA21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OA21x2_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OA21x2_ASAP7_75t_L"}
replace_cell [get_cells {_084261_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084262_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OA21x2_ASAP7_75t_R"} {error "wrong exact DATA driver _084262_"}
set mm [[ord::get_db] findMaster OA21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OA21x2_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OA21x2_ASAP7_75t_L"}
replace_cell [get_cells {_084262_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084263_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OA21x2_ASAP7_75t_R"} {error "wrong exact DATA driver _084263_"}
set mm [[ord::get_db] findMaster OA21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OA21x2_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OA21x2_ASAP7_75t_L"}
replace_cell [get_cells {_084263_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084264_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OR3x1_ASAP7_75t_R"} {error "wrong exact DATA driver _084264_"}
set mm [[ord::get_db] findMaster OR3x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OR3x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OR3x1_ASAP7_75t_L"}
replace_cell [get_cells {_084264_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084265_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "OA211x2_ASAP7_75t_R"} {error "wrong exact DATA driver _084265_"}
set mm [[ord::get_db] findMaster OA211x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA211x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster OA211x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */OA211x2_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell OA211x2_ASAP7_75t_L"}
replace_cell [get_cells {_084265_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084267_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "AO31x2_ASAP7_75t_R"} {error "wrong exact DATA driver _084267_"}
set mm [[ord::get_db] findMaster AO31x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */AO31x2_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell AO31x2_ASAP7_75t_L"}
replace_cell [get_cells {_084267_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084280_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "AO21x2_ASAP7_75t_R"} {error "wrong exact DATA driver _084280_"}
set mm [[ord::get_db] findMaster AO21x2_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */AO21x2_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell AO21x2_ASAP7_75t_L"}
replace_cell [get_cells {_084280_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {place8811}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "BUFx6f_ASAP7_75t_R"} {error "wrong exact DATA driver place8811"}
set mm [[ord::get_db] findMaster BUFx6f_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */BUFx6f_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell BUFx6f_ASAP7_75t_L"}
replace_cell [get_cells {place8811}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084286_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "AOI211x1_ASAP7_75t_R"} {error "wrong exact DATA driver _084286_"}
set mm [[ord::get_db] findMaster AOI211x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */AOI211x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell AOI211x1_ASAP7_75t_L"}
replace_cell [get_cells {_084286_}] [lindex $c 0]
set i [[ord::get_db_block] findInst {_084287_}]; if {$i eq "NULL" || [[$i getMaster] getName] ne "AO21x1_ASAP7_75t_R"} {error "wrong exact DATA driver _084287_"}
set mm [[ord::get_db] findMaster AO21x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set mm [[ord::get_db] findMaster AO21x1_ASAP7_75t_L]
if {$mm eq "NULL"} {error "genuine LVT physical master absent"}
set oldm [$i getMaster]
if {[$mm getWidth]!=[$oldm getWidth] || [$mm getHeight]!=[$oldm getHeight] || [master_pins $mm] ne [master_pins $oldm]} {error "LVT footprint or pin function interface differs"}
set c [get_lib_cells */AO21x1_ASAP7_75t_L]; if {[llength $c]!=1} {error "missing unique genuine LVT cell AO21x1_ASAP7_75t_L"}
replace_cell [get_cells {_084287_}] [lindex $c 0]
puts "QUERY_LVT_DATA24_MEASURED"
report_checks -path_delay max -to $ep -group_path_count 1 -digits 3 -fields {slew cap fanout}
exit
