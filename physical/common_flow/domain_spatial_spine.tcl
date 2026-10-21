# Exact pre-CTS ownership admission for the supported per-existing-domain API.
# This guard changes no clock, timing constraint, endpoint or spine algorithm.
namespace eval ot_dsp {}

proc ot_dsp::landed_unused {master pin} {
    set name [$master getName]
    return [expr {[$master isBlock]
        && [info exists ::ot_ce_landed_cluster] && $::ot_ce_landed_cluster
        && [info exists ::ot_ce_counts] && [dict exists $::ot_ce_counts $name]
        && [info exists ::ot_ce_landed_unused]
        && [dict exists $::ot_ce_landed_unused "$name/$pin"]}]
}

proc ot_dsp::validate {roots rootnets contacts nonclock} {
    if {[lsort [dict keys $rootnets]] ne [lsort $roots]} {
        error "OT_DOMAIN_SPINE missing/mismatched root coverage"
    }
    set nets {}; set counts {}; set seen {}
    foreach root $roots {
        set net [dict get $rootnets $root]
        if {$net eq "" || $net eq "NULL" || [dict exists $nets $net]} {
            error "OT_DOMAIN_SPINE missing or multiply-owned root net $root"
        }
        dict set nets $net $root
        dict set counts $root 0
    }
    foreach contact $contacts {
        lassign $contact terminal net
        if {[dict exists $seen $terminal]} {error "OT_DOMAIN_SPINE multiply-owned clock terminal $terminal"}
        dict set seen $terminal 1
        if {![dict exists $nets $net]} {error "OT_DOMAIN_SPINE unowned clock terminal $terminal"}
        dict incr counts [dict get $nets $net]
    }
    if {[llength $nonclock]} {error "OT_DOMAIN_SPINE root reaches non-clock terminal [lindex $nonclock 0]"}
    dict for {root count} $counts {
        if {!$count} {error "OT_DOMAIN_SPINE root $root has no actual clock contacts"}
        puts "OT_DOMAIN_SPINE OWNERSHIP root=$root physical_liberty_clock_contacts=$count"
    }
    return $counts
}

proc ot_dsp::admit {} {
    set block [ord::get_db_block]
    set rootnets {}; set netowners {}; set clocksources {}
    foreach clock [all_clocks] {
        foreach source [get_property $clock sources] {
            set root [get_full_name $source]
            if {$root ni $::ot_dsp_roots || [dict exists $clocksources $root]} {
                error "OT_DOMAIN_SPINE undeclared or multiply-clocked source $root"
            }
            dict set clocksources $root 1
        }
    }
    if {[lsort [dict keys $clocksources]] ne [lsort $::ot_dsp_roots]} {
        error "OT_DOMAIN_SPINE SDC source/root coverage mismatch"
    }
    foreach root $::ot_dsp_roots {
        set port [$block findBTerm $root]
        if {$port eq "" || $port eq "NULL"} {error "OT_DOMAIN_SPINE missing root port $root"}
        set net [$port getNet]
        if {$net eq "" || $net eq "NULL"} {error "OT_DOMAIN_SPINE disconnected root port $root"}
        dict set rootnets $root $net
        dict set netowners $net $root
    }
    set cache {}; set contacts {}; set nonclock {}
    foreach instance [$block getInsts] {
        set master [$instance getMaster]
        set name [$master getName]
        if {![dict exists $cache $name]} {
            set roles {}; set libraries [get_lib_cells -quiet "*/$name"]
            if {![llength $libraries] && ([$master isSequential] || [$master isBlock])} {
                error "OT_DOMAIN_SPINE missing actual Liberty clock roles for $name"
            }
            foreach cell $libraries {
                set one {}
                foreach pin [get_lib_pins -quiet -of_objects $cell] {
                    if {[get_property $pin is_clock]} {lappend one [get_property $pin name]}
                }
                set one [lsort -unique $one]
                if {[info exists previous] && $previous ne $one} {
                    error "OT_DOMAIN_SPINE inconsistent Liberty clock roles for $name"
                }
                set previous $one
                set roles $one
            }
            unset -nocomplain previous
            dict set cache $name $roles
        }
        set seenclock {}
        foreach terminal [$instance getITerms] {
            if {[$terminal getSigType] in {POWER GROUND}} continue
            set pin [[$terminal getMTerm] getName]
            set net [$terminal getNet]
            set path "[$instance getName]/$pin"
            if {$pin in [dict get $cache $name]} {
                if {![$terminal isInputSignal]} {error "OT_DOMAIN_SPINE invalid clock contact direction $path"}
                lappend seenclock $pin
                lappend contacts [list $path $net]
            } elseif {[$terminal isInputSignal] && [dict exists $netowners $net]
                      && [ot_dsp::landed_unused $master $pin]} {
                # Same source-proven unloaded hard-input law as clock_entries.
                # It is neither a Liberty clock contact nor a new exemption.
                continue
            } elseif {[$terminal getSigType] eq "CLOCK"} {
                error "OT_DOMAIN_SPINE unknown physical clock terminal $path lacks actual Liberty clock role"
            } elseif {[$terminal isInputSignal] && [dict exists $netowners $net]} {
                lappend nonclock $path
            }
        }
        if {[lsort $seenclock] ne [dict get $cache $name]} {
            error "OT_DOMAIN_SPINE physical/Liberty clock-pin coverage mismatch [$instance getName]"
        }
    }
    set counts [ot_dsp::validate $::ot_dsp_roots $rootnets $contacts $nonclock]
    if {[info exists ::ot_sp_record_taps_v1]} {ot_srt::admit $rootnets $contacts}
    return $counts
}

if {[info procs clock_tree_synthesis] ne "" && [info procs ot_dsp_cts_orig] eq ""} {
    rename clock_tree_synthesis ot_dsp_cts_orig
    proc clock_tree_synthesis {args} {
        ot_dsp::admit
        # clock_entries still checks every native/landed/raw-memory endpoint;
        # its inner call dispatches to the unchanged canonical spine engine.
        ot_dsp_cts_orig {*}$args
    }
}
