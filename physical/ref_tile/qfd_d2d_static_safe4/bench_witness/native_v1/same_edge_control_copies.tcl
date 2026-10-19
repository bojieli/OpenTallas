# Equal-state/source-equation physical copies of mapped sequential and combinational
# control drivers. Explicit opt-in required. Clock nets and hard macros excluded.
# HB2/HB4 noninverting semantics must be proved from the pinned Liberty before use.
# Equal-state physical copies of existing reset pipeline flops. No new pipeline
# stage, clock phase or reset release age. Source D/control/clock pins are copied
# exactly. Revisit upstream stages after splitting, since their D fanout grows.
namespace eval ot_ctlc {
    variable block [ord::get_db_block]
    # Actual original NAND driver maxcap23.04 versus measured24.23 at32 terminals.
    # Sixteen terminal owners reserve at least half the pin-load budget for wire.
    # Native TT/FF cap/slew audit is mandatory; this bound is not a timing waiver.
    variable limit 16
    variable serial 0
    variable copies {}
    variable match $::ot_control_copy_regexp
    variable origin {}
    variable max_copies 10000
}
proc ot_ctlc::connect {term net} {
 set inst [$term getInst];set itouch [$inst isDoNotTouch]
 set old [$term getNet];set otouch 0;set ntouch [$net isDoNotTouch]
 if {$old ne "NULL" && $old ne ""} {set otouch [$old isDoNotTouch]}
 if {$itouch} {$inst setDoNotTouch false}
 if {$otouch} {$old setDoNotTouch false}
 if {$ntouch} {$net setDoNotTouch false}
 try {if {$old ne "NULL" && $old ne ""} {$term disconnect};$term connect $net} finally {
  if {$otouch} {$old setDoNotTouch true}
  if {$ntouch} {$net setDoNotTouch true}
  if {$itouch} {$inst setDoNotTouch true}
 }
}
proc ot_ctlc::is_reset_stage {inst} {
    variable match
    expr {[regexp $match [$inst getName]] || [regexp {^ot_ctl_copy_[0-9]+$} [$inst getName]]}
}
proc ot_ctlc::inputs {inst} {
    set result {}
    foreach it [$inst getITerms] {
        if {[$it isInputSignal]} {dict set result [[$it getMTerm] getName] [$it getNet]}
    }
    return $result
}
proc ot_ctlc::loads {net {path {}} {seen {}}} {
    if {[dict exists $seen $net]} {error "OT_CTLC buffer loop"}
    dict set seen $net 1
    set result {}
    foreach it [$net getITerms] {
        if {![$it isInputSignal]} continue
        set inst [$it getInst]; set m [$inst getMaster]; set name [$m getName]
        # Explicit ASAP7 one-input buffer/inverter families only. Other logic is
        # a terminal; its equation is never bypassed or altered.
        if {[string match BUF* $name] || [string match *INV* $name] || $name in {HB2xp67_ASAP7_75t_R HB4xp67_ASAP7_75t_R}} {
            set inputs {}; set outputs {}
            foreach bp [$inst getITerms] {
                if {[$bp isInputSignal]} {lappend inputs $bp}
                if {[$bp isOutputSignal]} {lappend outputs $bp}
            }
            if {[llength $inputs] != 1 || [llength $outputs] != 1} {error "OT_CTLC unexpected buffer ABI $name"}
            set next [[lindex $outputs 0] getNet]
            if {$next ne "NULL" && $next ne ""} {
                lappend result {*}[loads $next [concat $path [list $inst]] $seen]
            }
        } else {lappend result [list $it $path]}
    }
    return $result
}
proc ot_ctlc::copy_path {path source cacheName prefix} {
    upvar 1 $cacheName cache
    variable block
    set current $source
    foreach original $path {
        set key [list $current $original]
        if {[dict exists $cache $key]} {set current [dict get $cache $key]; continue}
        set n [dict size $cache]
        set copy [odb::dbInst_create $block [$original getMaster] ${prefix}_b$n]
        set next [odb::dbNet_create $block ${prefix}_bn$n]
        $copy setOrient [$original getOrient]
        lassign [$original getLocation] ox oy
        $copy setLocation $ox $oy
        $copy setPlacementStatus PLACED
        foreach it [$original getITerms] {
            set term [$copy findITerm [[$it getMTerm] getName]]
            if {[$it isInputSignal]} {ot_ctlc::connect $term $current}
            if {[$it isOutputSignal]} {ot_ctlc::connect $term $next}
            if {[$it getSigType] in {POWER GROUND} && [$it getNet] ne "NULL"} {ot_ctlc::connect $term [$it getNet]}
        }
        dict set ::ot_ctlc::origin $copy $original
        lappend ::ot_ctlc::copies [list $copy $original]
        dict set cache $key $next
        set current $next
    }
    return $current
}
set changed 1
while {$changed} {
    set changed 0
    foreach inst [$ot_ctlc::block getInsts] {
        if {![ot_ctlc::is_reset_stage $inst]} continue
        set master [$inst getMaster]
        if {[$master isBlock]} continue
        set mn [$master getName]
        if {[string match BUF* $mn] || [string match *INV* $mn] || $mn in {HB2xp67_ASAP7_75t_R HB4xp67_ASAP7_75t_R}} continue
        foreach op [$inst getITerms] {
            if {![$op isOutputSignal]} continue
            set net [$op getNet]
            if {$net eq "NULL" || $net eq ""} continue
            if {[$net getSigType] eq "CLOCK"} continue
            set loads [ot_ctlc::loads $net]
            if {[llength $loads] <= $ot_ctlc::limit} continue
            set inmap [ot_ctlc::inputs $inst]
            # Retain the first chunk on the original, move each remaining chunk
            # to an exact same-edge copy. Clones are soft/unplaced for cone placement.
            for {set offset $ot_ctlc::limit} {$offset < [llength $loads]} {incr offset $ot_ctlc::limit} {
                incr ot_ctlc::serial
                if {$ot_ctlc::serial>$ot_ctlc::max_copies} {error "OT_CTLC bounded control replication exceeds10000 copies"}
                set name [format "ot_ctl_copy_%05d" $ot_ctlc::serial]
                set copy [odb::dbInst_create $ot_ctlc::block $master $name]
                $copy setOrient [$inst getOrient]
                lassign [$inst getLocation] ox oy
                $copy setLocation $ox $oy
                $copy setPlacementStatus PLACED
                foreach it [$inst getITerms] {
                    if {![$it isInputSignal] && [$it getSigType] ni {POWER GROUND}} continue
                    set input_net [$it getNet]
                    if {$input_net eq "NULL" || $input_net eq ""} continue
                    ot_ctlc::connect [$copy findITerm [[$it getMTerm] getName]] $input_net
                }
                set copy_net [odb::dbNet_create $ot_ctlc::block ${name}_q]
                $copy_net setSigType [$net getSigType]
                ot_ctlc::connect [$copy findITerm [[$op getMTerm] getName]] $copy_net
                set path_cache {}
                foreach endpoint [lrange $loads $offset [expr {$offset+$ot_ctlc::limit-1}]] {
                    lassign $endpoint load path
                    set sink_net [ot_ctlc::copy_path $path $copy_net path_cache $name]
                    set sink_inst [$load getInst]
                    set preserve_touch [$sink_inst isDoNotTouch]
                    if {$preserve_touch} {$sink_inst setDoNotTouch false}
                    set old_net [$load getNet]
                    set old_touch [$old_net isDoNotTouch]
                    if {$old_touch} {$old_net setDoNotTouch false}
                    try {ot_ctlc::connect $load $sink_net} finally {if {$old_touch} {$old_net setDoNotTouch true}}
                    if {$preserve_touch} {$sink_inst setDoNotTouch true}
                }
                if {[$copy getMaster] ne $master || [ot_ctlc::inputs $copy] ne $inmap} {
                    error "OT_CTLC clone does not preserve master and all inputs of [$inst getName]"
                }
                        dict set ot_ctlc::origin $copy $inst
                lappend ot_ctlc::copies [list $copy $inst]
            }
            puts "OT_CTLC split=[$inst getName]/[[$op getMTerm] getName] original_loads=[llength $loads]"
            set changed 1
        }
    }
}
# An independent final wiring check normalizes copied-driver identities, so
# recursively copied upstream reset stages must remain the exact same equations.
proc ot_ctlc::signature {net} {
    variable origin
    if {$net eq "NULL" || $net eq ""} {return {unconnected}}
    set sig {}
    foreach it [$net getITerms] {
        if {![$it isOutputSignal]} continue
        set driver [$it getInst]
        set seen {}
        while {[dict exists $origin $driver]} {
            if {[dict exists $seen $driver]} {error "OT_CTLC copy alias loop"}
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
foreach pair $ot_ctlc::copies {
    lassign $pair copy original
    if {[$copy getMaster] ne [$original getMaster]} {error "OT_CTLC final master differs"}
    foreach it [$copy getITerms] {
        if {![$it isInputSignal]} continue
        set source [$original findITerm [[$it getMTerm] getName]]
        if {[ot_ctlc::signature [$it getNet]] ne [ot_ctlc::signature [$source getNet]]} {
            error "OT_CTLC final input equation differs [$copy getName]/[[$it getMTerm] getName]"
        }
    }
    incr checked
}
puts "OT_CTLC_FINAL_EQUIVALENCE PASS same_master_all_signal_inputs=$checked copies_and_buffer_paths"
# Check after recursion, because an upstream split may reconnect the input of
# an already-created copy to an equivalent same-edge ancestor's output.
set maxload 0; set stages 0
foreach inst [$ot_ctlc::block getInsts] {
    if {![ot_ctlc::is_reset_stage $inst]} continue
    set master [$inst getMaster];set mn [$master getName]
    if {[$master isBlock] || [string match BUF* $mn] || [string match *INV* $mn] || $mn in {HB2xp67_ASAP7_75t_R HB4xp67_ASAP7_75t_R}} continue
    incr stages
    foreach op [$inst getITerms] {
        if {![$op isOutputSignal]} continue
        set net [$op getNet]
        if {$net eq "NULL" || $net eq ""} continue
            if {[$net getSigType] eq "CLOCK"} continue
        set n [llength [ot_ctlc::loads $net]]
        if {$n > $maxload} {set maxload $n}
        if {$n > $ot_ctlc::limit} {error "OT_CTLC output exceeds32 loads after recursion"}
    }
}
puts "OT_CTLC PASS existing_stages_and_copies=$stages new_copies=$ot_ctlc::serial maximum_buffer_tree_terminal_load=$maxload same_master_and_inputs_at_clone=PASS added_FF_edges=0"

# Source-pinned proof record includes every copied master and all input equations.
set out [open $::ot_control_copy_manifest w]
set aliases {};set records {}
foreach pair $ot_ctlc::copies {
 lassign $pair copy original
 dict set aliases [$copy getName] [$original getName]
 set inputs {}
 foreach pin [$copy getITerms] {if {[$pin isInputSignal]} {dict set inputs [[$pin getMTerm] getName] [ot_ctlc::signature [$pin getNet]]}}
 lappend records [list [$copy getName] [$original getName] [[$copy getMaster] getName] $inputs]
}
puts $out [list set ::ot_control_copy_aliases $aliases]
puts $out [list set ::ot_control_copy_records $records]
close $out
puts "OT_CTLC_MANIFEST $::ot_control_copy_manifest copied_cells=[llength $records]"
