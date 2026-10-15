#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
mapfile -t sources < results/arch/hbm_native_1013/sfu_native_quarter/r2_sources.txt
manifest=results/arch/hbm_native_1013/sfu_native_quarter/closed_ae5899467.sha256
frozen="${SFU_FROZEN_DIR:-$OUT/frozen}"
if [ -z "${SFU_FROZEN_DIR:-}" ];then
while read -r digest path;do
 mkdir -p "$frozen/$(dirname "$path")"
 git show "ae5899467:physical/ref_tile/sfu_lane_ring3_rt/src/$path" > "$frozen/$path"
done < "$manifest"
fi
frozen=$(realpath "$frozen")
(cd "$frozen" && sha256sum -c "$OLDPWD/$manifest")
declare -A closed_paths
while read -r digest path;do closed_paths["$path"]=1;done < "$manifest"
for i in "${!sources[@]}";do
 if [ "${closed_paths[${sources[$i]}]:-0}" = 1 ];then sources[$i]="$frozen/${sources[$i]}";fi
done
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_quarter.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_static_quarter.sv)
defs=()
if [ "${MUT_PHASE:-0}" = 1 ];then defs+=(-DOT_SFU_STATIC_PHASE_MUTANT);fi
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD "${defs[@]}" --top-module tb_hgi_sfu_static_quarter --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_static_quarter" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
