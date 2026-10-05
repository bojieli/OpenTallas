set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_SS_*.lib*]] { read_liberty $f }
set B /work/orfs/results/asap7/opentallas_ot_qwen_tp_seq_async_ctx_w12_asap7_qasp_f4/base
read_db $B/5_1_grt.odb
read_sdc $B/5_1_grt.sdc
source $P/setRC.tcl
estimate_parasitics -placement
report_checks -path_delay max -group_path_count 3 -endpoint_path_count 1 -digits 3
