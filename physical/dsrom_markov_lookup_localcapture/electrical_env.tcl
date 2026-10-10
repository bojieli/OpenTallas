# Restore the SAME electrical contract after ORFS multi-mode scenes exist.
# read_sdc before define_scene loses port loads; this is not a load reduction.
set protected 0
foreach macro [[ord::get_db_block] getInsts] {
    if {[[$macro getMaster] getName] ne "ot_rom_4096x274_m8"} {continue}
    foreach q [$macro getITerms] {
        if {![regexp {^rd_out\[([0-9]+)\]$} [[$q getMTerm] getName] -> bit] || $bit>=256} {continue}
        set net [$q getNet]
        set_dont_touch [get_nets [$net getName]]
        foreach t [$net getITerms] {
            if {$t ne $q && [$t getIoType] eq "INPUT"} {
                set capture_cells [get_cells [[$t getInst] getName]]
                if {[info exists ::ot_capture_allow_clock_reconnect] && $::ot_capture_allow_clock_reconnect} {
                    # CTS must reconnect CLK; D/q net protection and FIRM stay.
                    unset_dont_touch $capture_cells
                } else {
                    set_dont_touch $capture_cells
                }
            }
        }
        incr protected
    }
}
if {$protected!=512} {error "electrical repair requires512 protected direct ROM capture nets"}
puts "MD6_ELECTRICAL_ENV protected_direct_capture_nets=$protected"
if {[info exists ::ot_mm_active] && $::ot_mm_active} {
    foreach mode {ss ff} {
        set_mode $mode
        set_load 3.898 [all_outputs]
        set_max_transition 250 [current_design]
        set_max_fanout 16 [current_design]
        puts "MD6_ELECTRICAL_ENV mode=$mode output_load=3.898 max_transition=250 max_fanout=16"
    }
    set_mode ss
} else {
    set_load 3.898 [all_outputs]
    set_max_transition 250 [current_design]
    set_max_fanout 16 [current_design]
    puts "MD6_ELECTRICAL_ENV mode=current output_load=3.898 max_transition=250 max_fanout=16"
}
