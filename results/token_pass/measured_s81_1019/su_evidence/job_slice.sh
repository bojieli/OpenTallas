#!/usr/bin/env bash
# TOKSIM-S81/SU: slice SU benches on the RELEASE source 19bf4121e: leaf (L0/L2), vs (L0), beat (L0/L2), norm16 xfin/slice, slice_eng, leaf_eng, hcpl
S=/srv/opentallas-scratch/claude/toksim-s81-su
W=$S/src_slice; rm -rf $W; mkdir -p $W && tar xf $S/src_slice.tar -C $W || exit 1
O=$S/out_slice; rm -rf $O; mkdir -p $O; cd $W || exit 1
echo "HOST $(hostname) start $(date) src 19bf4121e"; $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --version
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH J=4
run() { local n=$1; shift; ( "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt ) & }
run leaf_L0  bash tools/s81_slice/leaf_bench.sh $O/leaf_L0 0 L0
run leaf_L2  bash tools/s81_slice/leaf_bench.sh $O/leaf_L2 0 L2
run vs_L0    bash tools/s81_slice/vs_bench.sh $O/vs_L0 0 L0
run beat_L0  bash tools/s81_slice/beat_bench.sh $O/beat_L0 base 37 L0
run beat_L2  bash tools/s81_slice/beat_bench.sh $O/beat_L2 base 37 L2
run xfin16   bash tools/s81_dv/norm16_bench.sh $O/xfin16 base xfin
run norm16   bash tools/s81_dv/norm16_bench.sh $O/norm16 base slice
run leaf_eng bash tools/s81_slice/leaf_eng_bench.sh $O/leaf_eng 0 7
run hcpl     bash tools/s81_slice/hcpl_bench.sh $O/hcpl both
wait; for f in $O/*.txt; do echo "== $f"; cat $f; done
echo "HOST $(hostname) done $(date)"
