#!/bin/bash
set -eu
out=$1
mut=${2:-0}
ready_mut=${3:-0}
extra=()
if [ "$ready_mut" = 1 ]; then extra+=(-DOT_HBM_IDX_READY_MUT_LAX); fi
mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
src=(rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv
 rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/test/hbm_idx_chunk_el/tb_hbm_native_idx_owned.sv rtl/test/hbm_idx_chunk_el/native_idx_owned.vlt)
"$vl" --hierarchical --cc --exe --build -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style \
 --top-module tb_hbm_native_idx_owned -GNS=16 -GMUT="$mut" "${extra[@]}" -CFLAGS '-DVTOP=Vtb_hbm_native_idx_owned -O1' \
 --Mdir "$out/obj" "${src[@]}" "$(pwd)/rtl/test/hdc_v41_tb_harness.cpp" >"$out/build.log" 2>&1
python3 tools/hbm_native_idx_owned_vectors.py --out "$out/vectors" >"$out/vectors.log"
nt=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ntok"])' "$out/vectors/metadata.json")
ns=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nslot"])' "$out/vectors/metadata.json")
bin=$(realpath "$out/obj/Vtb_hbm_native_idx_owned")
(cd "$out/vectors" && "$bin" +NTOK="$nt" +NSLOT="$ns" +BUBBLE=4 +ORDY=6) >"$out/run.log" 2>&1
cat "$out/run.log"
if [ "$mut" = 0 ] && [ "$ready_mut" = 0 ]; then
 grep -q 'V41XARR.*errors=0 ' "$out/run.log"
elif [ "$mut" != 0 ]; then
 grep -Eq 'V41XARR.*errors=[1-9][0-9]* ' "$out/run.log"
fi
sha256sum "${src[@]}" "$bin" >"$out/source_binary.sha256"
