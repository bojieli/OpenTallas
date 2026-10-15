read_db /work/capture_localize_before_DPL.odb
set_thread_count 2
detailed_placement
check_placement -verbose
write_db /work/capture_localize_legal.odb
puts "CAPTURE_RESTORE_LOCAL_LEGAL placement_only=1 route_qualified=0"
