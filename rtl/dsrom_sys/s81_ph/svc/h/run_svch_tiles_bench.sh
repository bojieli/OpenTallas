#!/usr/bin/env bash
# CLAUDE s81die-1011/ctrl svch: tile benches of dsfd_svch_pcs / dsfd_svch_rly.  Usage (repo root): run_svch_tiles_bench.sh OUT [pcs|pcs_btag|rly|rly_drop]
# env PCS_G (e.g. -GHDLY=1) passes tile parameters to the pcs bench; prints the bench's SVCHPCS / SVCHRLY line (PASS / FAIL).
set -uo pipefail
O=$1; t=${2:-pcs}; mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
H=rtl/dsrom_sys/s81_ph/svc/h
case $t in pcs) top=tb_dsfd_svch_pcs; d="${PCS_G:-}";; pcs_btag) top=tb_dsfd_svch_pcs; d="-DSVCQS_MUT_BTAG ${PCS_G:-}";; rly) top=tb_dsfd_svch_rly; d="";; rly_drop) top=tb_dsfd_svch_rly; d="-DSVCH_MUT_RLY_DROP";; esac
"$VL" --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module $top $d -Mdir "$O/obj_$t" -o sim \
  $H/ot_s81_svch_lane.sv $H/ot_s81_svch_pcsvc.sv $H/dsfd_svch_pcs.sv rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io.sv $H/tb_svch_tiles.sv \
  > "$O/build_$t.log" 2>&1 || { echo "$t BUILD FAIL"; tail -5 "$O/build_$t.log"; exit 1; }
"$O/obj_$t/sim" +seed=1 > "$O/run_$t.log" 2>&1
grep -h "SVCHPCS\|SVCHRLY" "$O/run_$t.log" | tail -1
