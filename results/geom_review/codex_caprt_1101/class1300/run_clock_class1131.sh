#!/bin/bash
set -euo pipefail
K=$(realpath "$1")
docker run --rm --name codex-caprt-class-$(basename "$K")-$$ --cpus=4 --memory=8g --memory-swap=8g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -e OT_CORNER=TT -e OT_POSTCTS_GRT=1 -e ODB=/work/run/results/asap7/kl_ot_s81sl_cap_rt_m5tall_balanced3/base/5_1_grt.odb -e OUTDIR=/work/class_placed -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
rc=0
openroad -threads 4 -exit /work/clock_class_place.tcl || rc=$?
if [ "$rc" = 0 ]; then cp /work/class_placed/4_cts.odb /work/run/results/asap7/kl_ot_s81sl_cap_rt_m5tall_balanced3/base/4_cts.odb;cp /work/class_placed/4_cts.sdc /work/run/results/asap7/kl_ot_s81sl_cap_rt_m5tall_balanced3/base/4_cts.sdc;fi
chown -R "$HUID:$HGID" /work
exit "$rc"
' > "$K/run_clock_class1131.log" 2>&1
