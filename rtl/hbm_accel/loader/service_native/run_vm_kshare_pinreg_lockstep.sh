#!/usr/bin/env bash
# STEWARD-HBMd/PINREG-KS 2026-10-23 (kshare r6): PINREG=0 vs PINREG=1 lockstep (tb_hbm_svc_vm_kshare_pinreg_lockstep).
#   run_vm_kshare_pinreg_lockstep.sh OUTDIR [case...]   cases (default all):
#   krl1 / krl1_slow / krl1_fast / krl0 -> PASS (equal per-class transaction streams, +1 latency recorded);
#   mut_ring2 (PINREG=1 DUT MUT 9: A/E rings depth 2) and mut_depth (MUT 6: C ring one entry short) -> FAIL.
# Verilator 5.050 (the closure daemon version); run via ot-run.
set -u
cd "$(dirname "$0")/../../../.."
out=$(realpath -m "${1:?outdir}"); shift; mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
n=rtl/hbm_accel/loader/service_native
src=("$n/tb_hbm_svc_vm_kshare_pinreg_lockstep.sv" "$n/ot_hbm_svc_vm_kshare_splitstrap.sv" "$n/ot_hbm_svc_kshare_sl.sv"
 "$n/ot_hbm_svc_async_fifo_shp.sv" "$n/ot_hbm_svc_async_fifo.sv" rtl/lib/ot_rst_fanout.sv "$n/ot_hbm_svc_ring_h9b_ff.sv"
 rtl/lib/ot_reset_sync.sv "$n/ot_hbm_svc_pc_ctrl_leaf.sv")
sha256sum "${src[@]}" > "$out/source.sha256"; "$vl" --version > "$out/verilator.version"
cases=("$@"); ((${#cases[@]})) || cases=(krl1 krl1_slow krl1_fast krl0 mut_ring2 mut_depth)
one(){ c=$1; g=(); pa=()
 case "$c" in
  krl1) g=(-GKRL1=1);; krl1_slow) g=(-GKRL1=1); pa=(+HBM_HALF=700 +STR_HALF=400);; krl1_fast) g=(-GKRL1=1); pa=(+HBM_HALF=400 +STR_HALF=700);;
  krl0) g=(-GKRL1=0);; mut_ring2) g=(-GKRL1=1 -GMUT1=9);; mut_depth) g=(-GKRL1=1 -GMUT1=6);;
  *) echo "$c: FAIL unknown case"; return;;
 esac
 "$vl" --binary --timing -j "${JOBS:-4}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-ZERODLY \
  --top-module tb_hbm_svc_vm_kshare_pinreg_lockstep --Mdir "$out/obj-$c" -o sim "${g[@]}" "${src[@]}" > "$out/build-$c.log" 2>&1 \
  || { echo "$c: BUILD_FAIL"; tail -20 "$out/build-$c.log"; return; }
 "$out/obj-$c/sim" "${pa[@]}" > "$out/$c.log" 2>&1
 echo "$c: $(grep -E '^(PASS|FAIL)' "$out/$c.log" | tail -n 1)"
 rm -rf "$out/obj-$c"
}
for c in "${cases[@]}"; do one "$c" & done; wait
for c in "${cases[@]}"; do grep -E '^(LATENCY|STREAM|LANE|MISMATCH|FAULT|INCOMPLETE)' "$out/$c.log" 2>/dev/null | sed "s/^/$c | /" | head -20; done
