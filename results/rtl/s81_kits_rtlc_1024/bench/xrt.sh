#!/bin/bash
cd /srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes
export PATH=$HOME/.local/opentallas-tools/bin:$PATH J=8
B=/srv/opentallas-scratch/claude/rtlc_bench/xrt
run(){ n=$1; shift; ( "$@" > $B/$n.txt 2>&1; echo "rc=$?" >> $B/$n.txt ) & }
mkdir -p $B
run le_h0 bash tools/s81_slice/xrt_land_eq.sh $B/le_h0 0 1 1 20000 none
run le_h1 bash tools/s81_slice/xrt_land_eq.sh $B/le_h1 1 1 2 20000 none
run le_h0s env SPARSE=1 bash tools/s81_slice/xrt_land_eq.sh $B/le_h0s 0 1 3 20000 none
run le_h1_citwin bash tools/s81_slice/xrt_land_eq.sh $B/le_h1_citwin 1 1 2 20000 citwin
run le_h0_fpin env SPARSE=1 bash tools/s81_slice/xrt_land_eq.sh $B/le_h0_fpin 0 1 3 20000 fpin
run xb_h0 bash tools/s81_slice/xrt_bench.sh $B/xb_h0 base 1 0
run xb_h1 bash tools/s81_slice/xrt_bench.sh $B/xb_h1 base 1 1
run xb_h1_citwin bash tools/s81_slice/xrt_bench.sh $B/xb_h1_citwin citwin 1 1
wait
