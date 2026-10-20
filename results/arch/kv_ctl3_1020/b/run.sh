#!/bin/bash
set -e
cd "$(dirname "$(readlink -f "$0")")"
docker run --rm --network none -v $PWD:/work -w /work openroad/orfs:asap7lock bash -c '
B=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
for k in AO INVBUF OA SEQ SIMPLE; do f=$(ls $B/asap7sc7p5t_${k}_RVT_TT_nldm_*lib* | head -1); case $f in *.gz) zcat $f > $k.lib;; *) cp $f $k.lib;; esac; done
export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:$PATH
run(){ TOP=$1 PARAMS="$2" TAG=$3 yosys -q -l syn_$3.log -c syn.tcl >/dev/null 2>&1 || echo "SYN FAIL $3"; }
run qkd_kv_es_fan_root2_b "RCOPIES 32 PH1C 1 S32 1" fanr1 &
run qkd_kv_es_fan_root2_b "RCOPIES 28 PH1C 1 S32 0" fanr0 &
run qkd_kv_die_cfg "NRST 43 CAP 1 PCOPIES 8 S32 1" dcfg1 &
wait'
echo SYN_DONE
