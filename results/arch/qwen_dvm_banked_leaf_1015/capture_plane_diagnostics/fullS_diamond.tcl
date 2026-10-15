read_db /work/fullS_before_DPL.odb
set_thread_count 2
detailed_placement -use_diamond_legalizer
check_placement -verbose
write_db /work/fullS_legal.odb
puts "FULL_S_CAPTURE_HOLD_READ_CONTROL_LEGAL placement_only=1 routed_qualified=0"
