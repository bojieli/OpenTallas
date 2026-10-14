# Scoped recovery of OpenROAD's empty incremental routing state after recover_power.
# Ordinary timing/hold repair, original antenna repair and checks remain enabled.
# Rebuild the current netlist's global route immediately before antenna processing.
if {[llength [info commands ot_qb_original_repair_antennas]] == 0} {
    rename repair_antennas ot_qb_original_repair_antennas
    proc repair_antennas {args} {
        puts "OT_QB_ROUTE_REFRESH: rebuild current global route before unchanged antenna repair"
        global_route -resistance_aware
        estimate_parasitics -global_routing
        uplevel 1 [list ot_qb_original_repair_antennas {*}$args]
    }
}
