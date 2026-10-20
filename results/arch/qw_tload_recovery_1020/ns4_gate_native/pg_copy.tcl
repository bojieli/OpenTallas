set source_db /audit/routes/gate/work/orfs/results/asap7/opentallas_qfd_dv_slice_tload_asap7_ref_gate/base/5_1_grt.odb
read_db $source_db
proc pg_open {} {
 set n 0
 foreach inst [[ord::get_db_block] getInsts] {
  foreach it [$inst getITerms] {
   if {[[$it getMTerm] getSigType] ni {POWER GROUND}} continue
   if {[$it getNet] eq "NULL"} {incr n}
  }
 }
 return $n
}
puts "TLOAD_NATIVE_PG_RAW [pg_open]"
global_connect
puts "TLOAD_NATIVE_PG_AFTER_ORDINARY_GC [pg_open]"
write_db /audit/5_1_grt_gc_copy.odb
exit
