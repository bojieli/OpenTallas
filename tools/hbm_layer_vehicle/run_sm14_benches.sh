#!/usr/bin/env bash
# TOK-FUNC-HBM-SM (10-21): rerun the EXISTING SM / matrix-unit token benches on the HBM d4g r14 die source (RTL-functional,
# source assembly).  One command:
#   run_sm14_benches.sh stage            build SRC (r14 rtl/physical + bundle uniquified masters + this tree's tools/tbs/fixtures)
#                                        locally and rsync SRC + SMW + QKV to STAGE_HOSTS
#   run_sm14_benches.sh run [JOBS...]    unpinned ot-run jobs (--dir REMOTE: only hosts holding the data qualify), wait all
#   run_sm14_benches.sh collect          pull REMOTE/out from STAGE_HOSTS into OUT/out
# RTL = codex/hbm-die14-release-1021 @1fe61477b + the r14sw bundle (BUNDLE: master_files.json / views.json of the r14 vplan_a,
# main ot_hgi_sm_xload_static_cl2.sv overlay, uniquified modules) -- every SM master comes from BUNDLE master_files.json.
# Benches (unchanged compilers / checks):
#   smmv_<L>   sm_mv_unit.py      DS SM.MATVEC every rank-0 record of L00/L02/L14/head, SM ot_hbm_accel_smh_attn at die.v
#                                 parameters #(.ENABLE_INT8(1)) (SM_MV_DIE_INT8=1), sm0 block + all rows
#   smb_pos    smb_unit.py pos    relative SM service bench (tb_hbm_svg_rel_sm: svg ID_COHORT 0, bench PC cfg) -- NOT the die
#                                 composition; kept because the lane lineage ran it
#   ts_<..>    toksim_smhbm.py    die composition as die.v binds one SM: svg #(ID_COHORT 1) -> vmks KRL1 -> 4 x pc_ctrl_leaf_cfg_h9b
#                                 (r14 die.v ctl_SW_p*) -> DRAM timing fixture; xc_rel_t; SM ENABLE_INT8 1.  DS dsA=L00+L02,
#                                 dsB=L14+head; Qwen packed INT8 (narrow, die path) qkv48/o128/gu192/down128 at TP-8 rows
#   qmv_<S>    qwen_sm_mv_unit.py Qwen3-8B real weights (D4G8 capture), narrow INT8 = die params; S = L0 | chain (L1)
#   qi8w_L0    qwen_sm_mv_unit.py --i8w  wide INT8 front: INT8W 1 is NOT bound in r14 die.v (informational)
set -uo pipefail
OUT=${OUT:-/home/ubuntu/scratch/tok-func-hbm/sm14}; REMOTE=${REMOTE:-/srv/opentallas-scratch/claude/tok-func-hbm/sm14}
STAGE_HOSTS=${STAGE_HOSTS:-"ot-gold1 ot-gold2"}; SRC_REV=${SRC_REV:-1fe61477b}
BUNDLE=${BUNDLE:-/home/ubuntu/scratch/tok-func-hbm/r14sw/bundle}
SMW_FROM=${SMW_FROM:-ot-epyc5:/srv/opentallas-scratch/claude/layerbench-hbm/dsfix/smw}
QKV_FROM=${QKV_FROM:-ot-epyc5:/srv/opentallas-scratch/claude/smb-int8/kv/L0}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); MAIN=${MAIN_REPO:-/home/ubuntu/OpenTallas}
MODE=${1:-run}; shift || true
if [ "$MODE" = stage ]; then
  set -e; rm -rf "$OUT/src"; mkdir -p "$OUT/src" "$OUT/smw" "$OUT/qkv" "$OUT/log"
  git -C "$MAIN" archive "$SRC_REV" rtl/hbm_accel rtl/lib rtl/model_ready_hbm_r14 rtl/gpu rtl/hdc rtl/v41rom \
    rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv physical/asap7_memory_macros physical/asap7_memory_macros_v2 \
    | tar -x -C "$OUT/src"
  cp -a "$BUNDLE/rtl/." "$OUT/src/rtl/"; cp -a "$BUNDLE/physical/." "$OUT/src/physical/"
  cp "$BUNDLE/master_files.json" "$BUNDLE/views.json" "$BUNDLE/renames.json" "$OUT/src/"
  git -C "$WT" archive HEAD tools/hbm_layer_vehicle tools/hgi_sim tools/hdc_golden_v41.py tools/hdc_golden.py \
    tools/rtl_gpu_sm_exact.py tools/rtl_hdc_v41_blockdot_campaign.py tools/hbm_svc_packed136_image.py tools/w19_payload_loader.py \
    tools/dshbm_matched_sm_seq.py rtl/test/hbm_accel results/rtl/hbm_ds_layer_tput_1018/fixtures/L00 \
    results/rtl/hbm_ds_layer_tput_1018/fixtures/L02 results/rtl/hbm_ds_layer_tput_1018/fixtures/L14 \
    results/rtl/hbm_ds_layer_tput_1018/fixtures/head results/rtl/hbm_ds_layer_tput_1018/priced_layers.json | tar -x -C "$OUT/src"
  echo "tools=$(git -C "$WT" rev-parse HEAD) rtl=$SRC_REV+r14sw-bundle" > "$OUT/src/REV"
  rsync -a "$SMW_FROM/" "$OUT/smw/"; rsync -a "$QKV_FROM" "$OUT/qkv/"
  for h in $STAGE_HOSTS; do ssh "$h" "mkdir -p $REMOTE/out $REMOTE/log" && rsync -a --delete "$OUT/src" "$OUT/smw" "$OUT/qkv" "$h:$REMOTE/"; done
  echo "STAGED $STAGE_HOSTS:$REMOTE"; exit 0
fi
if [ "$MODE" = collect ]; then
  mkdir -p "$OUT/out"; for h in $STAGE_HOSTS; do rsync -a --exclude 'work*' "$h:$REMOTE/out/" "$OUT/out/" || true; done; exit 0
fi
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
R=$REMOTE; SRCR=$R/src; FIX=$SRCR/results/rtl/hbm_ds_layer_tput_1018/fixtures; L=$OUT/log; mkdir -p "$L"
job() {  # name mem cmd
  local n=$1 m=$2; shift 2
  /home/ubuntu/bin/ot-run --mem "$m" --threads 16 --dir "$R/src" -- bash -c "cd $SRCR && export $VL HDC_V41_ARITH=chunk8 && $* ; echo JOB_RC=\$?" \
    > "$L/$n.log" 2>&1; echo "$(date -Is) DONE $n rc=$? $(grep -E 'JOB_RC|_UNIT|SM_MV_UNIT|verdict|PASS|FAIL' "$L/$n.log" | tail -n 2 | tr '\n' ' ')" >> "$L/summary.log"
}
ts() {   # name layers env...  (toksim die composition; build per host keyed by RTL content, flock'd)
  local n=$1 lay=$2; shift 2
  job "$n" 48 "export $* && mkdir -p $R/work_ts && flock $R/work_ts/build.lock python3 -c 'import sys;sys.argv=[\"x\"];sys.path.insert(0,\"tools/hbm_layer_vehicle\");import toksim_smhbm as T;from pathlib import Path;T.build(Path(\"$R/work_ts\"),None,[])' > $R/out/build_$n.log 2>&1; python3 tools/hbm_layer_vehicle/toksim_smhbm.py run --fix $FIX --smw $R/smw --work $R/work_ts --layers $lay --name $n --out $R/out/$n.json > $R/out/$n.log 2>&1"
}
ALL="smmv_L00 smmv_L02 smmv_L14 smmv_head smb_pos ts_dsA_p200 ts_dsA_p180 ts_dsB_p220 ts_dsB_p240 \
 ts_q_qkv48 ts_q_o128 ts_q_gu192 ts_q_down128 qmv_L0 qi8w_L0"
JOBS=${*:-$ALL}
for j in $JOBS; do
  case "$j" in
    smmv_*) Ly=${j#smmv_}; job "$j" 64 "export SM_MV_DIE_INT8=1 && python3 tools/hbm_layer_vehicle/sm_mv_unit.py run --fixtures $FIX/$Ly --weights $R/smw/$Ly --bundle $SRCR --work $R/work_$j --out $R/out/$j.json > $R/out/$j.log 2>&1" & ;;
    smb_pos) job "$j" 64 "export SMB_PACE_NUM=200 && python3 tools/hbm_layer_vehicle/smb_unit.py run --fix $FIX --smw $R/smw --bundle $SRCR --work $R/work_smb --layers L00:0,L02:2,L14:14,head:0 --name smb_pos --out $R/out/smb_pos.json > $R/out/smb_pos.log 2>&1" & ;;
    ts_dsA_p*) ts "$j" L00:0,L02:2 SMB_PACE_NUM=${j##*_p} & ;;
    ts_dsB_p*) ts "$j" L14:14,head:0 SMB_PACE_NUM=${j##*_p} & ;;
    ts_q_*) s=${j#ts_q_}; tag=${s%%[0-9]*}; rows=${s#$tag}
      for p in ${QPACES:-200 220 260}; do ts "${j}_p$p" qwen:0 TOKSIM_QWEN_MODE=int8 TOKSIM_QWEN_TAGS=$tag TOKSIM_QWEN_R=$tag:$rows SMB_PACE_NUM=$p & done ;;
    qmv_*) S=${j#qmv_}; KV=$R/qkv/$S; LL=0; [ "$S" = chain ] && LL=${QLAYER:-1}
      job "$j" 64 "python3 tools/hbm_layer_vehicle/qwen_sm_mv_unit.py run --kv $KV --L $LL --bundle $SRCR --work $R/work_$j --out $R/out/${j}_pos.json > $R/out/${j}_pos.log 2>&1; python3 tools/hbm_layer_vehicle/qwen_sm_mv_unit.py run --kv $KV --L $LL --bundle $SRCR --work $R/work_$j --all --out $R/out/${j}_all.json > $R/out/${j}_all.log 2>&1" & ;;
    qi8w_L0) job "$j" 48 "python3 tools/hbm_layer_vehicle/qwen_sm_mv_unit.py run --kv $R/qkv/L0 --L 0 --bundle $SRCR --i8w --work $R/work_$j --out $R/out/${j}_pos.json > $R/out/${j}_pos.log 2>&1" & ;;
    *) echo "unknown job $j"; exit 2 ;;
  esac
done
wait
echo "SM14_BENCHES_DONE $(date -Is)" >> "$L/summary.log"
