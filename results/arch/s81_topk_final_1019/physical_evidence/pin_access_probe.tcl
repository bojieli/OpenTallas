# Actual legal placement read-only native pin-access probe. No routing/timing waiver.
read_db $::env(PA_ODB)
set_thread_count 8
set_routing_layers -signal M2-M5 -clock M2-M5
pin_access -db_process_node 7 -min_access_points 1 -verbose 1
puts TOPK_PIN_ACCESS_COMPLETED
exit
