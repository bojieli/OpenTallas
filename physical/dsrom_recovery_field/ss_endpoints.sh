#!/bin/bash
# SS (asap7 RVT SS NLDM) setup endpoints of a routed screen: every violating register D pin, its slack, for grouping
# by RTL register (new PQ logic vs inherited pinned-spine structure).   ss_endpoints.sh <orfs dir> <out.txt>
O=$(readlink -f $1); OUT=$2
B=$(ls -d $O/results/asap7/*/base); b=${B#$O/}
P=/OpenROAD-flow-scripts/flow/platforms/asap7
cat > $O/ss_ep.tcl <<TCL
foreach l {asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz} { read_liberty $P/lib/NLDM/\$l }
read_db /work/$b/6_final.odb
read_sdc /work/$b/6_final.sdc
read_spef /work/$b/6_final.spef
report_checks -path_delay max -group_path_count 100000 -endpoint_path_count 1 -slack_max 0 -format end
TCL
docker run --rm -v $O:/work openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init -threads 8 /work/ss_ep.tcl" > $OUT 2>&1
