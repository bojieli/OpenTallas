read_db /work/run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base/6_final.s8b_archive.odb
foreach m [[ord::get_db] getLibs] { foreach x [$m getMasters] { if {[string match ot_sram* [$x getName]]} { puts "MASTER [$x getName] [expr {[$x getWidth]/1000.0}] x [expr {[$x getHeight]/1000.0}]" } } }
source /work/pg_connect.tcl
set b [ord::get_db_block]
set before 0; foreach i [$b getInsts] { incr before [ot_pg_open_terms $i] }
puts "V1PG open_before=$before"
set rep [ot_pg_connect_all dqc55_prog_v1]
puts "V1PG repaired_insts=$rep"
ot_pg_require_bound dqc55_prog_v1
write_db /work/run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base/6_final.odb
puts V1PG_DONE
