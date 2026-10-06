# Run in the retained ORFS design environment, after the matching mapped
# database and SDC have been loaded. This report does not change the database,
# constraints, regions, clocks, or parasitics. Use the actual WC/BC libraries.
# FHCUT_REPORT_DIR names a new output directory; existing evidence is retained.
if {![info exists ::env(FHCUT_REPORT_DIR)]} {error "Set FHCUT_REPORT_DIR"}
set out $::env(FHCUT_REPORT_DIR)
if {[file exists $out]} {error "Refusing to overwrite cut reports: $out"}
file mkdir $out
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set cells [open "$out/cells.tsv" w]
puts $cells "instance\tmaster\tarea_um2\tgroup\tclass"
set pins [open "$out/pins.tsv" w]
puts $pins "instance\tmaster_pin\tdirection\tsignal_type\tnet"
set groups [dict create]
set nets [dict create]
set macros 0
foreach inst [$block getInsts] {
    set name [$inst getName]
    set clean [string map [list "\\" ""] $name]
    set master [$inst getMaster]
    set mn [$master getName]
    set class ""
    if {$mn eq "ot_sram_1r1w_512x128_m4_r2c2"} {
        incr macros
        set class macro
    } elseif {[string first "g_actual_native_load" $clean]>=0} {
        set class native_capture
    } elseif {[string first "g_retirement" $clean]>=0} {
        set class retire
        foreach tag {row_fault quadrant_fault g_relay g_lane g_write u_status packet_pipe valid_pipe} {
            if {[string first $tag $clean]>=0} {set class $tag;break}
        }
    } elseif {[string first "g_argmax_consumer" $clean]>=0} {
        set class argmax_receiver
    } else {continue}
    set group [$inst getGroup]
    set gn ""
    if {$group ne "NULL"} {set gn [$group getName]}
    set area [expr {double([$master getWidth])*[$master getHeight]/($dbu*$dbu)}]
    puts $cells "$name\t$mn\t$area\t$gn\t$class"
    foreach it [$inst getITerms] {
        set mt [$it getMTerm]
        set net [$it getNet]
        set nn ""
        if {$net ne "NULL"} {set nn [$net getName]}
        puts $pins "$name\t[$mt getName]\t[$mt getIoType]\t[$mt getSigType]\t$nn"
        # Preserve the actual pin spelling and master. The STA report supplies
        # Liberty receiver capacitances and wire estimates/extracted loads;
        # no library sample or zero observation load is substituted here.
        if {[$mt getIoType] eq "OUTPUT" &&
            $class in {row_fault quadrant_fault g_relay g_lane g_write u_status}} {
            set sp [get_pins -quiet "$name/[$mt getName]"]
            if {[llength $sp]} {dict lappend groups $class {*}$sp}
            if {$nn ne ""} {dict set nets $nn 1}
        }
        if {$class eq "macro" && [$mt getSigType] eq "CLOCK" && $nn ne ""} {
            dict set nets $nn 1
        }
    }
}
close $cells
close $pins
if {$macros!=64} {error "Expected all64 real head SRAMs, found $macros"}
# Include the literal endpoint/ACK/accept nets even when ABC has renamed or
# flattened their drivers; all endpoints are separately retained in pins.tsv.
foreach net [$block getNets] {
    set name [$net getName]
    if {[regexp {native_ack|native_request_ready|native_reply_capture|native_reply_v|commit_busy|retire_warm_ack} $name]} {
        dict set nets $name 1
    }
}
foreach name [lsort [dict keys $nets]] {report_net -digits 6 $name >> "$out/net_loads.rpt"}
report_clock_properties > "$out/clocks.rpt"
report_check_types -max_slew -max_capacitance -max_fanout -violators > "$out/electrical.rpt"
dict for {class through} $groups {
    report_checks -through $through -path_delay max -group_path_count 32 \
        -format full_clock_expanded -fields {slew capacitance input_pin net fanout} \
        -digits 6 > "$out/${class}_setup.rpt"
    report_checks -through $through -path_delay min -group_path_count 32 \
        -format full_clock_expanded -fields {slew capacitance input_pin net fanout} \
        -digits 6 > "$out/${class}_hold.rpt"
}
report_checks -path_delay max -group_path_count 64 -format full_clock_expanded \
    -fields {slew capacitance input_pin net fanout} -digits 6 > "$out/setup.rpt"
report_checks -path_delay min -group_path_count 64 -format full_clock_expanded \
    -fields {slew capacitance input_pin net fanout} -digits 6 > "$out/hold.rpt"
puts "FH_LOADED_CUT reports=$out macros=$macros conditional_child_scope=1"
