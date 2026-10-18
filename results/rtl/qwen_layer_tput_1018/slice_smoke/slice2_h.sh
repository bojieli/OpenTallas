#!/bin/bash
# LB2-QWEN-C 10-18: Q-SLICE bench h (12-slice SETID chain) + MUT 10 on this lane's RTL (the remainder of slice2_bench.sh;
# the combined run's scope was OOM-stopped at 96 GB during the two parallel 12-slice builds)
D=/srv/opentallas-scratch/claude/lb2qc-1018; cd $D/src || exit 9
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
W=$D/slice2_bench; B=rtl/test/qwen_dv/dv_bench2.py
rm -rf $W/h $W/m10
python3 $B h --work $W/h > $W/pos_h.out 2>&1; /usr/bin/time -f "%e s %M KB" -a -o $W/h_time.txt true
python3 $B h --mut 10 --work $W > $W/mut10.out 2>&1
for f in pos_h mut10; do echo "== $f"; cat $W/$f.out; done
