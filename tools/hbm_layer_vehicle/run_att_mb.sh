#!/usr/bin/env bash
# HBM-ATTN-MB (10-19): fleet driver of the multi-block attention calendar campaign (att_mb.py campaign) on the d4g SM
# attention master (Verilator 5.050).  Stages REV's tools + bench into ROOT/src on every HOST (ROOT already holds the
# unit bundle ROOT/bundle and the KV fixtures ROOT/kv/{ds,qwen}), then ONE unpinned ot-run job:
#   run_att_mb.sh REV ROOT [HOSTS="ot-epyc6 ot-epyc9"]
# Output: ROOT/out/<run>/campaign.json + per-run json/log (sweeps, ds/qw base + mb, rl300, mut_* negative controls).
set -uo pipefail
REV=$1; ROOT=$2; HOSTS=${3:-"ot-epyc6 ot-epyc9"}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV"); RUN=${RUN:-$(echo "$SHA" | cut -c1-9)}
for H in $HOSTS; do
  ssh "$H" "mkdir -p $ROOT/src_$RUN $ROOT/out/$RUN && rm -rf $ROOT/src_$RUN/*" || exit 2
  git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hbm_sm_attention tools/hgi_sim tools/hdc_golden_v41.py \
    tools/hdc_golden.py tools/hbm_svc_packed136_image.py rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv | ssh "$H" "tar -x -C $ROOT/src_$RUN" || exit 2
  echo "$SHA" | ssh "$H" "cat > $ROOT/src_$RUN/REV"
done
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
/home/ubuntu/bin/ot-run --mem ${MEM:-128} --threads 32 --dir "$ROOT/src_$RUN" -- bash -c "cd $ROOT/src_$RUN && $VL HDC_V41_ARITH=chunk8 \
  python3 tools/hbm_layer_vehicle/att_mb.py campaign --kv-ds $ROOT/kv/ds --kv-qw $ROOT/kv/qwen --bundle $ROOT/bundle \
  --work $ROOT/work_$RUN --out $ROOT/out/$RUN --jobs 16 > $ROOT/out/$RUN/campaign.log 2>&1; rc=\$?; tail -c 3000 $ROOT/out/$RUN/campaign.log; exit \$rc"
echo "ATT_MB_CAMPAIGN rc=$? out=$ROOT/out/$RUN"
