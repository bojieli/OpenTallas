#!/bin/bash
# QC-A0 10-24: run one A0 ref_tile kit's route + sign-off STA + view export outside the (old-fleet) closure loop, with
# the loop's route env for this job spec (route_corner TC, route_hold_corners mm, HM 0.03, tt_overlay, CTS fix hooks,
# io_ref_routed FF hold reference) -- the job.json "route" + "collect" commands verbatim, placeholders filled.
#   usage: run_a0_route.sh SRC RUN KIT_DIR(physical/ref_tile/<kit>) LABEL [NC]
set -uo pipefail
SRC=$(realpath "$1"); RUN=$2; K=$3; LABEL=$4; NC=${5:-16}
CL=$RUN/cl; mkdir -p "$CL" "$RUN/routes"; RUN=$(realpath "$RUN"); CL=$RUN/cl
cd "$SRC"
echo "$(date -Is) start $(git rev-parse HEAD) kit=$K nc=$NC host=$(hostname)" >> "$RUN/RUN.log"
cp physical/common_flow/io_ref_routed.sdc "$CL/"
echo '{"calibrate": "disabled"}' > "$CL/calib.json"
export HM=0.03 OT_ORFS_CORNER=TC OT_ROUTE_HOLD_CORNERS=mm
python3 tools/closure_loop/hold_corners_patch.py "$SRC" >> "$RUN/RUN.log" 2>&1 || { echo "hold_corners_patch rc=$?" >> "$RUN/RUN.log"; exit 3; }
mkdir -p .ot_mm && cp "$CL/io_ref_routed.sdc" .ot_mm/ff_ioref_last.sdc
export OT_TTB_CORNER_MARK=$CL/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py "$SRC" >> "$RUN/RUN.log" 2>&1 || exit 4
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'
export OT_ORFS_CORNER_OVERRIDE=TC
HM=0.03 OT_MM_FF_SDC="$K/signoff.sdc" SRC=$SRC OT_PIN_GROUP_MAX=32 NC=$NC bash tools/ref_tile/ref_route.sh "$K/kit.env" "$LABEL" "$RUN/routes"
rc=$?
echo "$(date -Is) route rc=$rc" >> "$RUN/RUN.log"
B=$(basename "$K"); TOP=$(sed -n 's/^TOP=//p' "$K/kit.env")
MV=(); for m in $(python3 -c "import json;print(' '.join(json.load(open('$K/job.json'))['verdict']['macros']))"); do MV+=(--macro-view "$m"); done
mkdir -p "$RUN/record/route" "$RUN/record/views"
cp "$RUN/routes/$LABEL/corner_sta.json" "$RUN/routes/$LABEL/status" "$RUN/routes/$LABEL/STATUS" "$RUN/routes/$LABEL/signoff.sdc" "$RUN/record/route/" 2>/dev/null
[ $rc = 0 ] && python3 tools/ref_tile/ref_tile.py export --orfs-dir "$RUN/routes/$LABEL/work/orfs" --kit "$K" --out "$RUN/record/views/$TOP" "${MV[@]}" > "$RUN/record/route/export.log" 2>&1
echo "$(date -Is) done rc=$rc export=$?" >> "$RUN/RUN.log"
exit $rc
