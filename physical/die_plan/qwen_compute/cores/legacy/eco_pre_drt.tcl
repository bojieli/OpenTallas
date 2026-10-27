# Reload the actual incremental routing result, not reconstructed/fabricated clock guides.
# OpenROAD have_routes cannot lazily restore DB guides when any fixed clock net
# lacks guides. The saved segment file comes from this ECO's end_incremental.
set routes $::env(RESULTS_DIR)/eco_global_route.segments
if {![file isfile $routes] || [file size $routes] == 0} {
  error "QC_ECO FAIL: missing nonempty incremental global-route segments $routes"
}
# OpenROAD 6cb3f2b704 writes zero-length placeholder segments, but its own
# reader rejects them (GRT-0264). They contain no wire/via; retain the raw file
# and omit only records whose complete (x,y,layer) endpoints are identical.
set in [open $routes r]
set clean ${routes}.nonzero
set out [open $clean w]
set omitted 0
while {[gets $in line] >= 0} {
  set fields [regexp -all -inline {\S+} $line]
  if {[llength $fields] == 6 && [lrange $fields 0 2] eq [lrange $fields 3 5]} {
    incr omitted
    continue
  }
  puts $out $line
}
close $in
close $out
puts "QC_ECO zero-length placeholders omitted=$omitted; raw segments retained=$routes"
read_global_route_segments $clean
if {![grt::have_routes]} {
  error "QC_ECO FAIL: saved incremental segments did not restore global routes"
}
puts "QC_ECO restored exact incremental global-route segments $routes"
