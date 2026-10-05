# Enclosing v9 field boundary, not the spine-only screen SDC.
# Caller supplies literal pins from the selected linked parent. No pattern
# defaults: the screen cannot satisfy u_f, VM, or QX bindings.
# Times are ps. Load the corner's real ROM and standard-cell libraries first.
namespace eval ot_v9_field {}

proc ot_v9_field::one {kind name} {
    if {$kind eq "port"} {set objects [get_ports -quiet $name]} else {
        set objects [get_pins -quiet $name]
    }
    if {[llength $objects] != 1} {error "v9 field: missing/ambiguous $kind $name"}
    if {[get_full_name $objects] ne $name} {error "v9 field: binding must be literal: $name"}
    return $objects
}

proc ot_v9_field::pins {names suffix} {
    if {![llength $names]} {error "v9 field: empty $suffix boundary"}
    set objects {}
    foreach name $names {
        if {![regexp $suffix $name]} {error "v9 field: wrong pin role: $name"}
        lappend objects [ot_v9_field::one pin $name]
    }
    return $objects
}

proc ot_v9_field::constrain {binding corner} {
    if {$corner ni {SS FF}} {error "v9 field requires SS setup / FF hold libraries"}
    foreach key {root_port root_clock clock_anchors gate_input gate_output gate_enable
                 gated_clock boundaries macro_cells source_commit gate_enable_launch} {
        if {![dict exists $binding $key]} {error "v9 field: missing $key"}
    }
    # This binds the actual streaming input of the selected enclosing parent.
    # A serial-chain port must have its own 0.9 GHz contract; it is not rebound.
    if {[dict get $binding root_port] ne "clk"} {error "v9 source parent input is clk"}
    set_units -time ps -capacitance fF
    set root [ot_v9_field::one port [dict get $binding root_port]]
    set name [dict get $binding root_clock]
    if {[llength [get_clocks -quiet $name]]} {
        set c [get_clocks $name]
        if {abs([get_property $c period] - 833.333333333333) > 0.001} {
            error "v9 field: existing streaming period differs; refusing to replace it"
        }
        if {[get_property $c sources] ne $root} {error "v9 field: existing clock has another source"}
    } else {create_clock -name $name -period 833.333333333333 $root}

    foreach role {spine field vm} {
        if {![dict exists $binding clock_anchors $role]} {error "v9 field: missing $role clock anchor"}
        ot_v9_field::one pin [dict get $binding clock_anchors $role]
    }
    set gi [ot_v9_field::one pin [dict get $binding gate_input]]
    set go [ot_v9_field::one pin [dict get $binding gate_output]]
    set ge [ot_v9_field::one pin [dict get $binding gate_enable]]
    set cell [get_cells -of_objects $gi]
    if {[llength $cell] != 1 || [get_cells -of_objects $go] ne $cell ||
        [get_cells -of_objects $ge] ne $cell ||
        [get_property $cell ref_name] ne "ICGx1_ASAP7_75t_R"} {
        error "v9 field: gate must be the actual ot_hdc_cg ICG, CLK/GCLK/ENA"
    }
    foreach {object suffix} [list $gi /CLK $go /GCLK $ge /ENA] {
        if {![string match *$suffix [get_full_name $object]]} {error "v9 field: wrong ICG pin"}
    }
    set gn [dict get $binding gated_clock]
    if {[llength [get_clocks -quiet $gn]]} {error "v9 field: gated clock already declared; inspect its source before rebinding"}
    # Latch-low ICG: passed root edges, no divider and no independent phase.
    create_generated_clock -name $gn -master_clock $name -source $gi -combinational $go
    set clocks [get_clocks [list $name $gn]]
    set_clock_uncertainty -setup 60 $clocks
    set_clock_uncertainty -hold 25 $clocks
    set_clock_gating_check -setup 60 -hold 25 $cell
    ot_v9_field::pins [dict get $binding gate_enable_launch] {/(Q|QN)$}
    foreach role {activation configuration go result vm_read vm_write macro_read} {
        if {![dict exists $binding boundaries $role]} {error "v9 field: missing $role path"}
        set path [dict get $binding boundaries $role]
        ot_v9_field::pins [dict get $path launch] {/(Q|QN|rd_out\[[0-9]+\])$}
        ot_v9_field::pins [dict get $path capture] {/D$}
    }
    if {[llength [dict get $binding macro_cells]] != 4} {error "v9 field: full NB=2 PP=1 pair requires four real weight ROMs"}
    foreach n [dict get $binding macro_cells] {
        set c [get_cells -quiet $n]
        if {[llength $c] != 1 || [get_full_name $c] ne $n ||
            [get_property $c ref_name] ne "ot_rom_4096x274_m8"} {
            error "v9 field: selected real 4096-row weight macro absent: $n"
        }
    }
    # No false paths, asynchronous clock groups, IO arrival substitutions,
    # multicycle exceptions, or changes to the existing ping-pong constraints.
}

proc ot_v9_field::report {binding prefix} {
    # Invoke only AFTER CTS and the actual parasitics are loaded. This is a
    # query of the enclosing parent's paths, not a closure flag.
    set clocks [get_clocks [list [dict get $binding root_clock] [dict get $binding gated_clock]]]
    if {[llength $clocks] != 2} {error "v9 field: root/gated clocks not bound"}
    set_propagated_clock $clocks
    report_clock_properties $clocks > ${prefix}.clocks.rpt
    foreach role {spine field vm} {
        set anchor [ot_v9_field::one pin [dict get $binding clock_anchors $role]]
        if {[lsearch -exact [all_registers -clock [dict get $binding root_clock] -clock_pins] $anchor] < 0} {
            error "v9 field: $role anchor has no actual parent clock"
        }
    }
    foreach role {activation configuration go result vm_read vm_write macro_read} {
        set path [dict get $binding boundaries $role]
        set q [ot_v9_field::pins [dict get $path launch] {/(Q|QN|rd_out\[[0-9]+\])$}]
        set d [ot_v9_field::pins [dict get $path capture] {/D$}]
        set launch_clock [dict get $binding root_clock]
        set capture_clock $launch_clock
        if {$role in {activation macro_read}} {set capture_clock [dict get $binding gated_clock]}
        if {$role in {result macro_read}} {set launch_clock [dict get $binding gated_clock]}
        foreach dp $d {
            if {[lsearch -exact [all_registers -clock $capture_clock -data_pins] $dp] < 0} {
                error "v9 field: $role capture lacks expected $capture_clock: [get_full_name $dp]"
            }
        }
        if {$role ne "macro_read"} {
            foreach qp $q {
                if {[lsearch -exact [all_registers -clock $launch_clock -output_pins] $qp] < 0} {
                    error "v9 field: $role launch lacks expected $launch_clock: [get_full_name $qp]"
                }
            }
        }
        foreach delay {min max} {
            if {![llength [find_timing_paths -from $q -to $d -path_delay $delay -group_count 1]]} {
                error "v9 field: $role has no $delay timed path; missing_input_clocks remains true"
            }
            report_checks -from $q -to $d -path_delay $delay -group_count 10 \
                -format full_clock_expanded -fields {slew capacitance input_pin net} > ${prefix}.${role}.${delay}.rpt
        }
    }
    # All anchors must really carry the bound clock. OpenSTA's clock arrival
    # reports retain insertion/slew; no zero or ideal latency is substituted.
    report_clock_latency -clock $clocks -include_internal_latency > ${prefix}.latency.rpt
    set enq [ot_v9_field::pins [dict get $binding gate_enable_launch] {/(Q|QN)$}]
    set ena [ot_v9_field::one pin [dict get $binding gate_enable]]
    foreach delay {min max} {
        if {![llength [find_timing_paths -from $enq -to $ena -path_delay $delay -group_count 1]]} {
            error "v9 field: registered gate-enable has no $delay gating check"
        }
        report_checks -from $enq -to $ena -path_delay $delay -group_count 10 \
            -format full_clock_expanded -fields {slew capacitance input_pin net} > ${prefix}.gate_enable.${delay}.rpt
    }
    check_setup -verbose > ${prefix}.check_setup.rpt
    report_checks -path_delay min_max -unconstrained -format full_clock_expanded > ${prefix}.unconstrained.rpt
}
