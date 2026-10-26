#!/bin/bash
# s8exp on intel2 (scratch2): finish the FACE 3 obj_n12 compile in parallel (copied from intel1 s8exp, 4/32 units done),
# then slice / vec calibrate on the bound slice row.  Same tree / flags as s8cal.sh.
E=/srv/opentallas-scratch2/claude/tok-qw/s8exp; T=$E/tree; W=$E/die
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
t0=$(date +%s)
make -C $W/build/obj_n12 -f Vtb.mk -j 24 -o main2.o -o verilated.o -o verilated_threads.o > $W/build/make2.log 2>&1; echo "make rc=$?" >> $W/build/make2.log
echo "make $(( $(date +%s)-t0 ))" >> $W/timing.txt
[ -x $W/build/obj_n12/Vtb ] || { echo "no Vtb"; exit 3; }
cd $T
export DV2_S8DIE=1 DV_LOWER_VFLAGS="$(cat $W/vflags.txt)"
python3 rtl/test/qwen_dv/dv_lower_bench.py --work $W/build --calibrate > $W/build/slice_calibrate.out 2>&1; echo "rc=$?" >> $W/build/slice_calibrate.out
echo "slicecal $(( $(date +%s)-t0 ))" >> $W/timing.txt
python3 rtl/test/qwen_dv/dv_lower_vec_bench.py --work $W/build --mode calibrate > $W/build/calibrate.out 2>&1; echo "rc=$?" >> $W/build/calibrate.out
echo "veccal $(( $(date +%s)-t0 ))" >> $W/timing.txt
