# The generated boundary file is also sourced at other stages. Run only inside
# the generated post-tree clock_tree_synthesis wrapper, once in this process.
if {[info level] == 0} {return}
if {[lindex [info level 0] 0] ne "clock_tree_synthesis"} {return}
if {[info exists ::ot_ccf_internal_hold_once]} {return}
set ::ot_ccf_internal_hold_once 1
# CCF only: repair real internal hold paths before the ordinary CTS hold pass.
# The original standalone input MIN references the root pin, while native peers
# deliver phi-R. Those external paths stalled the global pass at -151 ps and
# left 39 internal checks at -8 ps. Optimize internal paths separately, then
# restore EVERY original constraint before the normal pass and published STA.
# No exception may survive this hook. Actual external peer hold remains mandatory.
proc ot_ccf_constraint_lines {file} {
    set fp [open $file r]
    set lines {}
    foreach line [split [read $fp] "\n"] {
        set line [string trim $line]
        if {$line ne "" && ![string match {#*} $line]} {lappend lines $line}
    }
    close $fp
    return [lsort $lines]
}
set ih_before "$::env(RESULTS_DIR)/ot_ccf_internal_hold_before.sdc"
set ih_after "$::env(RESULTS_DIR)/ot_ccf_internal_hold_after.sdc"
write_sdc $ih_before
set ih_original [ot_ccf_constraint_lines $ih_before]
# This specific candidate's input SDC has no path exceptions. Refuse to remove
# any pre-existing exception by accident; this hook is not a general SDC editor.
foreach ih_line $ih_original {
    if {[regexp {^(set_false_path|set_multicycle_path|set_max_delay|set_min_delay|set_path_margin)\M} $ih_line]} {
        error "CCF_INTERNAL_HOLD: existing path exception requires exact independent preservation"
    }
}
set ih_external [all_inputs -no_clocks]
puts "CCF_INTERNAL_HOLD: begin internal-only optimization, final SDC unchanged"
set_false_path -hold -from $ih_external
try {
    unset_dont_use [get_lib_cells {*/HB1xp67_ASAP7_75t_R */HB2xp67_ASAP7_75t_R}]
    repair_timing -hold -hold_margin 15 -max_buffer_percent 10 -max_iterations 1000 -verbose
} finally {
    unset_path_exceptions -hold -from $ih_external
}
write_sdc $ih_after
if {[ot_ccf_constraint_lines $ih_after] ne $ih_original} {
    error "CCF_INTERNAL_HOLD: constraint restoration changed the original SDC"
}
puts "CCF_INTERNAL_HOLD: all original constraints restored identically; normal CTS repair and actual peer hold remain active"
