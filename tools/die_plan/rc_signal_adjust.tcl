# rc_signal_adjust.tcl (r222, GENBUG-IMPL 11-15): signal-net wire cap on the GRT estimate basis.
#
# setRC_rcx.tcl's set_layer_rc table is calibrated to routed OpenRCX CLOCK-sink arrivals; OpenROAD's set_layer_rc has no
# per-class form, so estimate_parasitics -global_routing prices every net with it.  Long SIGNAL nets are 2x higher in
# the routed SPEF (M4-M7 +0.08 fF/um; col_h9_r2 gate -149 vs sign-off -267 ps).  Fit (6 routed col_h9_r2 kits, rc_calib.py fit
# --sigtype SIGNAL, 96k signal nets each, spread between kits <= 0.013 fF/um): signal unit C fF/um
#   M2 .186  M3 .131  M4 .209  M5 .175  M6 .207  M7 .181
# This proc adds, per SIGNAL net, delta C = sum over layers (C_signal - C_table) * GRT guide length as a net wire load
# (set_load -wire_load).  Clock nets (sigtype CLOCK) and power nets are untouched, so the clock-sink estimate does not move.
# Call after estimate_parasitics -global_routing; opt-in env OT_RC_SIGNAL=1 in the callers (default off = no change).
proc ot_rc_signal_adjust {} {
    array set csig {M2 0.186 M3 0.131 M4 0.209 M5 0.175 M6 0.207 M7 0.181}
    if {[info exists ::env(OT_RC_SIGNAL_C)]} { array set csig $::env(OT_RC_SIGNAL_C) }
    array set ctab {}
    set f ""
    if {[info exists ::env(LAYER_PARASITICS_FILE)] && [file exists $::env(LAYER_PARASITICS_FILE)]} { set f $::env(LAYER_PARASITICS_FILE) }
    if {$f ne ""} {
        set fh [open $f]
        while {[gets $fh ln] >= 0} {
            if {[regexp {^set_layer_rc\s+-layer\s+(M\d)\s+-resistance\s+\S+\s+-capacitance\s+(\S+)} $ln -> L c]} { set ctab($L) $c }
        }
        close $fh
    }
    set blk [ord::get_db_block]
    set dbu [$blk getDbUnitsPerMicron]
    set n 0; set tot 0.0
    foreach net [$blk getNets] {
        if {[$net getSigType] ne "SIGNAL"} continue
        set d 0.0
        foreach g [$net getGuides] {
            set L [[$g getLayer] getName]
            if {![info exists csig($L)] || ![info exists ctab($L)]} continue
            set b [$g getBox]
            set len [expr {max([$b xMax]-[$b xMin], [$b yMax]-[$b yMin]) / double($dbu)}]
            set d [expr {$d + ($csig($L) - $ctab($L)) * $len}]
        }
        if {$d > 0.0} {
            set_load -wire_load $d [get_nets -quiet -hierarchical [string map {\[ \\[ \] \\]} [$net getName]]]
            incr n; set tot [expr {$tot + $d}]
        }
    }
    puts [format "OT_RC_SIGNAL adjusted %d signal nets, +%.1f fF wire load (signal C M4 %.3f M5 %.3f M6 %.3f M7 %.3f fF/um vs table)" $n $tot $csig(M4) $csig(M5) $csig(M6) $csig(M7)]
}
