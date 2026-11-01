#!/bin/bash
set -euo pipefail
K=$(realpath "$1"); NAME=codex-caprt-relocate-A40R-$$
docker run --rm --name "$NAME" --cpus=4 --memory=8g --memory-swap=8g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -e OT_CORNER=TT -e OT_POSTCTS_GRT=1 -e ODB=/work/run/results/asap7/kl_ot_s81sl_cap_rt_m5tall_balanced3/base/5_1_grt.odb -e OUTDIR=/work/relocation_out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
rc=0
openroad -threads 4 -exit /work/A40_driver_relocate.tcl || rc=$?
if [ "$rc" = 0 ]; then
cp /work/relocation_out/5_1_grt.odb /work/run/results/asap7/kl_ot_s81sl_cap_rt_m5tall_balanced3/base/5_1_grt.odb
cp /work/relocation_out/5_1_grt.sdc /work/run/results/asap7/kl_ot_s81sl_cap_rt_m5tall_balanced3/base/5_1_grt.sdc
fi
chown -R "$HUID:$HGID" /work
exit "$rc"
' > "$K/relocate.log" 2>&1
