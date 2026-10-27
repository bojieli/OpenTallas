#!/bin/bash
# KV-RTL-MODDUP benches (post-fix tree W; pre-fix stream bench uses the saved old ot_qkvd_kv_desc.sv)
set -u
W=/srv/opentallas-scratch2/claude/wt/kv-rtl-moddup-1027; D=/srv/opentallas-scratch2/claude/kv-rtl-moddup-1027
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; export VERILATOR=$V JOBS=4
cd $W
S=$D/strip; mkdir -p $S
( bash physical/qkd_ctrl_strip/bench.sh pc $S/pc 0 > $S/pc.res 2>&1; echo "rc=$?" >> $S/pc.res ) &
( bash physical/qkd_ctrl_strip/bench.sh pc $S/pcm1 1 > $S/pcm1.res 2>&1; echo "rc=$?" >> $S/pcm1.res ) &
( bash physical/qkd_ctrl_strip/bench.sh kc $S/kc 0 > $S/kc.res 2>&1; echo "rc=$?" >> $S/kc.res ) &
( bash physical/qkd_ctrl_strip/bench.sh kc $S/kcm1 1 > $S/kcm1.res 2>&1; echo "rc=$?" >> $S/kcm1.res ) &
# kv plan leaf PC benches (subset of the generated run.sh)
L=$D/leaves; mkdir -p $L
{ sed -n '1,/^job() /p' rtl/test/kv_plan_leaves_1023/run.sh; grep -E '^job (qkd_kvs_pc_h_head_p|qkd_static_kv_pc_path_fan_nc_b_head_p)_' rtl/test/kv_plan_leaves_1023/run.sh; echo wait; } > $L/run_sub.sh
( bash $L/run_sub.sh $L/out 6 > $L/run.log 2>&1 ) &
# stream bench SELF=1 (issuer -> FIFO -> relays -> 32 taps), KV-die consumer mode; pre vs post fix, + issuer mutants
SB=$D/stream; mkdir -p $SB
sb() { tag=$1 desc=$2; shift 2
  $V --binary --timing -Wno-fatal -Wno-WIDTH -j 4 --top-module tb_hbm_stream_bw --Mdir $SB/obj_$tag "$@" \
    rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv \
    $desc rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv \
    rtl/test/model_ready_hbm_r14/tb_hbm_stream_bw.sv > $SB/$tag.build.log 2>&1 || { echo BUILD_FAIL > $SB/$tag.log; return; }
  grep -c MODDUP $SB/$tag.build.log > $SB/$tag.moddup
  $SB/obj_$tag/Vtb_hbm_stream_bw > $SB/$tag.log 2>&1; echo "rc=$?" >> $SB/$tag.log; rm -rf $SB/obj_$tag; }
P="-GSELF=1 -GCONS=1 -GWR_EN=1 -GWSETP=0"
NEW=rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_desc.sv; OLD=$D/pre_kv_desc.sv
sb post $NEW $P & sb pre $OLD $P & sb post_dmut1 $NEW $P -GDMUT=1 & sb post_dmut3 $NEW $P -GDMUT=3 &
sb post_plain $NEW &
wait
echo ALLDONE > $D/done
