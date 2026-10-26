read_db $::env(OT_PG_ODB)
source /work/so_exact/pg_connect.tcl
set c [dict create]
foreach i [[ord::get_db_block] getInsts] { set o [ot_pg_open_terms $i]; if {$o} { regsub {[0-9_]+$} [$i getName] {} p; set p [string range $p 0 11]; dict incr c "$p dt=[$i isDoNotTouch]" $o } }
dict for {k v} $c { puts "OT_PG_CENSUS $k $v" }
