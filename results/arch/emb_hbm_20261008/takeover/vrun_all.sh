#!/bin/bash
# usage: vrun_all.sh SU_STG IMG ; builds + runs every variant in parallel (Verilator, 8 build threads each)
R=/srv/opentallas-scratch2/scratch/claude/emb-hbm
SU=$1; IMG=$2
cd $R
sed -i 's/-j 16/-j 8/' vbuild.sh
run() { n=$1; shift; ./vbuild.sh $n -GLINK_STG=72 -GCR=128 -GSU_STG=$SU -GEQ_STG=22 "$@" && ./obj_$n/Vtb_emb_hbm_e2e +dir=$R/$IMG +lat=$R/lat_$n.txt > run_$n.log 2>&1; echo "$n $(grep -h '^PASS\|^FAIL emb' run_$n.log | tail -1)"; }
run base_kv1 -GTWIN=0 -GKVMODE=1 &
run twin_kv1 -GTWIN=1 -GKVMODE=1 &
run base_kv2 -GTWIN=0 -GKVMODE=2 &
run twin_kv2 -GTWIN=1 -GKVMODE=2 &
run base_kv0 -GTWIN=0 -GKVMODE=0 &
run mut_row -GMUT_STRIP=1 &
run mut_scale -GMUT_STRIP=2 &
run mut_ecc -GMUT_STRIP=3 &
run mut_gate -GMUT_GW=4 &
wait
echo ALLDONE
