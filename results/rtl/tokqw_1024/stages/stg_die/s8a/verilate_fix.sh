#!/bin/bash
# TOK-QK/S8A: verilate (C++ generation only, no compile) the 12-slice bound s8 row tb_qfd_dv2 FACE 3 from the s8exp tree
# with the FIXED qfd_dv_s8_suvm_rp1 (dd2d80455), same command as s8exp_wf3/dbg s8wf3_chain.sh, then diff the generated C++
# against the s8exp_wf3 what-if obj_n12 with comments / file:line markers removed.  Identical -> the wf3 binary is the
# fixed RTL's binary and its stg_die run is adopted of record.
set -u
A=/srv/opentallas-scratch2/claude/tok-qw/s8a; E=/srv/opentallas-scratch2/claude/tok-qw/s8exp; X=/srv/opentallas-scratch2/claude/tok-qw/s8exp_wf3
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
t0=$(date +%s)
[ -d $A/tree ] || cp -al $E/tree $A/tree
rm -f $A/tree/rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv; cp $A/src/qfd_dv_s8_suvm_rp1.sv $A/tree/rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv
sha1sum $A/tree/rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv $E/tree/rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv
cd $A/tree
export DV2_S8DIE=1 DV_LOWER_VFLAGS="$(cat $E/die/vflags.txt)"
SRCS=$(python3 -c 'import sys; sys.path.insert(0,"rtl/test/qwen_dv"); import dv_bench2 as B2; print(" ".join(B2.SRCS2))')
mkdir -p $A/v12
verilator --cc --exe -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --top-module tb_qfd_dv2 \
  --prefix Vtb -GMUT=0 -GN=12 -Mdir $A/v12/obj_n12 rtl/test/qwen_dv/main2.cpp $SRCS $DV_LOWER_VFLAGS > $A/v12/verilate.log 2>&1
echo "verilate rc=$? $(( $(date +%s)-t0 )) s" | tee -a $A/timing.txt
