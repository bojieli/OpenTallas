#!/usr/bin/env bash
# tb_hgi_coll_rgx_wtx: the SW quadrant engine's ROW_GATHER write path across the die net (wtx -> relays -> snkm).
# usage: run_rgx_wtx_bench.sh <outdir>   positive at RLY 0 / 6 / 20 (CRD 16), and the mutants SNK_MUT 1, SNK_MUT 2, CRD_MUT 1 (must FAIL)
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../../.." && pwd); O=$(realpath -m "$1"); mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic
SRC="$C/collective/p2p/tb_hgi_coll_rgx_wtx.sv $C/collective/p2p/ot_hgi_coll_rgx_wtx.sv $C/collective/rgx/ot_hgi_coll_rgx_snk.sv
 $C/collective/rgx/ot_hgi_coll_rgx_hbm.sv $C/vm/ot_hgi_vm_lanearb.sv"
for f in $(grep -l "module ot_hgi_hbm_rd_server\|module ot_hgi_hbm_wr_server\|module ot_hgi_hbm_rd_client\|module ot_hgi_vm_pkt_client\|module ot_hgi_hbm_wr_client" -r $R/rtl/hbm_accel/generic --include=*.sv); do SRC="$SRC ${f#$R/}"; done
run() { # name expect params...
  local n=$1 e=$2; shift 2
  ( cd "$R" && $V --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hgi_coll_rgx_wtx -Mdir "$O/obj_$n" \
      -I$C "$@" $SRC > "$O/build_$n.log" 2>&1 ) || { echo "BUILD_FAIL $n"; return; }
  "$O/obj_$n/Vtb_hgi_coll_rgx_wtx" > "$O/run_$n.log" 2>&1
  if grep -q "^RGXMEM PASS" "$O/run_$n.log"; then g=PASS; else g=FAIL; fi
  [ $g = $e ] && v=OK || v=WRONG; echo "$v $n expect=$e got=$g | $(grep -m1 -E 'RGXMEM PASS|FATAL' "$O/run_$n.log" | cut -c1-150)"
}
{ run rly0 PASS -GRLY=1; run rly6 PASS -GRLY=6; run rly20 PASS -GRLY=20; run crd4 PASS -GRLY=12 -GCRD=4
  run mut_snk1 FAIL -GSNK_MUT=1; run mut_snk2 FAIL -GSNK_MUT=2; run mut_crd FAIL -GCRD_MUT=1; } | tee "$O/SUMMARY"
grep -q "WRONG\|BUILD_FAIL" "$O/SUMMARY" && { echo "RGX_WTX FAIL"; exit 1; } || echo "RGX_WTX PASS"
