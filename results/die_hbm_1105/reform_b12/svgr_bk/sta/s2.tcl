
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
  # KW-FIX-5 11-04: K/.busfit/<lib> = this lib plus the LEF pins the module does not have (no arcs); all_registers segfaults
  # without them.  The receipt above and every view hash stay on the kit lib.
  foreach f $files {
    set g [file join [file dirname [file dirname $f]] .busfit [file tail $f]]
    set use $f
    if {[file exists $g]} {
      # only a fit made from exactly this kit lib; a stale one would read old timing arcs under this lib's receipt
      set c [open $g]; gets $c h; close $c
      if {[string first [lindex [exec sha256sum -- $f] 0] $h] >= 0} {set use $g}
    }
    read_liberty $use
  }
  set fp [open $receipt w]
  puts $fp "{\"status\":\"LOADED\",\"corner\":[ot_lib_json_string $corner],\"source\":\"ORFS make print corner LIB_FILES\",\"config\":[ot_lib_json_string $config],\"config_sha256\":[ot_lib_json_string $digest],\"libraries\":\[[join $rows ,]\]}"
  close $fp
  puts "OT_TIMING_LIBS $corner exact_count [llength $files] receipt $receipt"
  return $files
}

ot_lib_load TT /out/libraries.json
read_db /base/6_final.odb
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
read_spef /base/6_final.spef
read_sdc /sdc/golden.sdc

# ---- OWNER 12.24b/c sign-off clock uncertainty (in-session over the golden SDC: a re-sign of a 60 / 25 kit SDC is
# timed at the policy too).  Each overridden kind on every clock and every clock pair; real <-> virtual seam pairs split half / half (counted
# once per seam, gen_phys.UNC_SPLIT).  Nothing else in the golden SDC changes. ----
proc so_unc_apply {kind v split} {
  set virt {}
  foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend virt [get_full_name $c] } }
  set_clock_uncertainty $v -$kind [all_clocks]
  foreach a [all_clocks] {
    foreach b [all_clocks] {
      set seam [expr {([get_full_name $a] in $virt) != ([get_full_name $b] in $virt)}]
      set w [expr {$seam ? ([get_full_name $a] in $virt ? $split : 1.0 - $split) * $v : $v}]
      if {[catch {set_clock_uncertainty -from $a -to $b -$kind $w} msg]} { incr ::so_unc_err; set ::so_unc_msg $msg }
    }
  }
}
set ::so_unc_err 0; set ::so_unc_msg -
if {[catch {so_unc_apply setup 0 0.5} msg]} { incr ::so_unc_err; set ::so_unc_msg $msg }
so UNC_POLICY nominal setup 0 hold 25 kinds setup errors $::so_unc_err
set_propagated_clock [all_clocks]
so CORNER TT
so PARASITICS spef
so DESIGN [current_design]
so CELLS [llength [get_cells *]]
# Inventory actual sequential endpoint masters; a Liberty loaded but unused is
# not evidence of an unexpanded child. Keep the raw pair census unchanged.
set so_endpoint_masters {}; set so_endpoint_mapping_errors 0
foreach p [all_registers -clock_pins] {
  if {[catch {
    set owners [get_cells -quiet -of_objects [list $p]]
    if {[llength $owners] != 1} {error "nonunique clock endpoint owner"}
    set master [get_property [lindex $owners 0] ref_name]
    if {$master eq ""} {error "empty clock endpoint master"}
  }]} {incr so_endpoint_mapping_errors; continue}
  dict set so_endpoint_masters $master 1
}
so CLOCK_ENDPOINT_MASTERS {*}[lsort [dict keys $so_endpoint_masters]]
so CLOCK_ENDPOINT_MAPPING_ERRORS $so_endpoint_mapping_errors
# ---- ports (for sdc_lint context) and IO virtual clock ----
set so_ck_ports {}
foreach c [all_clocks] { foreach s [get_property $c sources] { if {[llength [get_ports -quiet [get_full_name $s]]]} { lappend so_ck_ports [get_full_name $s] } } }
set so_ck_ports [lsort -unique $so_ck_ports]
so CLOCK_PORTS {*}$so_ck_ports
set so_din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $so_ck_ports} { lappend so_din $p } }
so INPUTS {*}[lsort -unique [lmap p $so_din {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
so OUTPUTS {*}[lsort -unique [lmap p [all_outputs] {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
set so_vclk {}
foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend so_vclk $c } }
so CLOCKS {*}[lmap c [all_clocks] {get_full_name $c}]
so VCLKS {*}[lmap c $so_vclk {get_full_name $c}]
foreach c [all_clocks] { so PERIOD [get_full_name $c] [get_property $c period] }
# ---- timing with the block's own SDC ----
proc so_timing {tag} {
  so ${tag}_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
  so ${tag}_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
  so ${tag}_TNS_MAX [so_ps [sta::total_negative_slack_cmd max]]
  so ${tag}_TNS_MIN [so_ps [sta::total_negative_slack_cmd min]]
  so ${tag}_NVIOL_MAX [sta::endpoint_violation_count max]
  so ${tag}_NVIOL_MIN [sta::endpoint_violation_count min]
}
so_timing SDC
puts "P2 packet->packet"
report_checks -path_delay max -from [get_pins -hier -filter "full_name=~u_fcore.u?1?.u_bank.packet?273?*/QN"] -to [get_pins -hier -filter "full_name=~u_fcore.u?1?.u_bank.packet?149?*/D"] -fields {slew cap fanout} -digits 1
puts "P2 rgray"
report_checks -path_delay max -to [get_pins -hier -filter "full_name=~*u_response.rgray*/D"] -fields {slew cap fanout} -digits 1
puts "P2 received"
report_checks -path_delay max -to [get_pins -hier -filter "full_name=~*received_q*/D"] -fields {slew cap fanout} -digits 1
puts "P2 hbmrst"
report_checks -path_delay max -to [get_pins -hier -filter "full_name=~*u_response.mem*/D"] -fields {slew cap fanout} -digits 1
exit
