#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TASK_OUT=${OUT:-/tmp/qdq-fr-pin-capture}
TASK_MUT_ORDER=${MUT_ORDER:-0}
TASK_MUT_END=${MUT_END:-0}
TASK_VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[[ -x "$TASK_VERILATOR" ]] || TASK_VERILATOR=verilator
mkdir -p "$TASK_OUT"
cd "$TASK_ROOT"
"$TASK_VERILATOR" --binary --timing -Wno-fatal -j 4 --top-module tb_hgi_qdq_fr_pin_capture \
 -GMUT_ORDER="$TASK_MUT_ORDER" -GMUT_END="$TASK_MUT_END" --Mdir "$TASK_OUT/obj" \
 rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/ot_hgi_quant_record.sv \
 rtl/hbm_accel/generic/qw/ot_hgi_qdq_fr.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_fr_one_payload.sv \
 rtl/hbm_accel/generic/qw/ot_hgi_qdq_fr_capture_retire.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_fr_pin_capture.sv \
 rtl/test/hbm_accel/generic/tb_hgi_qdq_fr_pin_capture.sv > "$TASK_OUT/build.log" 2>&1
set +e
"$TASK_OUT/obj/Vtb_hgi_qdq_fr_pin_capture" > "$TASK_OUT/sim.log" 2>&1
TASK_RC=$?
set -e
cat "$TASK_OUT/sim.log"
exit "$TASK_RC"
