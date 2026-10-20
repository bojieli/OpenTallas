#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")"
docker run --rm --network none -v $PWD:/work -w /work openroad/orfs:asap7lock bash -c '
B=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
for k in AO INVBUF OA SEQ SIMPLE; do f=$(ls $B/asap7sc7p5t_${k}_RVT_TT_nldm_*lib* | head -1); case $f in *.gz) zcat $f > $k.lib;; *) cp $f $k.lib;; esac; done
export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:$PATH
P="MUT 0 DIECFG 1 NRST 43 LINKCFG 1 ESCFG 1 DIECAP 1 MU 1 WMUT 0 SRQ 2"
run(){ TOP=$1 PARAMS="$2" TAG=$3 yosys -q -l syn_$3.log -c syn.tcl >/dev/null 2>&1 || echo "SYN FAIL $3"; }
run qkd_static_kv_boot_dispatch_mu_s32 "$P" s32 &
run qkd_static_kv_boot_dispatch_mu "$P" orig &
wait'
for t in s32 orig; do echo "== $t"; python3 hf.py out_$t.v; done > fanout.txt 2>&1
echo SYN_DONE
