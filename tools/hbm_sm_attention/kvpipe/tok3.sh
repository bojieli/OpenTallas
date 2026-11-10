#!/bin/bash
# DIE-HBM-97 KVPIPE rev3 real-token check (same fixture + controls as tok.sh) (DO_NOT_COUNT until reviewed): Qwen L0 attention fixture (VEH-ATT3 golden
# capture) through the die master with the KVPIPE kv_line (in its face shell) + compensated attn_front_static.
# Pass run, then 4 controls that must FAIL by golden mismatch / schedule fault; then the synthetic bench set.
R=/srv/opentallas-scratch2/claude/die-hbm-97-kvpipe-run
cd $R/src_tok3 || exit 2
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator HDC_V41_ARITH=chunk8 VL_JOBS=4
O=$R/out_tok3; mkdir -p $O
KV=$R/src_tok3/results/rtl/hbm_qwen_layer_tput_1018/veh_att3_1019/kv
U=tools/hbm_layer_vehicle/qwen_att_unit.py
B=$R/bundle_kvp3
sha256sum $KV/L0/att_kv.json $KV/L0/att_kv.npz > $O/fixture.sha256; cat $KV/L0/capture.log >> $O/fixture.sha256
run() { n=$1; shift; echo "=== $n $(date)"; env "$@" > $O/$n.log 2>&1; echo "RC $n $?"; tail -n 1 $O/$n.log | cut -c1-600; }
CAL=$R/w_tok3/pass/calib_L0_L0.json
CTL="--sms 0 --blocks 0 --calib $CAL"
run tok_pass     KV_SHELL=1 python3 -I $U run --kv $KV --stage L0 --L 0 --bundle $B --work $R/w_tok3/pass --out $O/tok_pass.json --jobs 8
run tok_skew_m1  KV_SHELL=1 KV_SKEW=-1 python3 -I $U run --kv $KV --stage L0 --L 0 --bundle $B --work $R/w_tok3/pass --out $O/tok_skew_m1.json $CTL
run tok_skew_p1  KV_SHELL=1 KV_SKEW=1 python3 -I $U run --kv $KV --stage L0 --L 0 --bundle $B --work $R/w_tok3/pass --out $O/tok_skew_p1.json $CTL
run tok_dmut2    KV_SHELL=1 python3 -I $U run --kv $KV --stage L0 --L 0 --bundle $B --work $R/w_tok3/pass --out $O/tok_dmut2.json --dmut 2 $CTL
run tok_uncomp   KV_SHELL=1 ATT_UNIT_DEFINES=OT_KVLINE_UNCOMP python3 -I $U run --kv $KV --stage L0 --L 0 --bundle $B --work $R/w_tok3/pass --out $O/tok_uncomp.json $CTL
# late-side slack sweep (rev2: KV_SKEW=+1 PASSED = the late side is slack, not a failing control): first late shift
# that fails = the schedule's late margin + 1
for k in 2 3 4 6 8; do
run tok_skew_p$k  KV_SHELL=1 KV_SKEW=$k python3 -I $U run --kv $KV --stage L0 --L 0 --bundle $B --work $R/w_tok3/pass --out $O/tok_skew_p$k.json $CTL
done
echo KVPIPE_TOK3_DONE

