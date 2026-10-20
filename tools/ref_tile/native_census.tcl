# Mandatory gate admission, immediately after load_design of the mapped
# synthesis ODB and BEFORE initialize_floorplan or any placement command.
set native_libs {}
if {[info exists ::env(CORNERS)] && $::env(CORNERS) ne ""} {
  foreach c $::env(CORNERS) {
    set key [string toupper $c]_LIB_FILES
    if {![info exists ::env($key)]} {error "PRE_GATE_NATIVE_CENSUS missing $key"}
    lappend native_libs {*}$::env($key)
  }
} elseif {[info exists ::env(LIB_FILES)]} {
  lappend native_libs {*}$::env(LIB_FILES)
}
if {[info exists ::env(AUTO_MEMORIES)] && $::env(AUTO_MEMORIES) eq "1"} {
  foreach p [glob -nocomplain $::env(RESULTS_DIR)/memories/*.lib] {
    if {![string match *_pre_layout.lib $p]} {lappend native_libs $p}
  }
}
set native_cmd [list python3 /src/tools/ref_tile/native_census.py \
  --netlist $::env(RESULTS_DIR)/1_2_yosys.v --top $::env(DESIGN_NAME) \
  --out /work/native_census.json]
foreach p [lsort -unique $native_libs] {lappend native_cmd --liberty $p}
set native_rc [catch {exec {*}$native_cmd 2>@1} native_message]
puts $native_message
if {[file exists /work/native_census.json]} {
  set f [open /work/native_census.json]; set text [read $f]; close $f
  puts "GATE_NATIVE_CENSUS_RESULT [string map [list \n "" \r ""] $text]"
}
if {$native_rc} {error "PRE_GATE_NATIVE_CENSUS_REFUSED: inspect native_census.json"}
