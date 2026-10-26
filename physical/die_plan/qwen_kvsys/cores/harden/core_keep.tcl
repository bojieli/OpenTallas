# Core members do not use the partition u_bin/u_bout naming convention.
# Preserve sequential cells through synth_odb's eliminate_dead_logic, including
# declared boundary captures whose Q is intentionally unused. Yosys has already
# removed ordinary dead state. Remember pre-existing dont_touch flags.
uplevel #0 {
set ot_core_kept {}
foreach i [[ord::get_db_block] getInsts] {
    if {[[$i getMaster] isSequential] && ![$i isDoNotTouch]} {
        $i setDoNotTouch 1
        lappend ot_core_kept [$i getName]
    }
}
puts "OT_CORE_KEEP preserved [llength $ot_core_kept] sequential cells through eliminate_dead_logic"
}
