read_db /input.odb
source /work/die_repeaters.tcl
source /work/ctrl_corner400.tcl
set rc [s81_ctrl_corner_repair /work/tcl_out3/ctrl_corner]
write_db /work/tcl_out3/repaired.odb
if {$rc != 0} {exit 5}
