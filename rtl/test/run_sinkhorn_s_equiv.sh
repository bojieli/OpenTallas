#!/bin/bash
# HBM-P4-SPLIT: ot_hdc_sinkhorn_s (core split) vs pinned ot_hdc_sinkhorn lock-step.  run_sinkhorn_s_equiv.sh OUT pos|mut
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); mode=${2:-pos}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
src=(rtl/test/tb_hdc_sinkhorn_s_equiv.sv rtl/hdc/v41/ot_hdc_sinkhorn_s.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv)
def=(); [ "$mode" = mut ] && def=(-DMUT=1)
sha256sum "${src[@]}" > "$out/sources.sha256"
"$vl" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD "${def[@]}" \
  --top-module tb_hdc_sinkhorn_s_equiv --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; exit 3; }
set +e; "$out/obj/Vtb_hdc_sinkhorn_s_equiv" +N=${N:-300} > "$out/run.log" 2>&1; rc=$?; set -e
grep -E "SINKHORN_S_EQUIV|MISMATCH" "$out/run.log" | head -8
echo "SINKHORN_S_MODE $mode rc=$rc"; exit $rc
