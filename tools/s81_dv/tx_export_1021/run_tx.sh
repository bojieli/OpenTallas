#!/bin/bash
set -eu
out=$(realpath -m "${1:?out}");mut=${2:-0};mkdir -p "$out"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_l20s.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v tools/s81_dv/tx_export_1021/tb_tx_miter.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
"$VL" --version > "$out/verilator.version"
"$VL" --binary --timing --output-split 10000 --output-split-cfuncs 1000 -j "${J:-4}" -CFLAGS -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE --top-module tb_tx_miter -GMUT="$mut" ${TX_G:-} "${src[@]}" --Mdir "$out/obj" -o sim > "$out/build.log" 2>&1 || { tail -25 "$out/build.log";echo TX_BUILD_FAIL;exit 2; }
set +e
"$out/obj/sim" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
if [ "$rc" = 0 ] && grep -q '^TX_MITER_PASS$' "$out/run.log";then exit 0;fi
if [ "$rc" != 0 ] && grep -q '^TX_MISMATCH ' "$out/run.log";then echo TX_CAUSAL_FAIL;exit 1;fi
echo TX_UNCLASSIFIED_FAIL;exit 2
