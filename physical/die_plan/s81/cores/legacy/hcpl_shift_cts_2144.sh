#!/bin/bash
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd)
R=$K/run/results/asap7/kl_ot_dsrom_su_hcpost_lane_pr_v1b/base
sha256sum "$R/1_2_yosys.v" "$R/3_place.odb" "$R/3_place.sdc" > "$K/frozen_before.sha256"
docker run --rm --name codex-hcpl-shiftcts-2144 --memory=16g --memory-swap=16g --cpus=8 -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
M=(make -o synth -o place DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8)
for f in /work/run/results/asap7/kl_ot_dsrom_su_hcpost_lane_pr_v1b/base/1* /work/run/results/asap7/kl_ot_dsrom_su_hcpost_lane_pr_v1b/base/2* /work/run/results/asap7/kl_ot_dsrom_su_hcpost_lane_pr_v1b/base/3* /work/run/results/asap7/kl_ot_dsrom_su_hcpost_lane_pr_v1b/base/clock_period.txt; do M+=(-o "$f"); done
"${M[@]}" cts
chown -R 1000:1000 /work
' > "$K/cts_trial.log" 2>&1
sha256sum --check "$K/frozen_before.sha256" > "$K/frozen_after_check.txt"
