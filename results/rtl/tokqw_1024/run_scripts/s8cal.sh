#!/bin/bash
# s8exp: FACE 3 build + slice / vec calibrate on the bound slice row
E=$HOME/ot-scratch/tok-qw/r1024/s8exp; T=$E/tree; W=$E/die
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd $T
export DV2_S8DIE=1 DV_LOWER_VFLAGS="-GMU_NU=4 $(python3 tools/qwen_tokfunc/s8die_srcs.py $T)"
mkdir -p $W/build; echo "$DV_LOWER_VFLAGS" > $W/vflags.txt
t0=$(date +%s)
python3 rtl/test/qwen_dv/dv_lower_bench.py --work $W/build --calibrate > $W/build/slice_calibrate.out 2>&1; echo "rc=$?" >> $W/build/slice_calibrate.out
echo "build+slicecal $(( $(date +%s)-t0 ))" >> $W/timing.txt
python3 rtl/test/qwen_dv/dv_lower_vec_bench.py --work $W/build --mode calibrate > $W/build/calibrate.out 2>&1; echo "rc=$?" >> $W/build/calibrate.out
echo "veccal $(( $(date +%s)-t0 ))" >> $W/timing.txt
