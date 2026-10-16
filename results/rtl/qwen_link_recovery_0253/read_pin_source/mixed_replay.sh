#!/bin/bash
set -eu
cd /srv/opentallas-scratch/codex/dvm_read_pin_mixed_0253
sha256sum rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/qwen_sys/dvm_20261014/tb_qfd_xs_leaf_read_pin.sv > source.sha256
for mut in 0 2; do
 out=$PWD/mut$mut
 mkdir -p "$out"
 "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --x-assign 0 --x-initial 0 --top-module tb_qfd_xs_leaf_read_pin --prefix Vtb --Mdir "$out/obj" -GMUT=$mut rtl/hdc/ot_hdc_delay.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/qwen_sys/dvm_20261014/tb_qfd_xs_leaf_read_pin.sv -o tb -CFLAGS -O1 > "$out/build.log" 2>&1
 set +e
 "$out/obj/tb" > "$out/run.log" 2>&1
 rc=$?
 set -e
 if test "$mut" = 0; then test "$rc" = 0; grep '^PASS read_pin' "$out/run.log"; else test "$rc" != 0; grep 'FAIL read_pin payload' "$out/run.log"; fi
done
