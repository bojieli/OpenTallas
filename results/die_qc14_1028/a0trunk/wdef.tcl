read_db /w/cl_nk.odb
set masters {}
foreach i [[ord::get_db_block] getInsts] { dict incr masters [[[$i getMaster] getLib] getName] }
puts "LIBS $masters"
write_def /w/cl_nk.def
