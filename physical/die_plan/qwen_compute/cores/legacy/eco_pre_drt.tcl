# Reload the actual incremental routing result, not reconstructed/fabricated clock guides.
# OpenROAD have_routes cannot lazily restore DB guides when any fixed clock net
# lacks guides. The saved segment file comes from this ECO's end_incremental.
set routes $::env(RESULTS_DIR)/eco_global_route.segments
if {![file isfile $routes] || [file size $routes] == 0} {
  error "QC_ECO FAIL: missing nonempty incremental global-route segments $routes"
}
read_global_route_segments $routes
if {![grt::have_routes]} {
  error "QC_ECO FAIL: saved incremental segments did not restore global routes"
}
puts "QC_ECO restored exact incremental global-route segments $routes"
