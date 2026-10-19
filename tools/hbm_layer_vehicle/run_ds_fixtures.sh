#!/usr/bin/env bash
# LAYERBENCH-HBM (10-18): generate the DeepSeek-V4.1 per-record layer fixtures (ds_layer_fixtures.py) on the fleet.
#   run_ds_fixtures.sh [REV=HEAD] [LAYERS="0 2 3 14 head"] [RANKS=0] [ROOT=/srv/opentallas-scratch/claude/layerbench-hbm/dsfix]
# Inputs on the host under ROOT: ckpt/ = the sparse released-checkpoint subset of the 1M reference token
# (tools/hgi_sim/ckpt_subset.py, 14.0 GB data; the full 476 GB snapshot is on the workstation only), refs/ = the W17
# reference shards (committed: results/rtl/hbm_ds_layer_tput_1018/fixtures/w17_ref_ctx1048576_seed20260930).  ot-run
# picks the host by --dir (only hosts holding ROOT qualify).  Out: ROOT/fix/<L>/ + ROOT/out/<L>.log.
set -uo pipefail
REV=${REV:-HEAD}; LAYERS=${LAYERS:-0 2 3 14 head}; RANKS=${RANKS:-0}
ROOT=${ROOT:-/srv/opentallas-scratch/claude/layerbench-hbm/dsfix}; HOST=${HOST:-ot-epyc5}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "rm -rf $ROOT/src && mkdir -p $ROOT/src $ROOT/out $ROOT/fix" || exit 2
# archive list = inputs only (hdc_v41x_fullshape_layers.json is a campaign OUTPUT, absent at most revs: its pathspec made
# git archive fail and the host got an empty src/ -- dsfix chain 10-18 09:25).  Every listed path must exist at REV.
PATHS="tools compiler/models docs/HBM_GENERIC_INTERFACE.md results/abi3/deepseek_v41_reduced_v2_reference_oracle_fp8.json
  results/abi3/qwen3_reduced_reference_oracle.json results/rtl/v41_program_constants.json
  results/rtl/w17_v41_1m_reference_token.json results/rtl/w19_hbm_tp96_isa.json results/rtl/dshbm_baseline_measured_20261004
  results/rtl/hbm_ds_layer_tput_1018/priced_layers.json results/arch/hbm_generic_iface_20261009"
for p in $PATHS; do [ -n "$(git -C "$WT" ls-tree -r --name-only "$SHA" -- "$p" | head -1)" ] || { echo "MISSING_AT_REV $p"; exit 2; }; done
# plus every top-level file of results/rtl, results/abi3, results/arch (~66 MB): ds_native reads several (w19_sm_real_ops.json ...)
TOP=$(git -C "$WT" ls-tree --name-only "$SHA" results/rtl/ results/abi3/ results/arch/ | while read -r f; do [ "$(git -C "$WT" cat-file -t "$SHA:$f")" = blob ] && echo "$f"; done)
# plus every results/<a>/<b> entry named in ds_native's cost-model sources (dshbm_1m_allmeasured.su_tables reads
# results/rtl/dshbm_local_chains_20261004/su/..., 10-18 11:55 L0 rc=1); "<dir>/<prefix>_" names expand to the matching dirs.
REFD=$(for f in $(git -C "$WT" ls-tree --name-only "$SHA" tools/dshbm_1m_allmeasured.py tools/hgi_sim/ | grep '\.py$'); do
  git -C "$WT" show "$SHA:$f"; done | grep -oE 'results/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' | sort -u)
EXTRA=$(for d in $REFD; do git -C "$WT" ls-tree --name-only "$SHA" "$(dirname "$d")/" | grep -F "$d"; done | sort -u)
git -C "$WT" archive "$SHA" $PATHS $TOP $EXTRA | ssh "$HOST" "tar -x -C $ROOT/src" || { echo "ARCHIVE_FAIL"; exit 2; }
ssh "$HOST" "test -f $ROOT/src/tools/hbm_layer_vehicle/ds_layer_fixtures.py && test -d $ROOT/refs && test -d $ROOT/ckpt" || { echo "SRC_OR_INPUTS_MISSING on $HOST"; exit 2; }
echo "$SHA" | ssh "$HOST" "cat > $ROOT/src/REV"
NOAVX="AVX512F AVX512CD AVX512_KNL AVX512_KNM AVX512_SKX AVX512_CLX AVX512_CNL AVX512_ICL AVX512_SPR AVX512_SPR"
RC=0
for L in $LAYERS; do
  /home/ubuntu/bin/ot-run --mem ${MEM:-48} --threads 2 --dir "$ROOT" -- bash -c "cd $ROOT/src && \
    HDC_V41_ARITH=chunk8 NPY_DISABLE_CPU_FEATURES='$NOAVX' OT_V41_FLASH_SNAPSHOT=$ROOT/ckpt \
    python3 tools/hbm_layer_vehicle/ds_layer_fixtures.py --layer $L --ranks $RANKS --refs $ROOT/refs --out $ROOT/fix \
      > $ROOT/out/$L.log 2>&1; rc=\$?; tail -2 $ROOT/out/$L.log; exit \$rc" &
done
for j in $(jobs -p); do wait $j || RC=1; done
exit $RC
