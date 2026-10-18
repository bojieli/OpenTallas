#!/bin/bash
# LB2-QWEN-C 10-18: Q-SLICE slice2 benches (bench_r2.sh set) on this lane's RTL (level-9 idle fix 2092dfebe)
D=/srv/opentallas-scratch/claude/lb2qc-1018; cd $D/src || exit 9
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
W=$D/slice2_bench; rm -rf $W; mkdir -p $W
B=rtl/test/qwen_dv/dv_bench2.py
python3 $B a b c d e f g i j --work $W > $W/pos.out 2>&1 &
python3 $B i --mut 11 --work $W > $W/mut11.out 2>&1 &
python3 $B j --mut 12 --work $W > $W/mut12.out 2>&1 &
FS=$(python3 -c "import sys; sys.path.insert(0,'rtl/test/qwen_dv'); import dv_bench2 as B; print(' '.join(s for s in B.SRCS2 if 'tb_' not in s))")
for m in 0 11 12; do
  ( verilator --binary -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
      --top-module tb_qfd_dv2_faces -GMUT=$m -Mdir $W/faces_m$m $FS rtl/qwen_dv/qfd_dv_slice2_faces.sv \
      rtl/test/qwen_dv/tb_qfd_dv2_faces.sv > $W/faces_build_m$m.log 2>&1 && $W/faces_m$m/Vtb_qfd_dv2_faces > $W/faces_m$m.out 2>&1 ) &
done
wait
python3 $B h --work $W/h > $W/pos_h.out 2>&1 &
python3 $B h --mut 10 --work $W > $W/mut10.out 2>&1 &
wait
for f in pos pos_h mut10 mut11 mut12 faces_m0 faces_m11 faces_m12; do echo "== $f"; cat $W/$f.out; done
