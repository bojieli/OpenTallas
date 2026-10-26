#!/usr/bin/env bash
# LAYERBENCH-HBM (10-18): regenerate the Qwen D4G8 golden fixtures (L0 / chain / head) from the COMMITTED generator
# (tools/hbm_qwen_layer/qwen_d4g_proof.py at REV) and verify every file / expected array byte-for-byte against the
# COMMITTED manifests results/rtl/hbm_qwen_layer_tput_1018/fixtures/manifest_<stage>.json.
#   regen_fixtures.sh [REV=HEAD] [STAGES="L0 chain head"] [ROOT=/srv/opentallas-scratch/claude/layerbench-hbm/qfix]
# Data locality: the Qwen3-8B snapshot (b968826d9c46...) + torch exist only on ot-pve1, so ot-run selects the host by
# --dir (only ot-pve1 holds ROOT), not by a pinned host.  The quantised image cache is rebuilt from the snapshot in a
# FRESH cache dir (no reuse of the TOKEN-PASS-HBMQ cache).  Logs -> ROOT/out/<stage>.{log,verify.log,json}.
set -uo pipefail
REV=${REV:-HEAD}; STAGES=${STAGES:-L0 chain head}
ROOT=${ROOT:-/srv/opentallas-scratch/claude/layerbench-hbm/qfix}; HOST=${HOST:-ot-pve1}
SNAP=${SNAP:-/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "rm -rf $ROOT/src $ROOT/fix $ROOT/img && mkdir -p $ROOT/src $ROOT/out $ROOT/img" || exit 2
git -C "$WT" archive "$SHA" tools compiler results/arch/hbm_generic_iface_20261009 results/rtl/hbm_qwen_layer_tput_1018/fixtures | ssh "$HOST" "tar -x -C $ROOT/src"
echo "$SHA" | ssh "$HOST" "cat > $ROOT/src/REV"
for S in $STAGES; do
  /home/ubuntu/bin/ot-run --mem 16 --threads 2 --dir "$ROOT" -- bash -c "cd $ROOT/src && \
    python3 tools/hbm_qwen_layer/qwen_d4g_proof.py --snapshot $SNAP --cache $ROOT/img --stage $S --dump $ROOT/fix \
      --out $ROOT/out/$S.json > $ROOT/out/$S.log 2>&1; \
    python3 tools/hbm_qwen_layer/verify_fixtures.py --dir $ROOT/fix/$S \
      --manifest results/rtl/hbm_qwen_layer_tput_1018/fixtures/manifest_$S.json > $ROOT/out/$S.verify.log 2>&1; \
    rc=\$?; tail -1 $ROOT/out/$S.verify.log; exit \$rc"
  RC=$((${RC:-0} | $?))
done
exit ${RC:-0}
