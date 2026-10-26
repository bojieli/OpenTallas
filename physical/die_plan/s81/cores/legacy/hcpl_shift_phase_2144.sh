#!/bin/bash
# Separate fresh-corner stages; no route/finish entry point.
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd)
PHASE=${1:?place, cts, ff, or grt required}
NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' "$K/config.mk")
[ -n "$NICK" ]
R=$K/run/results/asap7/$NICK/base
case "$PHASE" in
 place) exec bash "$K/run_original.sh" "$K" place "${2:-16}" "${3:-8}" ;;
 cts|ff|grt) ;;
 *) echo "HCPL_SHIFT no route/finish; current die/flow review still required" >&2; exit 3 ;;
esac
if [ "$PHASE" = cts ]; then
 [ ! -f "$R/4_cts.odb" ]
 sha256sum "$R/1_2_yosys.v" "$R/3_place.odb" "$R/3_place.sdc" > "$K/shift_frozen_before.sha256"
fi
if [ "$PHASE" = grt ]; then
 [ ! -f "$R/5_1_grt.odb" ]
 python3 "$K/shift_timing_guard.py" "$K/shift_postff_TT.log" "$K/shift_postff_FF.log"
 cp "$R/4_cts.odb" "$R/4_cts_shift_preff.odb"
 cp "$K/shift_ff/repair_ff.odb" "$R/4_cts.odb"
fi
docker run --rm --name "hcpl-shift-$PHASE-$$" --memory="${2:-16}g" --memory-swap="${2:-16}g" --cpus="${3:-8}" -e PHASE="$PHASE" -e NICKNAME="$NICK" -e SHIFT_THREADS="${3:-8}" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
R=/work/run/results/asap7/$NICKNAME/base
if [ "$PHASE" = ff ]; then
 export PLIBS="$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_FF_*.lib*)"
 export ODB=$R/4_cts.odb SDC=/work/constraint.sdc FF_SDC=/work/shift_ff_vclk.sdc RCFILE=/work/setRC_rcx.tcl OUT_DIR=/work/shift_ff OT_HOLD_FF_MARGIN=5
 openroad -exit -no_init /work/repair_ff.tcl
else
 M=(make -o synth -o place DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$SHIFT_THREADS)
 for f in "$R"/1* "$R"/2* "$R"/3* "$R"/clock_period.txt; do M+=(-o "$f"); done
 if [ "$PHASE" = grt ]; then M+=(-o cts);for f in "$R"/4*; do M+=(-o "$f"); done;fi
 "${M[@]}" "$PHASE"
fi
chown -R 1000:1000 /work
' > "$K/shift_${PHASE}.log" 2>&1
if [ "$PHASE" = cts ]; then sha256sum --check "$K/shift_frozen_before.sha256"; fi
if [ "$PHASE" = ff ] || [ "$PHASE" = grt ]; then
 if [ "$PHASE" = ff ]; then ODB=/work/shift_ff/repair_ff.odb;TAG=postff;else ODB=/work/run/results/asap7/$NICK/base/5_1_grt.odb;TAG=postgrt;fi
 for C in TT FF; do
 docker run --rm --name "hcpl-shift-audit-$TAG-$C-$$" --memory=8g --memory-swap=8g --cpus=4 -e C="$C" -e ODB="$ODB" -e OT_SHIFT_STAGE="$TAG" -v "$K":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/audit_shift_clock.tcl' > "$K/shift_${TAG}_${C}.log" 2>&1
 done
 python3 "$K/shift_timing_guard.py" "$K/shift_${TAG}_TT.log" "$K/shift_${TAG}_FF.log"
fi
