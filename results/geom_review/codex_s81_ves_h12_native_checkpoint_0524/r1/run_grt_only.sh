#!/bin/bash
# OWN VEs reviewed one-pass GRT-only checkpoint. No DRT/filler/finish/STA/LEC.
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-ves-h12-prep-0524/pass_m12_r1
IMAGE=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
MEM=32
THREADS=8
cd "$K"
test ! -e run_native_grt.log
test ! -e run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base/5_1_grt.odb
test "$(realpath "$K/run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base/INPUT_ROUTED/6_final.odb")" = "$K/baseline/6_final.odb"
sha256sum -c FROZEN_INPUTS.sha256
docker run --rm --name ves-h12-native-grt-r1-0524 --memory="${MEM}g" --memory-swap="${MEM}g" --cpus="$THREADS" -v "$K":/work -v "$K/baseline":/work/baseline:ro -w /OpenROAD-flow-scripts/flow -e OT_PG_STRICT=1 -e OT_CLK_FREEZE=1 -e OT_MAX_BUFFER_PERCENT=5 -e NUM_CORES="$THREADS" "$IMAGE" bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -u
set -a
source /work/variant.env
set +a
export OT_PRD_PASS=1 OT_PRD_NO_HOLD=0
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1
python3 -I /work/private_runtime_prepare.py --expected /work/FROZEN_RUNTIME.json /OpenROAD-flow-scripts/flow/scripts
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$NUM_CORES" do-5_1_grt CORNER=TC "CORNERS=tc bc" SKIP_INCREMENTAL_REPAIR=1
' > "$K/run_native_grt.log" 2>&1
B=/work/run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base
docker run --rm --memory=16g --memory-swap=16g --cpus=2 -v "$K":/work -e VES_SAVED_ODB="$B/5_1_grt.odb" -e RESULTS_DIR="$B" "$IMAGE" bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -no_init -threads 2 -exit /work/post_saved_checks.tcl
' > "$K/saved_checks.log" 2>&1
python3 -I "$K/clk_geom_diff.py" "$K/run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base/source_wire_pre.tsv" "$K/post_wire.tsv" --json "$K/source_wire_diff.json"
python3 -I "$K/clk_geom_diff.py" "$K/run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base/clk_freeze_pre.tsv" "$K/post_wire.tsv" --json "$K/clock_reset_frozen_diff.json"
sha256sum -c FROZEN_INPUTS.sha256
printf 'GRT_CHECKPOINT_ONLY_RC0 %s\nDRT_FILL_FINISH_HELD\n' "$(date -Is)" > "$K/status"
