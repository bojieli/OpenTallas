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
# NOMCAP-1118 (OWNER r708): nominal input-pin load on clock buffer/inverter cells and sequential CLK pins.  A container
# that mounts the repo copies (tools/die_plan/nomcap_libs, MANIFEST.json) names them in OT_NOMCAP_DIR; the stock ORFS
# INVBUF/SEQ RVT libraries a kit config selects are then replaced by the copy of the same base name (SEQ gains .gz).
# OT_NOMCAP=0 keeps the stock libraries.  Kits generated with the switch on already name /work/nomcap in config.mk.
proc ot_lib_nomcap {files} {
  if {![info exists ::env(OT_NOMCAP_DIR)] || $::env(OT_NOMCAP_DIR) eq ""} {return $files}
  if {[info exists ::env(OT_NOMCAP)] && [string tolower $::env(OT_NOMCAP)] in {0 off no false}} {return $files}
  set out {}; set n 0
  foreach f $files {
    set t [file tail $f]
    if {[string match /OpenROAD-flow-scripts/* $f] && [regexp {^asap7sc7p5t_(INVBUF|SEQ)_RVT_(TT|FF|SS)_nldm_[0-9]+\.lib(\.gz)?$} $t]} {
      set c [file join $::env(OT_NOMCAP_DIR) [expr {[string match *.gz $t] ? $t : "$t.gz"}]]
      if {![file isfile $c]} {error "OT_NOMCAP: $c missing (OT_NOMCAP_DIR mounted without the r708 copies)"}
      lappend out $c; incr n
    } else {lappend out $f}
  }
  puts "OT_NOMCAP r708 replaced $n stock INVBUF/SEQ libraries from $::env(OT_NOMCAP_DIR)"
  return $out
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
  set files [ot_lib_nomcap [regexp -all -inline {\S+} [lindex $records 0]]]
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
