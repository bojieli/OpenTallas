#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")"
docker run --rm --network none -v $PWD:/work -w /work openroad/orfs:asap7lock bash -c '
B=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
for k in AO INVBUF OA SEQ SIMPLE; do f=$(ls $B/asap7sc7p5t_${k}_RVT_TT_nldm_*lib* | head -1); case $f in *.gz) zcat $f > $k.lib;; *) cp $f $k.lib;; esac; done
export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:$PATH
TOP=qkd_kvs_ctl_s32 PARAMS="CTLSRAM 1" TAG=t32 yosys -q -l syn_t32.log -c syn.tcl >/dev/null 2>&1 || echo "SYN FAIL t32"'
python3 hf.py out_t32.v > fanout.txt 2>&1
echo SYN_DONE
