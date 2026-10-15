set ::dvm_bank_rebind 1
source /src/physical/ref_tile/qfd_xs_leaf_extcap/local_banks.tcl
detailed_placement
check_placement -verbose
estimate_parasitics -placement
puts "EXTCAP_BANK_REBIND full_cones_legal=1 route_admitted=0"
