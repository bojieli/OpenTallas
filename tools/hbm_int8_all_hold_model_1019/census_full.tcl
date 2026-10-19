# READ ONLY frozen native DB; no physical mutation or DB export.
set corner $::env(INT8_CORNER)
source /work/kit/libs_${corner}.tcl
read_db /work/output/cts_checkpoint.odb
source $p/setRC.tcl
source /work/kit/constraints.sdc
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set regs [all_registers]
set data {}
foreach pin [all_registers -data_pins] {if {[get_property $pin lib_pin_name] eq "D"} {lappend data $pin}}
puts "ENDPOINT_COUNTS cells=[llength $regs] data=[llength $data]"
if {[llength $regs] != 2782} {error WRONG_REGISTER_COUNT}
set async {}
foreach pin [get_pins -of_objects $regs] {
 if {[get_property $pin lib_pin_name] in {RESETN SETN}} {lappend async $pin}
}
set inv [open /audit/inventory_${corner}.tsv w]
puts $inv "role\tpin\tmaster"
foreach role {data async} {
 foreach pin [set $role] {
  set cell [get_cells -of_objects $pin]
  puts $inv "$role\t[get_full_name $pin]\t[get_property $cell ref_name]"
 }
}
close $inv
set counter 0
foreach role {data async} {
 set endpoints [set $role]
 foreach class {internal rootIO} {
  set sources [expr {$class eq "internal" ? $regs : [all_inputs -no_clocks]}]
  foreach delay {min max} {
   foreach transition {rise fall} {
    # There is <=1 selected path per explicit native endpoint+transition per path group.
    # Group bound equals actual endpoint cardinality, so no endpoint can be truncated.
    set args [list -path_delay $delay -from $sources -${transition}_to $endpoints -group_path_count [llength $endpoints] -endpoint_path_count 1]
    set paths [find_timing_paths {*}$args]
    set label ${corner}_${role}_${class}_${delay}_${transition}
    set fd [open /audit/${label}.tsv w]
    puts $fd "endpoint\tstartpoint\tslack_ps"
    foreach path $paths {
     puts $fd "[get_full_name [get_property $path endpoint]]\t[get_full_name [get_property $path startpoint]]\t[get_property $path slack]"
    }
    close $fd
    sta::redirect_file_begin /audit/${label}.json
    report_checks {*}$args -format json -fields {capacitance slew fanout input_pin net} -digits 9
    sta::redirect_file_end
    puts "CENSUS_CLASS_COMPLETE $label endpoints=[llength $endpoints] actual_paths=[llength $paths]"
    incr counter
   }
  }
 }
}
puts "CENSUS_COMPLETE $corner queries=$counter data=[llength $data] async=[llength $async] NO_DB_WRITE_NO_CTS_NO_REPAIR"
