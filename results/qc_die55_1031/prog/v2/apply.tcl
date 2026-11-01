read_db /work/src_5_2.odb
source /work/$::env(OT_MOVE)
detailed_placement
check_placement -verbose
write_db /work/$::env(OT_OUTDB)
source /work/geom_dump.tcl
puts APPLY_DONE
