#!/usr/bin/env bash
# LB2-HBM-CQW (10-18): run qwen_layer_images.py snap (HGI functional model over the D4G8 fixtures -> operands + images
# + SW-slice replay) on the fleet host that holds the verified fixture copy.
#   run_qwen_images.sh [REV=HEAD] [STAGES="L0 chain head"] [RANKS=0,5]
#     [ROOT=/srv/opentallas-scratch/claude/layerbench-hbm/qfix_archive]   (ROOT/fix/<stage> = regen_fixtures.sh output)
# ot-run picks the host by --dir (only the host holding ROOT qualifies).  Out: ROOT/cqw/out/ (copy back + commit).
set -uo pipefail
REV=${REV:-HEAD}; STAGES=${STAGES:-L0 chain head}; RANKS=${RANKS:-0,5}
ROOT=${ROOT:-/srv/opentallas-scratch/claude/layerbench-hbm/qfix_archive}; HOST=${HOST:-ot-epyc5}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "rm -rf $ROOT/cqw/src $ROOT/cqw/out && mkdir -p $ROOT/cqw/src $ROOT/cqw/out $ROOT/cqw/log" || exit 2
git -C "$WT" archive "$SHA" tools results/rtl/hbm_qwen_layer_tput_1018 results/rtl/hbm_ds_layer_tput_1018/slice_sw \
  results/arch/hbm_generic_iface_20261009 rtl/hbm_accel/generic/adapters rtl/hdc/v41x \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v | ssh "$HOST" "tar -x -C $ROOT/cqw/src"
echo "$SHA" | ssh "$HOST" "cat > $ROOT/cqw/src/REV"
RC=0
for S in $STAGES; do
  /home/ubuntu/bin/ot-run --mem ${MEM:-24} --threads 2 --dir "$ROOT" -- bash -c "cd $ROOT/cqw/src && \
    PYTHONPATH=tools python3 -m hbm_layer_vehicle.qwen_layer_images snap --stage $S --ranks $RANKS --fix $ROOT/fix/$S \
      --out $ROOT/cqw/out > $ROOT/cqw/log/$S.log 2>&1; rc=\$?; tail -c 1500 $ROOT/cqw/log/$S.log; exit \$rc" &
done
for j in $(jobs -p); do wait $j || RC=1; done
exit $RC
