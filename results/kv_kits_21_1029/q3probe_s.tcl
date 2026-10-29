
proc so {k args} { puts "SO $k [join $args { }]" }
proc so_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f [sta::time_sta_ui $t]] }
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

ot_lib_load FF /out/libraries.json
read_db /base/5_1_grt.odb
# FLOW 10-26 PG: every POWER/GROUND MTerm of every instance master bound to a net of that type in the signed ODB
# (global_connect skips dont_touch cells: s8b ot_ms_* spine buffers had VDD/VSS open in 6_final.odb).
set so_pg_terms 0; set so_pg_open 0; set so_pg_first "-"
foreach so_i [[ord::get_db_block] getInsts] {
  foreach so_mt [[$so_i getMaster] getMTerms] {
    set so_r [$so_mt getSigType]
    if {$so_r ni {POWER GROUND}} continue
    incr so_pg_terms
    set so_t [$so_i findITerm [$so_mt getName]]
    set so_n NULL
    if {$so_t ne "NULL" && $so_t ne ""} { set so_n [$so_t getNet] }
    if {$so_n eq "NULL" || $so_n eq "" || [$so_n getSigType] ne $so_r} {
      incr so_pg_open
      if {$so_pg_first eq "-"} { set so_pg_first "[$so_i getName]/[$so_mt getName]" }
    }
  }
}
so PG $so_pg_terms $so_pg_open $so_pg_first
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
read_sdc /sdc/golden.sdc
set_propagated_clock [get_clocks clk]
set_clock_latency -source 202.5 [get_clocks vclk]
report_checks -path_delay min -through [get_pins {u_ref.u_leaf.u_a.u_k.rs_d[855]$_DFF_P_/D}] -format full_clock_expanded -digits 2
report_checks -path_delay min -to [get_pins {u_ref.u_leaf.u_c.u.u_r0/q$_DFF_PN0_/RESETN}] -format full_clock_expanded -digits 2
report_worst_slack -min
