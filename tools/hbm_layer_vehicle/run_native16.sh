#!/usr/bin/env bash
# LB2-HBM-NAT16 (10-18): run the NATIVE TP-192 (16-SM d4g die) DeepSeek-V4.1 programme bit-exact on the fleet.
#   run_native16.sh [REV=HEAD] [LAYERS="0"] [TP=192] [TAG=tp192] [MEM=96] [ROOT=/srv/opentallas-scratch/claude/layerbench-hbm/dsfix]
# Each LAYER entry is one fleet job: "N" = layer N entered from the W17 reference shards; "head" = layer 39 + the LM head.
# Runs tools/hgi_sim/ds_native.py with OT_DS_TP=$TP (w19 compiler head_of placement) on the released-checkpoint subset
# ROOT/ckpt and the committed W17 shards ROOT/refs (results/rtl/hbm_ds_layer_tput_1018/fixtures/w17_ref_ctx1048576_seed20260930),
# and writes ROOT/nat16/out/$TAG/<L>.json (ds_native record: per-region bit-exact verdicts), <L>.prog.json (rank-0 record
# stream, ds_rank0_program schema) and <L>.log.  ot-run picks the host by --dir (only hosts holding ROOT qualify).
set -uo pipefail
REV=${REV:-HEAD}; LAYERS=${LAYERS:-0}; TP=${TP:-192}; TAG=${TAG:-tp$TP}; MEM=${MEM:-96}
ROOT=${ROOT:-/srv/opentallas-scratch/claude/layerbench-hbm/dsfix}; HOST=${HOST:-ot-epyc5}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV")
SRC=$ROOT/nat16/src-${SHA:0:9}; OUT=$ROOT/nat16/out/$TAG
PATHS=""
for p in tools compiler/models docs/HBM_GENERIC_INTERFACE.md results/abi3/deepseek_v41_reduced_v2_reference_oracle_fp8.json \
  results/abi3/qwen3_reduced_reference_oracle.json results/rtl/v41_program_constants.json results/rtl/w17_v41_1m_reference_token.json \
  results/rtl/w19_hbm_tp96_isa.json results/rtl/dshbm_baseline_measured_20261004 results/rtl/dshbm_1m_allmeasured_20261004 \
  results/rtl/hbm_su_c12_20261005 results/arch/hbm_generic_iface_20261009 results/arch/hgi_sim_20261009 rtl/hdc/v41; do
  git -C "$WT" cat-file -e "$SHA:$p" 2>/dev/null && PATHS="$PATHS $p" || echo "run_native16: skip missing $p"
done
if ! ssh "$HOST" "test -f $SRC/REV"; then
  ssh "$HOST" "rm -rf $SRC.tmp && mkdir -p $SRC.tmp" || exit 2
  git -C "$WT" archive "$SHA" $PATHS | ssh "$HOST" "tar -x -C $SRC.tmp && echo $SHA > $SRC.tmp/REV && rm -rf $SRC && mv $SRC.tmp $SRC" || exit 2
fi
ssh "$HOST" "mkdir -p $OUT $ROOT/nat16/sched"
NOAVX="AVX512F AVX512CD AVX512_KNL AVX512_KNM AVX512_SKX AVX512_CLX AVX512_CNL AVX512_ICL AVX512_SPR"
RC=0
for L in $LAYERS; do
  if [ "$L" = head ]; then ARGS="--layers 39 --head"; else ARGS="--layers $L"; fi
  /home/ubuntu/bin/ot-run --mem "$MEM" --threads 2 --dir "$ROOT" -- bash -c "cd $SRC/tools && \
    OT_DS_TP=$TP HDC_V41_ARITH=chunk8 NPY_DISABLE_CPU_FEATURES='$NOAVX' OT_V41_FLASH_SNAPSHOT=$ROOT/ckpt \
    HGI_SCHED_CACHE=$ROOT/nat16/sched /usr/bin/time -v python3 -m hgi_sim.ds_native $ARGS --refs $ROOT/refs \
      --out $OUT/$L.json --program-out $OUT/$L.prog.json > $OUT/$L.log 2>&1; rc=\$?; grep -E '^(L[0-9]+|head) ' $OUT/$L.log | tail -3; \
    grep -E 'Maximum resident|Elapsed' $OUT/$L.log; exit \$rc" &
done
for j in $(jobs -p); do wait "$j" || RC=1; done
exit $RC
