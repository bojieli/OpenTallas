# Equal-state physical copies of existing reset pipeline flops. No new pipeline
# stage, clock phase or reset release age. Source D/control/clock pins are copied
# exactly. Revisit upstream stages after splitting, since their D fanout grows.
namespace eval ot_lpc {
    variable block [ord::get_db_block]
    variable limit 32
    variable serial 0
    variable copies {}
    variable match $::ot_reset_copy_regexp
    variable origin {}
}
proc ot_lpc::is_reset_stage {inst} {
    variable match
    expr {[regexp $match [$inst getName]] || [regexp {^ot_lpr_copy_[0-9]+$} [$inst getName]]}
}
proc ot_lpc::inputs {inst} {
    set result {}
    foreach it [$inst getITerms] {
        if {[$it isInputSignal]} {dict set result [[$it getMTerm] getName] [$it getNet]}
    }
    return $result
}
proc ot_lpc::loads {net {path {}} {seen {}}} {
    if {[dict exists $seen $net]} {error "OT_LPC buffer loop"}
    dict set seen $net 1
    set result {}
    foreach it [$net getITerms] {
        if {![$it isInputSignal]} continue
        set inst [$it getInst]; set m [$inst getMaster]; set name [$m getName]
        # Explicit ASAP7 one-input buffer/inverter families only. Other logic is
        # a terminal; its equation is never bypassed or altered.
        if {[string match BUF* $name] || [string match *INV* $name]} {
            set inputs {}; set outputs {}
            foreach bp [$inst getITerms] {
                if {[$bp isInputSignal]} {lappend inputs $bp}
                if {[$bp isOutputSignal]} {lappend outputs $bp}
            }
            if {[llength $inputs] != 1 || [llength $outputs] != 1} {error "OT_LPC unexpected buffer ABI $name"}
            set next [[lindex $outputs 0] getNet]
            if {$next ne "NULL" && $next ne ""} {
                lappend result {*}[loads $next [concat $path [list $inst]] $seen]
            }
        } else {lappend result [list $it $path]}
    }
    return $result
}
proc ot_lpc::copy_path {path source cacheName prefix} {
    upvar 1 $cacheName cache
    variable block
    set current $source
    foreach original $path {
        set key [list $current $original]
        if {[dict exists $cache $key]} {set current [dict get $cache $key]; continue}
        set n [dict size $cache]
        set copy [odb::dbInst_create $block [$original getMaster] ${prefix}_b$n]
        set next [odb::dbNet_create $block ${prefix}_bn$n]
        foreach it [$original getITerms] {
            set term [$copy findITerm [[$it getMTerm] getName]]
            if {[$it isInputSignal]} {$term connect $current}
            if {[$it isOutputSignal]} {$term connect $next}
            if {[$it getSigType] in {POWER GROUND} && [$it getNet] ne "NULL"} {$term connect [$it getNet]}
        }
        dict set ::ot_lpc::origin $copy $original
        lappend ::ot_lpc::copies [list $copy $original]
        $copy setDoNotTouch true
        dict set cache $key $next
        set current $next
    }
    return $current
}
set changed 1
while {$changed} {
    set changed 0
    foreach inst [$ot_lpc::block getInsts] {
        if {![ot_lpc::is_reset_stage $inst]} continue
        set master [$inst getMaster]
        if {![$master isSequential]} continue
        foreach op [$inst getITerms] {
            if {![$op isOutputSignal]} continue
            set net [$op getNet]
            if {$net eq "NULL" || $net eq ""} continue
            set loads [ot_lpc::loads $net]
            if {[llength $loads] <= $ot_lpc::limit} continue
            set inmap [ot_lpc::inputs $inst]
            $inst setDoNotTouch true
            # Retain the first chunk on the original, move each remaining chunk
            # to an exact same-edge copy. Clones are soft/unplaced for cone placement.
            for {set offset $ot_lpc::limit} {$offset < [llength $loads]} {incr offset $ot_lpc::limit} {
                incr ot_lpc::serial
                set name [format "ot_lpr_copy_%05d" $ot_lpc::serial]
                set copy [odb::dbInst_create $ot_lpc::block $master $name]
                foreach it [$inst getITerms] {
                    if {![$it isInputSignal] && [$it getSigType] ni {POWER GROUND}} continue
                    set input_net [$it getNet]
                    if {$input_net eq "NULL" || $input_net eq ""} continue
                    [$copy findITerm [[$it getMTerm] getName]] connect $input_net
                }
                set copy_net [odb::dbNet_create $ot_lpc::block ${name}_q]
                $copy_net setSigType [$net getSigType]
                [$copy findITerm [[$op getMTerm] getName]] connect $copy_net
                set path_cache {}
                foreach endpoint [lrange $loads $offset [expr {$offset+$ot_lpc::limit-1}]] {
                    lassign $endpoint load path
                    set sink_net [ot_lpc::copy_path $path $copy_net path_cache $name]
                    set sink_inst [$load getInst]
                    set preserve_touch [$sink_inst isDoNotTouch]
                    if {$preserve_touch} {$sink_inst setDoNotTouch false}
                    $load disconnect
                    $load connect $sink_net
                    if {$preserve_touch} {$sink_inst setDoNotTouch true}
                }
                if {[$copy getMaster] ne $master || [ot_lpc::inputs $copy] ne $inmap} {
                    error "OT_LPC clone does not preserve master and all inputs of [$inst getName]"
                }
                $copy setDoNotTouch true
                dict set ot_lpc::origin $copy $inst
                lappend ot_lpc::copies [list $copy $inst]
            }
            puts "OT_LPC split=[$inst getName]/[[$op getMTerm] getName] original_loads=[llength $loads]"
            set changed 1
        }
    }
}
# An independent final wiring check normalizes copied-driver identities, so
# recursively copied upstream reset stages must remain the exact same equations.
proc ot_lpc::signature {net} {
    variable origin
    if {$net eq "NULL" || $net eq ""} {return {unconnected}}
    set sig {}
    foreach it [$net getITerms] {
        if {![$it isOutputSignal]} continue
        set driver [$it getInst]
        set seen {}
        while {[dict exists $origin $driver]} {
            if {[dict exists $seen $driver]} {error "OT_LPC copy alias loop"}
            dict set seen $driver 1; set driver [dict get $origin $driver]
        }
        lappend sig [list cell $driver [[$it getMTerm] getName]]
    }
    foreach bt [$net getBTerms] {
        if {[$bt getIoType] eq "INPUT"} {lappend sig [list port [$bt getName]]}
    }
    if {![llength $sig]} {return [list undriven $net]}
    return [lsort $sig]
}
set checked 0
foreach pair $ot_lpc::copies {
    lassign $pair copy original
    if {[$copy getMaster] ne [$original getMaster]} {error "OT_LPC final master differs"}
    foreach it [$copy getITerms] {
        if {![$it isInputSignal]} continue
        set source [$original findITerm [[$it getMTerm] getName]]
        if {[ot_lpc::signature [$it getNet]] ne [ot_lpc::signature [$source getNet]]} {
            error "OT_LPC final input equation differs [$copy getName]/[[$it getMTerm] getName]"
        }
    }
    incr checked
}
puts "OT_LPC_FINAL_EQUIVALENCE PASS same_master_all_signal_inputs=$checked copies_and_buffer_paths"
# Check after recursion, because an upstream split may reconnect the input of
# an already-created copy to an equivalent same-edge ancestor's output.
set maxload 0; set stages 0
foreach inst [$ot_lpc::block getInsts] {
    if {![ot_lpc::is_reset_stage $inst]} continue
    incr stages
    foreach op [$inst getITerms] {
        if {![$op isOutputSignal]} continue
        set net [$op getNet]
        if {$net eq "NULL" || $net eq ""} continue
        set n [llength [ot_lpc::loads $net]]
        if {$n > $maxload} {set maxload $n}
        if {$n > $ot_lpc::limit} {error "OT_LPC output exceeds32 loads after recursion"}
    }
}
puts "OT_LPC PASS existing_stages_and_copies=$stages new_copies=$ot_lpc::serial maximum_buffer_tree_terminal_load=$maxload same_master_and_inputs_at_clone=PASS no_added_edges=0"
