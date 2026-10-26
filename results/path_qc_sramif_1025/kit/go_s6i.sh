#!/bin/bash
# PATH-QC-SRAMIF vmr_s6i (ot-run job): vmr_s6h kit + RTL MIF=1 (per-bank pre-decoded read landing regs, +1 read/+1 write)
# -> synth/floorplan/place (pre_gpl_s5.tcl: face flops + macro_pin_flops OT_MPF_TREE/SHARED, unchanged) -> keep check ->
# CTS + GRT (s6h mscts spec + per-tap corr, unchanged) -> FF-only GRT hold (hold_s6.sh, margin 0) -> F6 dump.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); IMAGE=openroad/orfs:asap7lock
HB=$(echo $K/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base)
echo "go_s6i start $(date -Is) host $(hostname)" >> "$K/image.txt"
"$K/run_kit.sh" "$K" place 32 16; rc=$?
echo "go_s6i place rc $rc $(date -Is)" >> "$K/image.txt"; [ $rc = 0 ] || exit $rc
python3 -I "$K/keep_check.py" "$K" > "$K/keep_check.txt" 2>&1; rc=$?; cat "$K/keep_check.txt"
[ $rc = 0 ] || { echo "go_s6i KEEP_CHECK FAIL" >> "$K/image.txt"; exit 7; }
docker run --rm --name sramif-vmr-s6i-cg-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-cts do-5_1_grt; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > "$K/run_cg.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "go_s6i cts/grt rc $rc $(date -Is)" >> "$K/image.txt"; [ $rc = 0 ] || exit $rc
cp "$HB/5_1_grt.odb" "$HB/5_1_grt_prehold.odb"; cp "$HB/route.guide" "$HB/route_prehold.guide"
OT_S6_HOLD_MARGIN=0 "$K/hold_s6.sh"; rc=$?
echo "go_s6i hold rc $rc $(date -Is)" >> "$K/image.txt"
"$K/f6_dump.sh" "$K" 3_place > "$K/f6_place.log" 2>&1
"$K/f6_dump.sh" "$K" 5_1_grt > "$K/f6_grt.log" 2>&1
exit $rc
