#!/bin/bash
# TOKSIM-HBM-su 10-19: Qwen SFU.GLU span on the d4g sfucore (ot_hgi_sfu_core_split2 = the core of the bound
# ot_hgi_sfu_core_split3, LG_PATH 15, TAP 14/11) + ot_hgi_sfu_programme_store_r10, lockstep with the reference split
# engine (R=15 die relays) + LG pair taps + ot_vms_bank_static VM banks; golden = canonical Qwen fixture words.
# Derived from tools/hbm_static/run_sfu_split_equiv.sh (STORE10=1 CORE2=1 SFU_LG_R=15). Run from the source root.
# usage: run_glu_span.sh OUT WORDS OVERLAP DRAIN_LAG [R=15]
set -euo pipefail
OUT=$(realpath -m "$1"); W=$2; OV=$3; LAG=$4; R=${5:-15}
mkdir -p "$OUT"
mapfile -t sources < results/arch/hbm_native_1013/sfu_native_quarter/r2_sources.txt
manifest=results/arch/hbm_native_1013/sfu_native_quarter/closed_ae5899467.sha256
frozen="$OUT/frozen"; lane_src=physical/ref_tile/sfu_lane_ring3_rt/src
[ -d "$frozen" ] || while read -r digest path;do mkdir -p "$frozen/$(dirname "$path")";cp "$lane_src/$path" "$frozen/$path";done < "$manifest"
frozen=$(realpath "$frozen"); (cd "$frozen" && sha256sum -c --quiet "$OLDPWD/$manifest")
declare -A closed_paths; while read -r digest path;do closed_paths["$path"]=1;done < "$manifest"
for i in "${!sources[@]}";do [ "${closed_paths[${sources[$i]}]:-0}" = 1 ] && sources[$i]="$frozen/${sources[$i]}";done
python3 tools/hbm_static/toksim_su/sfu/gen_glu_case.py results/rtl/hbm_hc_sfu_static_1015/qswiglu "$OUT/data" "$W" "$OV" "$LAG" $((R+1)) | tee "$OUT/case.txt"
M=physical/asap7_memory_macros; P=rtl/hbm_accel/generic/peers
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_quarter.sv tools/hbm_static/toksim_su/sfu/tb_toksim_glu_split.sv
 $P/ot_hgi_sfu_scheduled_engine.sv $P/ot_hgi_sfu_io_calendar_static.sv $P/ot_hgi_sfu_vm_programmed_engine.sv
 $P/ot_hgi_sfu_vm_static_bridge.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 $P/ot_hgi_sfu_programmed_engine.sv $P/ot_hgi_sfu_calendar_paged_static.sv $P/ot_hgi_sfu_program_stripe_static.sv
 $P/ot_hgi_sfu_static_engine.sv $P/ot_hgi_sfu_static_operand_store.sv $P/ot_hgi_su_unit.sv
 $P/ot_hgi_sfu_programme_store.sv $P/ot_hgi_sfu_core_split.sv
 "$M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
 "$M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
 $P/ot_hgi_sfu_split_engine.sv $P/ot_hgi_sfu_lg_relay.sv $P/ot_hgi_sfu_lg_pair_leaf.sv
 $P/ot_hgi_sfu_programme_store_r10.sv $P/ot_hgi_sfu_store_stripe_leaf_r10.sv physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v
 $P/ot_hgi_sfu_core_split2.sv rtl/lib/ot_rst_relay.sv)
ninst=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['ninst'])" "$OUT/data/io_manifest.json")
rows=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['rows'])" "$OUT/data/io_manifest.json")
sedge=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['scalar_prefetch_edge'])" "$OUT/data/io_manifest.json")
minact=$(( W*1000/3072 )); [ $minact -lt 100 ] && minact=100
defs=("-DSFU_IMAGE=\"$OUT/data/image.hex\"" "-DSFU_DATA_DIR=\"$OUT/data\"" -DSFU_LG_R=$R -DSFU_PSTORE_R10 -DSFU_CORE_SPLIT2
 -DSFU_IO_ROWS=$rows -DSFU_SCALAR_EDGE=$sedge -DTK_WORDS=$W -DTK_NINST=$ninst -DTK_MINACT=$minact)
sha256sum "${sources[@]}" "$0" > "$OUT/sources.sha256"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; "$VL" --version > "$OUT/verilator.txt"
"$VL" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD "${defs[@]}" --top-module tb_toksim_glu_split --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 1; }
set +e; "$OUT/obj/Vtb_toksim_glu_split" > "$OUT/run.log" 2>&1; rc=$?; set -e
echo "rc=$rc" >> "$OUT/run.log"
grep -h "TOKSIM_GLU_SPAN\|SFU_SPLIT_EQUIV\|^PASS\|VM_QSWIGLU\|FAULT\|fatal" "$OUT/run.log" | head -8
rm -rf "$OUT/obj" "$frozen"
