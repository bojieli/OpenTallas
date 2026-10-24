#!/bin/bash
# HBM-P5-RTLB 10-23: coll_q2 reduce split twin vs pinned lock-step (Verilator 5.050). usage: run_reduce_pr.sh OUT [MUT] [N] [DENS] [SEED]
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); mut=${2:-0}; n=${3:-20000}; dens=${4:-2}; seed=${5:-1}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
P=rtl/hbm_accel/generic/collective/p2p
src=(rtl/test/hbm_accel/generic/tb_hgi_coll_reduce_static_pr.sv $P/ot_hgi_coll_reduce_static_pr.sv $P/ot_hgi_coll_reduce_static.sv $P/ot_hgi_coll_pring_static.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/proto/ot_fp32_add_rne_pipe.sv)
sha256sum "${src[@]}" "$0" > "$out/sources.sha256"
obj="$out/obj_mut$mut"
[ -x "$obj/Vtb_hgi_coll_reduce_static_pr" ] || "$vl" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GMUT=$mut \
  --top-module tb_hgi_coll_reduce_static_pr --Mdir "$obj" "${src[@]}" > "$out/build_mut$mut.log" 2>&1 || { tail -20 "$out/build_mut$mut.log"; exit 3; }
"$obj/Vtb_hgi_coll_reduce_static_pr" +N=$n +DENS=$dens +SEED=$seed > "$out/run_mut${mut}_d${dens}_s$seed.log" 2>&1 || true
grep -E "REDUCE_PR" "$out/run_mut${mut}_d${dens}_s$seed.log" | head -6
grep -q "REDUCE_PR PASS" "$out/run_mut${mut}_d${dens}_s$seed.log"
