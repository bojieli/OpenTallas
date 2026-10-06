# Loaded, linked full-engine parent only. No clock creation or IO substitution.
# Source the parent's real SDC and extracted parasitics before calling report.
source [file join [file dirname [info script]] .. dsrom_field_spine field_boundary_clock.tcl]
namespace eval ot_qx10_parent {}

proc ot_qx10_parent::report {binding corner prefix} {
    if {$corner ni {SS FF}} {error "QX10 boundary requires SS / FF"}
    foreach key {root_port root_clock gated_clock gate_input gate_output gate_enable
                 macro_cells engine_clock_anchors xs_capture go_launch_families
                 source_commit source_sha256 boundaries clock_anchors
                 gate_enable_launch reset_boundary} {
        if {![dict exists $binding $key]} {error "QX10 boundary missing $key"}
    }
    if {[dict get $binding source_commit] ne "0032b735573af2d24416eee1cf5911c0ac99ff5d" ||
        [dict get $binding source_sha256] ne "88e58e80d79dece71346b3123174d0ae0188b6590de88938575877b2209fc3b6"} {
        error "QX10 boundary is not the selected Z18 engine source"
    }
    # Fail on the register projection before attempting any timing reports.
    set macros [dict get $binding macro_cells]
    if {[llength $macros] != 4 || [llength [lsort -unique $macros]] != 4} {
        error "QX10 boundary needs four distinct real weight ROMs in the linked parent"
    }
    foreach name $macros {
        set cell [get_cells -quiet $name]
        if {[llength $cell] != 1 || [get_full_name $cell] ne $name ||
            [get_property $cell ref_name] ne "ot_rom_4096x274_m8"} {
            error "QX10 full engine absent: $name"
        }
    }
    if {[dict get $binding root_port] ne "clk"} {error "QX10 native parent source is clk"}
    set root [ot_v9_field::one port [dict get $binding root_port]]
    set rn [dict get $binding root_clock]
    set gn [dict get $binding gated_clock]
    if {$rn eq $gn} {error "QX10 root and gated clocks cannot alias"}
    foreach name [list $rn $gn] {
        set c [get_clocks -quiet $name]
        if {[llength $c] != 1 || abs([get_property $c period] - 833.333333333333) > 0.001} {
            error "QX10 actual streaming clock missing or changed: $name"
        }
    }
    set gi [ot_v9_field::one pin [dict get $binding gate_input]]
    set gp [ot_v9_field::one pin [dict get $binding gate_output]]
    set ge [ot_v9_field::one pin [dict get $binding gate_enable]]
    set gate [get_cells -of_objects $gi]
    if {[llength $gate] != 1 || [get_cells -of_objects $gp] ne $gate ||
        [get_cells -of_objects $ge] ne $gate ||
        [get_property $gate ref_name] ne "ICGx1_ASAP7_75t_R"} {
        error "QX10 actual source ICG is absent"
    }
    foreach {pin suffix} [list $gi /CLK $gp /GCLK $ge /ENA] {
        if {![string match *$suffix [get_full_name $pin]]} {error "QX10 wrong ICG terminal"}
    }
    if {[get_property [get_clocks $rn] sources] ne $root ||
        [get_property [get_clocks $gn] sources] ne $gp} {
        error "QX10 clocks do not originate at the actual parent clk and ICG GCLK"
    }
    foreach name $macros {
        set mp [ot_v9_field::one pin "${name}/clk"]
        if {[get_clocks -of_objects $mp] ne [get_clocks $gn]} {
            error "QX10 real ROM clock lacks actual ICG source: $name"
        }
    }
    # Literal internal register clocks distinguish a complete engine from a
    # projected g_qb/g_mz boundary. Both logical banks must be represented.
    set gated_pins [all_registers -clock $gn -clock_pins]
    set free_pins [all_registers -clock $rn -clock_pins]
    foreach bank {0 1} {
        foreach family {lane chain tree reset} {
            set key "bank${bank}_${family}"
            if {![dict exists $binding engine_clock_anchors $key]} {error "QX10 missing $key anchor"}
            set name [dict get $binding engine_clock_anchors $key]
            set scope [dict get {lane g_l3 chain g_ch3 tree g_tr5 reset g_mz} $family]
            if {[string first "g_mac\[$bank\].${scope}." $name] < 0} {
                error "QX10 $key is not a literal selected-engine internal anchor"
            }
            set p [ot_v9_field::one pin $name]
            set expected $gated_pins
            if {$family eq "reset"} {set expected $free_pins}
            if {[lsearch -exact $expected $p] < 0} {error "QX10 $key not on its actual source clock"}
        }
    }
    set xs [ot_v9_field::pins [dict get $binding xs_capture] {/D$}]
    set gated_data [all_registers -clock $gn -data_pins]
    foreach p $xs {
        if {[lsearch -exact $gated_data $p] < 0} {error "QX10 XS capture is not gated (source lines 257/260)"}
    }
    if {[lsort [dict get $binding xs_capture]] ne [lsort [dict get $binding boundaries activation capture]]} {
        error "QX10 XS binding must cover the complete activation capture boundary"
    }
    set clocks [get_clocks [list $rn $gn]]
    set_clock_uncertainty -setup 60 $clocks
    set_clock_uncertainty -hold 25 $clocks
    set_clock_gating_check -setup 60 -hold 25 $gate
    set_propagated_clock $clocks
    set free_q [all_registers -clock $rn -output_pins]
    set go_d [ot_v9_field::pins [dict get $binding boundaries go capture] {/D$}]
    foreach family {loader broadcast} {
        if {![dict exists $binding go_launch_families $family]} {error "QX10 missing $family go launch"}
        set q [ot_v9_field::pins [dict get $binding go_launch_families $family] {/(Q|QN)$}]
        foreach p $q {
            if {[lsearch -exact $free_q $p] < 0} {error "QX10 $family go launch lacks actual parent clock"}
        }
        foreach delay {min max} {
            if {![llength [find_timing_paths -from $q -to $go_d -path_delay $delay -group_count 1]]} {
                error "QX10 missing $family go $delay path"
            }
            report_checks -from $q -to $go_d -path_delay $delay -group_count 10 \
                -format full_clock_expanded -fields {slew capacitance input_pin net} > ${prefix}.go_${family}.${delay}.rpt
        }
    }
    ot_v9_field::report $binding $prefix
    # Include all internal classes, not only the handoff's current worst path.
    report_checks -path_delay min_max -group_count 100 -format full_clock_expanded \
        -fields {slew capacitance input_pin net} > ${prefix}.all_classes.rpt
}
