#!/usr/bin/env bash
# HBM-BANKLAT-COLL 10-19: COLL parent VM_RT bench (tb_hgi_coll_ctl_vmrt, Verilator 5.050). MUT0 (VM_RT = LAT budget, lanes
# padded) must PASS; MUT1 (VM_RT = LAT-1), MUT2 (VM_RT 0 = today's leaf), MUT3 (lanes not padded) must FAIL.
# usage: run_coll_ctl_vmrt.sh OUT [LAT]
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd); ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=$(realpath -m "${1:?out}"); LAT=${2:-74}; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
src=("$P/tb_hgi_coll_ctl_vmrt.sv" "$P/ot_hgi_coll_ctl_v5.sv" "$P/ot_hfd_coll_q_hard_v5.sv" "$P/ot_hgi_coll_slice_v7.sv" rtl/hdc/ot_hdc_prefix.sv)
sha256sum "${src[@]}" > "$OUT/sources.sha256"; "$V" --version > "$OUT/verilator.version"
rc_all=0
for m in 0 1 2 3; do
  "$V" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTITOP \
    --top-module tb_hgi_coll_ctl_vmrt -GMUT=$m -GLAT=$LAT -Mdir "$OUT/obj$m" "${src[@]}" > "$OUT/m$m.build.log" 2>&1 \
    || { tail -30 "$OUT/m$m.build.log"; exit 2; }
  set +e; "$OUT/obj$m/Vtb_hgi_coll_ctl_vmrt" > "$OUT/m$m.log" 2>&1; rc=$?; set -e
  grep -m3 'COLL_VMRT' "$OUT/m$m.log" || tail -3 "$OUT/m$m.log"
  if [ $m = 0 ]; then { [ $rc = 0 ] && grep -q '^COLL_VMRT PASS' "$OUT/m$m.log"; } || rc_all=1
  else { [ $rc != 0 ] && ! grep -q '^COLL_VMRT PASS' "$OUT/m$m.log"; } && echo "MUT$m rejected" || { echo "MUT$m SURVIVED"; rc_all=1; }; fi
  rm -rf "$OUT/obj$m"
done
[ $rc_all = 0 ] && echo "COLL_VMRT GATE PASS LAT$LAT" || { echo "COLL_VMRT GATE FAIL"; exit 1; }
