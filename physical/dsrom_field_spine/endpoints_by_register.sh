#!/bin/bash
# endpoints_by_register.sh <orfs dir> <odb stage: 3_place | 4_cts | 5_route | 6_final>: SS (asap7 RVT SS NLDM) setup violations grouped
# by RTL register (placement-estimated parasitics; use for the route loop of physical/dsrom_field_spine/phys.sh).
O=$1; ST=$2
B=$(ls -d $O/results/asap7/*/base); b=${B#$O/}; P=/OpenROAD-flow-scripts/flow/platforms/asap7
SDC=$(ls $B/${ST}.sdc 2>/dev/null || ls $B/3_place.sdc)
cat > $O/pl_ep.tcl <<TCL
foreach l {asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz} { read_liberty $P/lib/NLDM/\$l }
read_db /work/$b/${ST}.odb
read_sdc /work/$b/$(basename $SDC)
source $P/setRC.tcl
estimate_parasitics -placement
report_checks -path_delay max -group_path_count 100000 -endpoint_path_count 1 -slack_max 0 -format end
report_worst_slack -max
TCL
timeout 1500 docker run --rm -v $O:/work openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init -threads 8 /work/pl_ep.tcl" > $O/pl_ep.txt 2>&1
grep "worst slack" $O/pl_ep.txt
grep VIOL $O/pl_ep.txt | sed -E 's#\\##g; s/\[[0-9]+\]//g; s/\$[^ ]*//' | awk '{k=$1; s=$(NF-1); c[k]++; if(!(k in m)||s<m[k])m[k]=s} END{for(k in c)print m[k],c[k],k}' | sort -n | head -25
