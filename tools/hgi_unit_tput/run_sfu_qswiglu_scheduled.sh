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
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_quarter.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_qswiglu_scheduled.sv)
python3 tools/hbm_static/make_qswiglu_gate.py "$SFU_QSWIGLU_FIXTURE" "$OUT/data"
python3 tools/hbm_static/make_qswiglu_io_calendar.py "$OUT/data"
cp "$OUT/data/image.hex" "$OUT/image.hex"
M=physical/asap7_memory_macros
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_scheduled_engine.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_io_calendar_static.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_vm_programmed_engine.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_vm_static_bridge.sv
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_programmed_engine.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_calendar_paged_static.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_program_stripe_static.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_engine.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_operand_store.sv
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
 "$M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
 "$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
 "$M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v")
defs=("-DSFU_IMAGE=\"$OUT/image.hex\"" "-DSFU_DATA_DIR=\"$OUT/data\"")
if [ "${SFU_IO_OVERLAP:-0}" = 1 ];then defs+=(-DSFU_IO_ROWS=432 -DSFU_SCALAR_EDGE=0);fi
if [ "${MUT_PHASE:-0}" = 1 ];then defs+=(-DOT_SFU_STATIC_PHASE_MUTANT);fi
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD "${defs[@]}" --top-module tb_hgi_sfu_qswiglu_scheduled --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_qswiglu_scheduled" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
set +e
"$OUT/obj/Vtb_hgi_sfu_qswiglu_scheduled" +MUT_IO > "$OUT/mutant.log" 2>&1
mut_rc=$?
set -e
if [ "$mut_rc" = 0 ] || ! grep -Eq 'VM_QSWIGLU_WORD|SCHEDULED_ENGINE_FAULT' "$OUT/mutant.log";then cat "$OUT/mutant.log";exit 1;fi
printf 'PASS independent vector compiler actual actual loaded-programme suppressed-issue mutant rc=%s\n' "$mut_rc"
set +e
"$OUT/obj/Vtb_hgi_sfu_qswiglu_scheduled" +MUT_LG_CLOCK > "$OUT/mutant_clock.log" 2>&1
mut_rc=$?
set -e
if [ "$mut_rc" = 0 ] || ! grep -Eq 'VM_QSWIGLU_WORD|SCHEDULED_ENGINE_FAULT' "$OUT/mutant_clock.log";then cat "$OUT/mutant_clock.log";exit 1;fi
printf 'PASS actual missing LG group root mutant rc=%s\n' "$mut_rc"
