# Refresh the copied child interface after its actual CTS tree exists.
# Deliberately no legacy median/midrange link-budget hook.
if {[info procs clock_tree_synthesis] eq ""} { error "ENGC CTS command unavailable" }
rename clock_tree_synthesis ot_engc_child_mean_cts
proc clock_tree_synthesis {args} {
    ot_engc_child_mean_cts {*}$args
    estimate_parasitics -placement
    read_sdc /src/physical/s81_engc_tiles/rso_closure/child_mean.sdc
}
