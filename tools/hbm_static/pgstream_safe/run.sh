#!/bin/bash
# Same actual parent lockstep and seam checker, with regional bridge candidate.
set -euo pipefail
cd "$(dirname "$0")/../../.."
out=$(realpath -m "$1"); mut=${2:-0}; qid=${3:-1}; rr=${4:-18}; wr=${5:-15}
mkdir -p "$out"
S=rtl/hbm_accel/generic/adapters/static_su
verilator --version | tee "$out/version.txt"
verilator --binary --timing -j "${OT_THREADS:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN \
 --top-module tb_hbm_su_pg_stream_regional -GMUT="$mut" -GEDGES=1500 -GQID="$qid" -GREAD_RETURN="$rr" -GWRITE_RETURN="$wr" -GFAULT_REG=1 \
 --Mdir "$out/obj" -o pgs \
 rtl/lib/ot_rst_relay.sv "$S/ot_hbm_su_static_vm_ports.sv" "$S/ot_hbm_su_static_vm_bank_leaf_s.sv" \
 "$S/programme/multirate_bridge.sv" "$S/programme/multirate_bridge_split.sv" "$S/programme/multirate_bridge_regional.sv" \
 "$S/top/ot_hbm_su_static_pg_lg_tap.sv" "$S/top/ot_hbm_su_static_pg_stream.sv" "$S/top/ot_hbm_su_static_pg_stream_regional.sv" \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv \
 rtl/hdc/ot_hdc_delay.sv rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_regional.sv > "$out/build.log" 2>&1
"$out/obj/pgs" | tee "$out/bench.log"
