#!/bin/bash
# TOK-QK/S8 10-24 WHAT-IF (diagnostic, NOT the bound RTL of record): the bound s8 die slice row (tb_qfd_dv2 FACE 3) with
# ONE change: qfd_dv_s8_suvm_rp1 starts the closed SU8 (qfd_dv_s5_su8_rst3) 3 edges after the PROG read request
# (dbg/src/whatif_suvm_d3.sv), i.e. the candidate fix for FAIL finding S8-SU-PROG-ALIGN (SU8 accepts si at su_cmd+5,
# the vm8q_rp1/s8x_prog PROG word reaches its pin register at su_cmd+8).  Purpose: find the NEXT defects of the bound row
# (slice/vec/mat calibrate, stg pos family) in parallel with the QC fix.  C++ at -O0 (build time; same Verilog).
set -u
E=/srv/opentallas-scratch2/claude/tok-qw/s8exp; X=/srv/opentallas-scratch2/claude/tok-qw/s8exp_wf3
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p $X/die/build $X/stgdie; t0=$(date +%s)
[ -d $X/tree ] || cp -a $E/tree $X/tree
cp $E/dbg/src/whatif_suvm_d3.sv $X/tree/rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv
cp $E/die/vflags.txt $X/die/vflags.txt; ln -sfn $E/stgdie/fx $X/stgdie/fx
cd $X/tree
export DV2_S8DIE=1 DV_LOWER_VFLAGS="$(cat $X/die/vflags.txt)"
if [ ! -x $X/die/build/obj_n12/Vtb ]; then
  SRCS=$(python3 -c 'import sys; sys.path.insert(0,"rtl/test/qwen_dv"); import dv_bench2 as B2; print(" ".join(B2.SRCS2))')
  verilator --cc --exe -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --top-module tb_qfd_dv2 \
    --prefix Vtb -GMUT=0 -GN=12 -Mdir $X/die/build/obj_n12 rtl/test/qwen_dv/main2.cpp $SRCS $DV_LOWER_VFLAGS > $X/die/build/verilate.log 2>&1
  echo "verilate rc=$? $(( $(date +%s)-t0 )) s" >> $X/timing.txt
  make -C $X/die/build/obj_n12 -f Vtb.mk -j 16 OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0 > $X/die/build/make.log 2>&1
  echo "make rc=$? $(( $(date +%s)-t0 )) s" >> $X/timing.txt
fi
[ -x $X/die/build/obj_n12/Vtb ] || { echo "no Vtb"; exit 3; }
python3 rtl/test/qwen_dv/dv_lower_bench.py --work $X/die/build --calibrate > $X/die/build/slice_calibrate.out 2>&1; echo "rc=$?" >> $X/die/build/slice_calibrate.out
cp $X/die/build/cal.log $X/die/build/slice_cal.log 2>/dev/null
echo "slicecal $(( $(date +%s)-t0 )) s" >> $X/timing.txt
python3 rtl/test/qwen_dv/dv_lower_vec_bench.py --work $X/die/build --mode calibrate > $X/die/build/calibrate.out 2>&1; echo "rc=$?" >> $X/die/build/calibrate.out
echo "veccal $(( $(date +%s)-t0 )) s" >> $X/timing.txt
grep -q "^rc=0" $X/die/build/slice_calibrate.out && grep -q "^rc=0" $X/die/build/calibrate.out || { echo "WHAT-IF CAL FAIL"; tail -12 $X/die/build/slice_calibrate.out $X/die/build/calibrate.out; exit 6; }
bash $E/stage_stg_die.sh $X $E/stg_result.json $E/pos_runlist.txt --par 24
echo "stgdie $(( $(date +%s)-t0 )) s" >> $X/timing.txt
