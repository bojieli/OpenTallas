# LAYERBENCH-QWEN smoke campaign (TOK.QW.BENCH.3): cut + smoke every slice; results under $F/smoke/<name>
. /srv/opentallas-scratch/claude/layerbench-qwen-1018/env.sh
T=$F/tools/qwen_layerbench; set -u
GR='qfd_(rly|rlyh|rlyh0|land|landh|landh0)_.*|qfd_rst_rep(_p8)?'
OVR='tt_ctlm:XPF_TRANSPORT_EDGES=26:DIE GAP dv2f14bn GEN leaves XPF_TRANSPORT_EDGES at -1 (RTL $error); 26 = hr pin register + 25 relays n_dvw_hr_wi__r25, smoke only, compiler must assign'
CX=$CSRC/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv
[ -f $F/img_ctl/img/program.memh ] || bash $CSRC/rtl/test/qwen_split/run_sys_face_bench.sh $F/img_ctl 1 > $F/img_ctl.log 2>&1
$CUT --die-v $CDIE --bind $CBIND --src $CSRC --master 'qfd_(tt_ctlm_dv|sys_face)' --grow "$GR" --top qwc_slice_ctl --out $F/out/c_ctl
$CUT --die-v $CDIE --bind $CBIND --src $CSRC --master 'qfd_(tt_ctlm_dv|sys_face)' --grow "$GR" --top qwc_slice_ctl --override "$OVR" --out $F/out/c_ctl_x
$CUT --die-v $KDIE --bind $KBIND --src $KSRC --master 'qkd_kvs_ctl' --grow 'qkd_rlys_.*|qkd_rst_region' --top qwk_slice_ctl --out $F/out/k_ctl
$CUT --die-v $CDIE --bind $CBIND --src $CSRC --inst 'dvs_W5|c16_W5_[0-3]' --grow "$GR" --top qwc_slice_colW5 --out $F/out/c_colW5
$CUT --die-v $KDIE --bind $KBIND --src $KSRC --master 'qkd_kvs_attn' --grow 'qkd_rlys_.*|qkd_rst_region' --top qwk_slice_attn --out $F/out/k_attn
D="+define+SMOKE_IMG=\"$F/img_ctl/img\""
mkdir -p $F/smoke
export SMOKE_UNRESET_OK="o_n_dvw_hr_wi__r25|o_n_ng_tt_native_cmd_0"   # compute ctl: ME program-store RAM words before any programme load (see record)
( BENCH_FILES="$CX" BENCH_DEFS="$D" bash $T/run_smoke.sh $F/out/c_ctl $F/smoke/c_ctl_asis $T/drive_qwc_slice_ctl.svh 0 +OT_ROM_DIR=$F/img_ctl/img > $F/smoke/c_ctl_asis.out 2>&1 ) &
( BENCH_FILES="$CX" BENCH_DEFS="$D" bash $T/run_smoke.sh $F/out/c_ctl_x $F/smoke/c_ctl_xpf $T/drive_qwc_slice_ctl.svh 0 +OT_ROM_DIR=$F/img_ctl/img > $F/smoke/c_ctl_xpf.out 2>&1 ) &
( BENCH_FILES="$CX" BENCH_DEFS="$D +define+SMOKE_COMP_AUTH=2" bash $T/run_smoke.sh $F/out/c_ctl_x $F/smoke/c_ctl_xpf_comp2 $T/drive_qwc_slice_ctl.svh 0 +OT_ROM_DIR=$F/img_ctl/img > $F/smoke/c_ctl_xpf_comp2.out 2>&1 ) &
( bash $T/run_smoke.sh $F/out/c_ctl_x $F/smoke/c_ctl_xpf_idle - 0 +OT_ROM_DIR=$F/img_ctl/img > $F/smoke/c_ctl_xpf_idle.out 2>&1 ) &
( bash $T/run_smoke.sh $F/out/k_attn $F/smoke/k_attn - 0 > $F/smoke/k_attn.out 2>&1 ) &
( bash $T/run_smoke.sh $F/out/k_attn $F/smoke/k_attn_m1 - 1 > $F/smoke/k_attn_m1.out 2>&1 ) &
wait
for f in $F/smoke/*.out; do echo "== $(basename $f .out)"; grep -E "SMOKE_RESULT|SMOKE_BUILD_FAIL|RESET_DET |%Error" $f | head -4; done
( bash $T/run_smoke.sh $F/out/k_ctl $F/smoke/k_ctl - 0 > $F/smoke/k_ctl.out 2>&1 ) ; for f in $F/smoke/k_ctl.out; do grep -E 'SMOKE_RESULT|RESET_DET ' $f; done
# compute column (needs > 96 GB to verilate): bash $T/run_smoke.sh $F/out/c_colW5 $F/smoke/c_colW5 - 0  (ot-run --mem 300)
