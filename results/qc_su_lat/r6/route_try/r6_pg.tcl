# QC-SU-BTAB r6: PG binding before DRT (flow-pg-final-1026@eda7910d2 pg_connect.tcl). ODB in env OT_PG_ODB; OT_PG_WRITE=1 writes back.
read_db $::env(OT_PG_ODB)
source /work/so_exact/pg_connect.tcl
puts "OT_PG_PRECHECK rc=[catch {ot_pg_require_bound pre} m] $m"
if {$::env(OT_PG_WRITE) eq "1"} { ot_pg_connect_all pre_drt; ot_pg_require_bound pre_drt; write_db $::env(OT_PG_ODB) }
