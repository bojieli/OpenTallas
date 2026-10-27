# QC-SU-F4D probe 2: the kit hook pair (pre_drt_f4d.tcl / post_drt_f4d.tcl) on the F4C rp1 5_1_grt DB, DRT 6 iterations
set_thread_count 16
read_db $::env(ODB)
source /work/pre_drt_f4d.tcl
detailed_route -output_drc /out/drc2.rpt -verbose 0 -droute_end_iter 6
source /work/post_drt_f4d.tcl
write_db /out/5_2_route_probe2.odb
