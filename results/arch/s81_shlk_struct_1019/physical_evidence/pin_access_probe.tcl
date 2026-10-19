# Read-only in-memory probe of actual legal gate placement; no timing exceptions.
read_db $::env(SH_PA_ODB)
set_thread_count 8
pin_access -db_process_node 7 -bottom_routing_layer M2 -top_routing_layer M5 -min_access_points 1 -verbose 1
puts SH_PIN_ACCESS_COMPLETED
exit
