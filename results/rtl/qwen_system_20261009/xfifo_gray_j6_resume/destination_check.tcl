set plat /OpenROAD-flow-scripts/flow/platforms/asap7
set corner $::env(AUDIT_CORNER)
foreach group {AO INVBUF OA SEQ SIMPLE} {
 set lib [lindex [glob $plat/lib/NLDM/asap7sc7p5t_${group}_RVT_${corner}_nldm_*] 0]
 read_liberty $lib
}
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/3_place.odb
read_sdc $base/3_place.sdc
source /src/physical/qwen_die_masters/signoff/qfd_io_xfifo_gray_cdc.tcl
exit
