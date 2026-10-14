#!/bin/bash
set -eu
mode=${1:-native}
case "$mode" in
 native) args=(-GSMAX=9);;
 fallback) args=(-GSMAX=11);;
 native_delay) args=(-GSMAX=9 -GMUT=1);;
 native_epoch) args=(-GSMAX=9 -GMUT=2);;
 fallback_delay) args=(-GSMAX=11 -GMUT=1);;
 fallback_epoch) args=(-GSMAX=11 -GMUT=2);;
 *) echo "unknown mode: $mode" >&2;exit 2;;
esac
out=${VM_BAND_INTEGRATION_OUT:-$PWD/results/rtl/qwen_tp8_vm_plane_20261013/vm_band_integration}/$mode
mkdir -p "$out"
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
p=rtl/qwen_sys/vm_plane_20261013
"$v" --binary --timing -O1 --output-split 12000 --output-split-cfuncs 1000 \
 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-PINMISSING -Wno-UNOPTFLAT \
 -j 4 --top-module tb_qfd_vm_band_integration "${args[@]}" --Mdir "$out/build" \
 "$p/band_integration/tb_qfd_vm_band_integration.sv" "$p/band/ot_qfd_vm_band.sv" \
 "$p/band_controls/ot_qfd_vm_band_controls.sv" \
 "$p/ot_qfd_vm_xcol_roots.sv" "$p/ot_qfd_vm_xtree.sv" \
 "$p/ot_qfd_vm_xplane.sv" "$p/ot_qfd_vm_xpad2.sv" \
 "$p/bay/ot_qfd_vm_xrelay_w.sv" > "$out/build.log" 2>&1
set +e
"$out/build/Vtb_qfd_vm_band_integration" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
printf 'INTEGRATION_MODE=%s RUN_EXIT=%s\n' "$mode" "$rc"
if [[ "$mode" == *_delay || "$mode" == *_epoch ]]; then
 [[ "$rc" != 0 ]] && grep -q '^FAIL integration' "$out/run.log"
else
 [[ "$rc" == 0 ]] && grep -q '^PASS integration' "$out/run.log"
fi
