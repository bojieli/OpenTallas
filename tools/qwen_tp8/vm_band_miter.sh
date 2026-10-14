#!/bin/bash
set -eu
# One full production-shape run. Independent variants are admitted by ot-run.
mode=${1:-native}
case "$mode" in
 native) args=(-GSMAX=9);;
 fallback) args=(-GSMAX=11);;
 lane_mutant) args=(-GSMAX=9 -GMUT=1);;
 root_mutant) args=(-GSMAX=9 -GMUT=2);;
 *) echo "unknown mode: $mode" >&2; exit 2;;
esac
out=${VM_BAND_OUT:-/tmp/qwen-vm-band}/$mode
mkdir -p "$out"
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
p=rtl/qwen_sys/vm_plane_20261013
"$v" --binary --timing -O1 --output-split 12000 --output-split-cfuncs 1000 \
 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-PINMISSING -Wno-UNOPTFLAT \
 -j 4 --top-module tb_qfd_vm_band "${args[@]}" --Mdir "$out/build" \
 "$p/band/tb_qfd_vm_band.sv" "$p/band/ot_qfd_vm_band.sv" \
 "$p/ot_qfd_vm_xcol_roots.sv" "$p/ot_qfd_vm_xtree.sv" \
 "$p/ot_qfd_vm_xplane.sv" "$p/ot_qfd_vm_xpad2.sv" \
 "$p/bay/ot_qfd_vm_xrelay_w.sv" > "$out/build.log" 2>&1
set +e
"$out/build/Vtb_qfd_vm_band" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
printf 'BAND_MODE=%s RUN_EXIT=%s\n' "$mode" "$rc"
if [[ "$mode" == *mutant ]]; then
 [[ "$rc" != 0 ]] && grep -q '^FAIL fullband' "$out/run.log"
else
 [[ "$rc" == 0 ]] && grep -q '^PASS fullband' "$out/run.log"
fi
