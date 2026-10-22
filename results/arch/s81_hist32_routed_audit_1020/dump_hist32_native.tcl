source /audit/physical/common_flow/native_pg_binding.tcl
set odbs [glob /job/routes/*/work/orfs/results/asap7/*/base/6_final.odb]
if {[llength $odbs] != 1} {error "ambiguous final ODB"}
read_db [lindex $odbs 0]
set block [ord::get_db_block]
set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
set f [open /audit/native_endpoint_dump.json {WRONLY CREAT EXCL}]
puts $f "\{\"schema\":\"opentallas.readonly_native_endpoints.v1\",\"dbu\":$dbu,\"nets\":\["
set comma ""
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} continue
  puts -nonewline $f "$comma\{\"name\":[ot_pg_json_string [$net getName]],\"sig_type\":[ot_pg_json_string [$net getSigType]],\"iterms\":\["
  set c ""
  foreach it [$net getITerms] {
    set xy [$it getAvgXY]
    if {[llength $xy] != 3 || ![lindex $xy 0]} {error "missing actual ITerm coordinates [$it getName]"}
    set inst [$it getInst]
    puts -nonewline $f "$c\{\"inst\":[ot_pg_json_string [$inst getName]],\"master\":[ot_pg_json_string [[$inst getMaster] getName]],\"pin\":[ot_pg_json_string [[$it getMTerm] getName]],\"io\":[ot_pg_json_string [$it getIoType]],\"x\":[expr {[lindex $xy 1]/$dbu}],\"y\":[expr {[lindex $xy 2]/$dbu}]\}"
    set c ,
  }
  puts -nonewline $f "\],\"bterms\":\["
  set c ""
  foreach bt [$net getBTerms] {
    set boxes {}
    foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend boxes $box}}
    if {![llength $boxes]} {error "missing BTerm geometry [$bt getName]"}
    set box [lindex $boxes 0]
    puts -nonewline $f "$c\{\"pin\":[ot_pg_json_string [$bt getName]],\"io\":[ot_pg_json_string [$bt getIoType]],\"x\":[expr {([$box xMin]+[$box xMax])/2.0/$dbu}],\"y\":[expr {([$box yMin]+[$box yMax])/2.0/$dbu}]\}"
    set c ,
  }
  puts -nonewline $f "\]\}"
  set comma ,
}
puts $f "\]\}"
close $f
set g [open /audit/pg_grid.json {WRONLY CREAT EXCL}]
puts $g "\{\"schema\":\"opentallas.all_native_pg_grid.v1\",\"nets\":\["
set c ""; set failures 0; set checked 0
foreach net [$block getNets] {
  if {[$net getSigType] ni {POWER GROUND}} continue
  set name [$net getName]
  set rc [catch {check_power_grid -net $name -error_file /audit/pg_grid_${checked}.rpt} result]
  puts -nonewline $g "$c\{\"name\":[ot_pg_json_string $name],\"role\":[ot_pg_json_string [$net getSigType]],\"rc\":$rc,\"result\":[ot_pg_json_string $result]\}"
  set c ,; incr checked; if {$rc} {incr failures}
}
puts $g "\],\"checked\":$checked,\"failures\":$failures\}"
close $g
if {!$checked || $failures} {error "all-PG-grid audit failed checked=$checked failures=$failures"}
puts "READONLY_NATIVE_ENDPOINTS_AND_PG_GRID_PASS"
exit
