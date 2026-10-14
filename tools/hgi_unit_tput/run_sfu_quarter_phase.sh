#!/bin/bash
set -euo pipefail
mut=${MUT_PHASE:-0}
mkdir -p "$OUT"
defs=()
if [ "${MUT_PHASE:-0}" != 0 ];then defs+=(-DOT_SFU_PHASE_MUTANT);fi
source_list=results/arch/hbm_native_1013/sfu_native_quarter/r2_sources.txt
if [ "${SPLIT_S_PIPE:-0}" != 0 ];then source_list=results/arch/hbm_native_1013/sfu_native_quarter/r5_sources.txt;fi
mapfile -t sources < "$source_list"
# Arithmetic and original oracle always use the actual immutable CLOSED source, not current software defaults.
closed_manifest=results/arch/hbm_native_1013/sfu_native_quarter/closed_ae5899467.sha256
frozen=${SFU_FROZEN_DIR:-}
if [ -z "$frozen" ] && [ -d physical/ref_tile/sfu_lane_ring3_rt/src ];then
 frozen=physical/ref_tile/sfu_lane_ring3_rt/src
elif [ -z "$frozen" ] && git rev-parse --git-dir >/dev/null 2>&1;then
 frozen="$OUT/frozen_ae5899467"
 while read -r digest path;do
  mkdir -p "$frozen/$(dirname "$path")"
  git show "ae5899467:physical/ref_tile/sfu_lane_ring3_rt/src/$path" > "$frozen/$path"
 done < "$closed_manifest"
fi
# Immutable shipped vehicles already place these exact files at the original paths.
frozen=$(realpath "${frozen:-.}")
(cd "$frozen" && sha256sum -c "$OLDPWD/$closed_manifest")
declare -A closed_paths
while read -r digest path;do closed_paths["$path"]=1;done < "$closed_manifest"
for i in "${!sources[@]}";do
 if [ "${closed_paths[${sources[$i]}]:-0}" = 1 ];then sources[$i]="$frozen/${sources[$i]}";fi
done
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD "${defs[@]}" --top-module tb_hgi_sfu_quarter_phase -GMUT_PHASE="$mut" -GSPLIT_S_PIPE="${SPLIT_S_PIPE:-0}" --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_quarter_phase" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
