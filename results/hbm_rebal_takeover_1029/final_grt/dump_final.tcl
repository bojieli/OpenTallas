read_db /work/run/results/asap7/hbc_hnx_lane_x/base/5_1_grt.odb
set ::env(OT_GEOM_OUT) /work/final_grt_geom.tsv
source /work/geom_dump.tcl
check_placement -verbose
