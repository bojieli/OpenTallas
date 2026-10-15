# Resize inserts data buffers after GPL. Rebind the actual full bank cones
# before CTS, then legalize and check them; never credit stale group labels.
set ::dvm_bank_rebind 1
source /src/physical/ref_tile/qfd_xs_leaf_banked/local_banks.tcl
source /src/physical/ref_tile/qfd_xs_leaf_banked/fill_restore_local.tcl
detailed_placement
check_placement -verbose
estimate_parasitics -placement
puts "BANK_REBIND before_CTS full_data_cones_legalized=1 route_admitted=0"
