#!/usr/bin/env bash
# TOK-FUNC-HBM-ATT (10-21): ONE command for the attention + index unit token benches of the HBM d4g release die r14
# (RTL-functional, source assembly).  Positive runs only (the witnesses of these benches are committed by their lanes).
#   run_att14.sh REV BUNDLE OUT HOST
#     REV     tools/tb revision (this branch)          BUNDLE  local r14 bundle (master_files.json, views.json, rtl/, physical/)
#     OUT     remote run root on HOST                   HOST    staging host (ot-run then qualifies hosts holding OUT)
#   ONLY=att|idx|merge and REUSE_STAGE=1 resume selected original cases on existing stage/binaries.
#   env SRC_REV (r14 source, default 1fe61477b = codex/hbm-die14-release-1021) for the IDX / SU sources and their benches;
#       L00_KV (DS T128 L00 ATT capture, TOKSIM-HBM-att) default ot-epyc5:.../dsfix/att_toksim/L00.
# Jobs (ot-run, Verilator 5.050):
#   ds_full   att_images.py unit, DS L0 / L2 / L14 (run_att_unit.sh pos): every SM QK+PV op bit-exact on the r14
#             ot_hbm_accel_smh_attn master (bundle master_files.json, views.json env DEFINES + params ENABLE_INT8 1)
#   ds_s32    the same with --subrun 32 (run_att_gap.sh part A: the d4g resident-programme sub-run calendar), L2 / L14,
#             then part B (att_merge_su.py vectors on the L2 RTL nodes -> tb_su_static_arithmetic on the r14 SU
#             arithmetic sources, die lane MLAT 4 / ALAT 3 / LEAF 1 = su_SW0 contract params) -- base run only
#   qwen      qwen_att_unit.py run, stage L0:L0 and chain:L1 (run_qwen_att_unit.sh pos)
#   idx       rtl/test/toksim_idxdma: topk_r14_fix (DS L0/L2/L14 route.top6 fixture records) + topk_r14 (random) on
#             hb_idx__ctl = ot_hbm_idx_rootctl_static_am #(SEL_LAT 30, VM_RT 65, CR_RT 36); run_banklat_idx.sh PASS cases
#             topk / n12_ctl / n12_dir (op n12 VM_RT_EXTRA 171 behind the root share) on the r14 sources
set -uo pipefail
STATUS=0
REV=$1; BUN=$2; OUT=$3; H=$4; SRC_REV=${SRC_REV:-1fe61477b}; LOGD=${LOGD:-$HOME/scratch/tok-func-hbm/att14}; mkdir -p "$LOGD"
L00_KV=${L00_KV:-ot-epyc5:/srv/opentallas-scratch/claude/layerbench-hbm/dsfix/att_toksim/L00}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV"); SRC=$(git -C "$WT" rev-parse "$SRC_REV")
DSF=results/rtl/hbm_ds_layer_tput_1018
ONLY=${ONLY:-all}
if [ "${REUSE_STAGE:-0}" != 1 ]; then
ssh "$H" "mkdir -p $OUT/src $OUT/r14src $OUT/bundle $OUT/kv $OUT/out $OUT/.fleet-ready && rm -rf $OUT/src/* $OUT/r14src/*" || exit 2
git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hbm_sm_attention tools/hgi_sim tools/hdc_golden_v41.py tools/hdc_golden.py \
  tools/hbm_svc_packed136_image.py tools/hbm_static rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv rtl/test/toksim_idxdma \
  $DSF/veh_att_1019/kv $DSF/fixtures/L00 $DSF/fixtures/L02 $DSF/fixtures/L14 results/rtl/hbm_qwen_layer_tput_1018/veh_att3_1019/kv \
  | ssh "$H" "tar -x -C $OUT/src" || exit 2
git -C "$WT" archive "$SRC" rtl/hbm_accel rtl/hdc rtl/proto rtl/lib rtl/gpu rtl/test/hbm_idx_static physical/asap7_memory_macros \
  physical/asap7_memory_macros_v2 physical/hbm_generic/argmax18/rtl physical/hbm_mtp/rtl tools/hbm_idx_static_query_vectors.py tools/hdc_golden_v41.py tools/hdc_golden.py \
  | ssh "$H" "tar -x -C $OUT/r14src" || exit 2
git -C "$WT" archive "$SHA" rtl/test/toksim_idxdma | ssh "$H" "tar -x -C $OUT/r14src" || exit 2
echo "$SHA" | ssh "$H" "cat > $OUT/src/REV"; echo "$SRC" | ssh "$H" "cat > $OUT/r14src/REV"
rsync -a --delete "$BUN/rtl" "$BUN/physical" "$BUN/master_files.json" "$BUN/views.json" "$H:$OUT/bundle/" || exit 2
ssh "$H" "cp -a $OUT/src/$DSF/veh_att_1019/kv/L02 $OUT/src/$DSF/veh_att_1019/kv/L14 $OUT/kv/ && mkdir -p $OUT/kv/L00" || exit 2
ssh "${L00_KV%%:*}" "tar -c -C ${L00_KV#*:} ." | ssh "$H" "tar -x -C $OUT/kv/L00" || exit 2
fi
QKV=$OUT/src/results/rtl/hbm_qwen_layer_tput_1018/veh_att3_1019/kv
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
A="cd $OUT/src && export $VL HDC_V41_ARITH=chunk8 && python3 tools/hbm_layer_vehicle/att_images.py unit --kv $OUT/kv --bundle $OUT/bundle"
Q="cd $OUT/src && export $VL HDC_V41_ARITH=chunk8 && python3 tools/hbm_layer_vehicle/qwen_att_unit.py run --kv $QKV --bundle $OUT/bundle"
# An exact unique lane-root alias selects only hosts holding this staged input.
# The fleet runner requires this directory to exist before placement.
FLEET_LANE=${FLEET_LANE:-/srv/opentallas-scratch/claude/tok-hbm-att-$(basename "$OUT")}
ssh "$H" "test -d $FLEET_LANE || ln -s $OUT $FLEET_LANE" || exit 2
RUN="/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir $FLEET_LANE --"
stage_job() { printf '%s\n' "$2" | ssh "$H" "cat > $OUT/$1.sh"; }
P1=; P2=; P3=; P4=
# one build dir (obj_d0_p0 / obj_d0_p1) per job; the first op of each job builds it
J_FULL=""; for L in 0 2 14; do
  J_FULL="$J_FULL $A --layer $L --work $OUT/w_full --out $OUT/out/ds_L${L}_full.json > $OUT/out/ds_L${L}_full.log 2>&1; r=\$?; echo DS_L${L}_FULL_RC \$r; test \$r = 0 || exit \$r;"; done
if [ "$ONLY" = all ] || [ "$ONLY" = att ]; then
stage_job job_ds_full "$J_FULL"
$RUN bash "$OUT/job_ds_full.sh" > "$LOGD/ds_full.otrun.log" 2>&1 &
P1=$!
fi
J_S32=""; for L in 2 14; do
  J_S32="$J_S32 $A --layer $L --subrun 32 --work $OUT/w_s32 --out $OUT/out/ds_L${L}_s32.json > $OUT/out/ds_L${L}_s32.log 2>&1; r=\$?; echo DS_L${L}_S32_RC \$r; test \$r = 0 || exit \$r;"; done
if [ "$ONLY" = all ] || [ "$ONLY" = att ]; then
stage_job job_ds_s32 "$J_S32"
$RUN bash "$OUT/job_ds_s32.sh" > "$LOGD/ds_s32.otrun.log" 2>&1 &
P2=$!
fi
J_Q="$Q --stage L0 --L 0 --work $OUT/w_q --out $OUT/out/qw_L0_L0.json > $OUT/out/qw_L0_L0.log 2>&1; r=\$?; echo QW_L0_RC \$r; test \$r = 0 || exit \$r; \
$Q --stage chain --L 1 --work $OUT/w_q --out $OUT/out/qw_chain_L1.json > $OUT/out/qw_chain_L1.log 2>&1; r=\$?; echo QW_CHAIN_RC \$r; test \$r = 0 || exit \$r"
if [ "$ONLY" = all ] || [ "$ONLY" = att ]; then
stage_job job_qwen "$J_Q"
$RUN bash "$OUT/job_qwen.sh" > "$LOGD/qwen.otrun.log" 2>&1 &
P3=$!
fi
FIX="$OUT/src/$DSF/fixtures/L00,$OUT/src/$DSF/fixtures/L02,$OUT/src/$DSF/fixtures/L14"
J_I="cd $OUT/r14src && export $VL && export FIXDIRS=$FIX && \
for c in topk_r14_fix topk_r14; do bash rtl/test/toksim_idxdma/run_toksim_idxdma.sh $OUT/out/idx \$c > $OUT/out/idx_\$c.log 2>&1; r=\$?; echo IDX_\${c}_RC \$r; test \$r = 0 || exit \$r; done; \
for c in topk n12_ctl n12_dir; do bash rtl/test/hbm_idx_static/run_banklat_idx.sh $OUT/out/banklat \$c > $OUT/out/banklat_\$c.log 2>&1; r=\$?; echo BANKLAT_\${c}_RC \$r; test \$r = 0 || exit \$r; done"
if [ "$ONLY" = all ] || [ "$ONLY" = idx ]; then
stage_job job_idx "$J_I"
/home/ubuntu/bin/ot-run --mem 32 --threads 8 --dir "$FLEET_LANE" -- bash "$OUT/job_idx.sh" > "$LOGD/idx.otrun.log" 2>&1 &
P4=$!
fi
[ -z "$P2" ] || wait "$P2" || STATUS=1
# SU merge (run_att_gap.sh part B, base run) on the L2 s32 RTL nodes, r14 SU arithmetic sources
NODES=$OUT/out/ds_L2_s32.nodes.npz
M="cd $OUT/src && export $VL && set -e; mkdir -p $OUT/merge; \
python3 tools/hbm_layer_vehicle/att_merge_su.py vectors --nodes $NODES --out $OUT/merge/vec_pos > $OUT/merge/vec_pos.log; \
nops=\$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))[\"nops\"])' $OUT/merge/vec_pos/programme.json); \
cd $OUT/r14src; d=rtl/hbm_accel/generic/adapters/static_su; \
\$VERILATOR --binary --timing --hierarchical -O1 -j 8 -CFLAGS -O0 -Wno-fatal --top-module tb_su_static_arithmetic \
 -GNOPS=\$nops -GMLAT=4 -GALAT=3 -GLEAF=1 --Mdir $OUT/merge/obj \
 \$d/arithmetic/ot_hbm_su_static_ins.sv \$d/arithmetic/ot_hbm_su_static_lane.sv \$d/arithmetic/ot_hbm_su_static_arithmetic.sv \
 \$d/arithmetic/tb_su_static_arithmetic.sv \$d/data_store/ot_hbm_su_static_data_store.sv \$d/data_store/ot_hbm_su_static_pinned_bank.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv \
 rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > $OUT/merge/build.log 2>&1; \
set +e; $OUT/merge/obj/Vtb_su_static_arithmetic +DIR=$OUT/merge/vec_pos > $OUT/merge/pos.log 2>&1; r=\$?; echo MERGE_POS_RC \$r; test \$r = 0 || exit \$r; \
grep -h 'SU_ARITH' $OUT/merge/pos.log | cut -c1-300"
if { [ "$ONLY" = all ] || [ "$ONLY" = att ] || [ "$ONLY" = merge ]; } && timeout 120 ssh "$H" "python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))[\"summary\"][\"verdict\"]==\"PASS\" else 1)' $OUT/out/ds_L2_s32.json"; then
  stage_job job_merge "$M"
  /home/ubuntu/bin/ot-run --mem ${MEM_SU:-400} --threads 8 --dir "$FLEET_LANE" -- bash "$OUT/job_merge.sh" > "$LOGD/merge.otrun.log" 2>&1 || STATUS=1
else echo "MERGE SKIPPED (DS L2 s32 not PASS)" > "$LOGD/merge.otrun.log"; fi
for pid in "$P1" "$P3" "$P4"; do [ -z "$pid" ] || wait "$pid" || STATUS=1; done
grep -h "_RC \|RAN on\|NOT RUN\|SKIPPED" "$LOGD"/*.otrun.log
echo "ATT14_DONE rc=$STATUS"
exit "$STATUS"
