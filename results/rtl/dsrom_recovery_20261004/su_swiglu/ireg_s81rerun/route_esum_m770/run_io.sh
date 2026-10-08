source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
C=$1; S=${2:-die_io_833.sdc}; L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
D=$(ls -d /work/results/asap7/*/base)
cat > /work/sta833/io_$C.tcl <<T
foreach l [glob $L/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_${C}_nldm_*.lib*] { read_liberty \$l }
read_db $D/6_final.odb
read_spef $D/6_final.spef
read_sdc /work/sta833/$S
report_worst_slack -max
report_worst_slack -min
report_tns
report_checks -path_delay max -endpoint_path_count 1 -format end -slack_max 40 -group_path_count 5000
report_checks -path_delay min -endpoint_path_count 1 -format end -slack_max 15 -group_path_count 5000
T
openroad -exit -no_init -threads 4 /work/sta833/io_$C.tcl
