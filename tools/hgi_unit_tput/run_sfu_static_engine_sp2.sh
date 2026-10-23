#!/bin/bash
# HBM-P5-RTLA (2026-10-23): store-side pin-register twin gate of the SFU core split (ot_hgi_sfu_core_split3 ->
# ot_hgi_sfu_static_engine_sp2).  Same sources / image as run_sfu_static_engine.sh (closed ae5899467 lane frozen copies,
# independent Python vector calendar) plus the _sp2 twin; tb_hgi_sfu_static_engine_sp2 runs twin and pinned in lock-step.
# Positive: SP2_LOCKSTEP PASS.  Mutant (-DOT_SFU_SP2_MUT_RDX1: lane read tags one edge short of the +2 store pins) must FAIL.
# OUT=dir [SFU_FROZEN_DIR=dir] tools/hgi_unit_tput/run_sfu_static_engine_sp2.sh
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
(cd "$frozen" && sha256sum -c --quiet "$OLDPWD/$manifest")
declare -A closed_paths
while read -r digest path;do closed_paths["$path"]=1;done < "$manifest"
for i in "${!sources[@]}";do
 if [ "${closed_paths[${sources[$i]}]:-0}" = 1 ];then sources[$i]="$frozen/${sources[$i]}";fi
done
T=rtl/hbm_accel/generic/peers/sfu_sp2
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_quarter.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_static_engine_sp2.sv
 $T/ot_su12_sfu_sp2.sv $T/ot_hgi_sfu_arithmetic_grid_sp2.sv $T/ot_hgi_sfu_static_quarter_sp2.sv $T/ot_hgi_sfu_static_engine_sp2.sv
 $T/ot_hgi_sfu_static_operand_store_sp2.sv)
python3 - "$OUT/image.hex" <<'PYCODE'
import sys
from pathlib import Path
sys.path.insert(0,'tools/hbm_static')
from sfu_vector_calendar import compile_vector
from sfu_control_image import encode
words=encode(compile_vector(words=7168,bases=(0,0,0,0,0)))
assert len(words)==502
Path(sys.argv[1]).write_text(''.join(f'{word:0436x}\n' for word in words))
PYCODE
M=physical/asap7_memory_macros
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_engine.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_operand_store.sv
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
 "$M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
 "$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
 "$M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v")
sha256sum "${sources[@]}" "$0" > "$OUT/sources.sha256"
V="${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}"
build(){ "$V" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD "-DSFU_IMAGE=\"$OUT/image.hex\"" "$@" --top-module tb_hgi_sfu_static_engine_sp2 "${sources[@]}"; }
STEP=${STEP:-all}
if [ "$STEP" = all ] || [ "$STEP" = pos ];then
 build --Mdir "$OUT/obj" > "$OUT/build.log" 2>&1
 "$OUT/obj/Vtb_hgi_sfu_static_engine_sp2" > "$OUT/run.log" 2>&1 || true
 cat "$OUT/run.log"; grep -q 'SP2_LOCKSTEP PASS' "$OUT/run.log"
fi
if [ "$STEP" = all ] || [ "$STEP" = mut ];then
 build -DOT_SFU_SP2_MUT_RDX1 --Mdir "$OUT/obj_mut" > "$OUT/build_mut.log" 2>&1
 set +e; "$OUT/obj_mut/Vtb_hgi_sfu_static_engine_sp2" > "$OUT/mutant.log" 2>&1; mut_rc=$?; set -e
 if [ "$mut_rc" = 0 ] || ! grep -q 'SP2_LOCKSTEP' "$OUT/mutant.log" || grep -q 'SP2_LOCKSTEP PASS' "$OUT/mutant.log";then cat "$OUT/mutant.log";echo "SFU_SP2 MUTANT ESCAPED";exit 1;fi
 echo "SFU_SP2 MUTANT RDX1 FAILS as required rc=$mut_rc: $(grep -m1 'SP2_LOCKSTEP' "$OUT/mutant.log")"
fi
