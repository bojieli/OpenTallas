#!/bin/bash
# TW3-PGSTREAM 10-19: one-root split ot_hbm_su_static_pg_stream_split (pg_stream_q + pg_stream_s over the banked seam)
# lockstep vs the current two-root ot_hbm_su_static_pg_stream + seam calendar window checker (tb_hbm_su_pg_stream_split),
# Verilator (the closure daemon pins 5.050; ot-heavy puts it first on PATH).
# usage: su_pg_stream_split_vl_run.sh OUT [MUT] [EDGES] [QID] [READ_RETURN] [WRITE_RETURN]
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}; edges=${3:-1500}; qid=${4:-1}; rr=${5:-10}; wr=${6:-7}; fault_reg=${7:-0}; mkdir -p "$out"
S=rtl/hbm_accel/generic/adapters/static_su
T=tb_hbm_su_pg_stream_split
verilator --version | tee "$out/version.txt"
build() {
verilator --binary --timing -j "${OT_THREADS:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module $T \
 -GMUT=$mut -GEDGES=$edges -GQID=$qid -GREAD_RETURN=$rr -GWRITE_RETURN=$wr -GFAULT_REG=$fault_reg --Mdir "$out/obj" -o pgs \
 rtl/lib/ot_rst_relay.sv $S/ot_hbm_su_static_vm_ports.sv $S/ot_hbm_su_static_vm_bank_leaf_s.sv \
 $S/programme/multirate_bridge.sv $S/programme/multirate_bridge_split.sv \
 $S/top/ot_hbm_su_static_pg_lg_tap.sv $S/top/ot_hbm_su_static_pg_stream.sv $S/top/ot_hbm_su_static_pg_stream_split.sv \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv \
 rtl/hdc/ot_hdc_delay.sv rtl/test/hbm_accel/generic/$T.sv > "$out/build.log" 2>&1
}
# one retry on a PCH race (10-18 rule)
build || { grep -q "pch\|\.gch\|No such file" "$out/build.log" && rm -rf "$out/obj" && build; } || { tail -40 "$out/build.log"; exit 1; }
{ cat "$out/version.txt"; "$out/obj/pgs"; } | tee "$out/bench.log" | tail -14
