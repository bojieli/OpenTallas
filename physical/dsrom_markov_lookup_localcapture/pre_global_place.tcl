source /src/physical/dsrom_markov_lookup_localcapture/capture_anchor.tcl
source /src/physical/dsrom_markov_lookup_localcapture/electrical_env.tcl
# ORFS removes buffers AFTER this hook, then calls buffer_ports with no args.
# Configure that actual insertion: preserve native input buffering, select the
# measured1.62x0.27um output master once, after remove_buffers (112.8492um2).
if {![llength [info commands ::ot_md6_original_buffer_ports]]} {
    rename ::buffer_ports ::ot_md6_original_buffer_ports
    proc ::buffer_ports {args} {
        if {[llength $args]} {error "MD6 pair expects pinned ORFS default buffer_ports invocation"}
        ot_md6_original_buffer_ports -inputs
        ot_md6_original_buffer_ports -outputs -buffer_cell BUFx24_ASAP7_75t_R -max_utilization 60 -verbose
        # Preserve this selected drive through GPL's timing-driven downsizing.
        # These are combinational output buffers, never capture or clock cells.
        # Output nets stay editable for a later hold repair.
        set count 0
        foreach port [[ord::get_db_block] getBTerms] {
            if {[$port getIoType] ne "OUTPUT"} {continue}
            foreach term [[$port getNet] getITerms] {
                if {[$term getIoType] ne "OUTPUT"} {continue}
                set cell [$term getInst]
                if {[[$cell getMaster] getName] ne "BUFx24_ASAP7_75t_R"} {error "unexpected selected output drive"}
                set_dont_touch [get_cells [$cell getName]]
                incr count
            }
        }
        if {$count!=258} {error "expected258 selected nonclock output buffers"}
        puts "MD6_ACTUAL_OUTPUT_BUFFER_MASTER BUFx24_ASAP7_75t_R"
    }
}
