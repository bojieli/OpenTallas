#!/bin/bash
# H-SU 2026-10-16: lockstep equivalence of the SFU physical split (programme store + core) against
# ot_hgi_sfu_scheduled_engine on the canonical Qswiglu invocation. Usage: OUT=dir [SFU_LG_R=23] [EQ_MUT=flip|skip] $0
set -euo pipefail
mkdir -p "$OUT"
mapfile -t sources < results/arch/hbm_native_1013/sfu_native_quarter/r2_sources.txt
manifest=results/arch/hbm_native_1013/sfu_native_quarter/closed_ae5899467.sha256
frozen="$OUT/frozen"
[ -d "$frozen" ] || while read -r digest path;do mkdir -p "$frozen/$(dirname "$path")";git show "ae5899467:physical/ref_tile/sfu_lane_ring3_rt/src/$path" > "$frozen/$path";done < "$manifest"
frozen=$(realpath "$frozen")
(cd "$frozen" && sha256sum -c --quiet "$OLDPWD/$manifest")
declare -A closed_paths
while read -r digest path;do closed_paths["$path"]=1;done < "$manifest"
for i in "${!sources[@]}";do [ "${closed_paths[${sources[$i]}]:-0}" = 1 ] && sources[$i]="$frozen/${sources[$i]}";done
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_quarter.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_split_equiv.sv)
python3 tools/hbm_static/make_qswiglu_gate.py "${SFU_QSWIGLU_FIXTURE:-results/rtl/hbm_hc_sfu_static_1015/qswiglu}" "$OUT/data"
lgpath=$((${SFU_LG_R:?SFU_LG_R required (0 or 23)}+1))  # reference split engine LG = 1 + R; the split core runs LG_PATH=R so its bridge (R+1 incl. its pin-register pair) matches
SFU_LG_PATH=$lgpath python3 tools/hbm_static/make_qswiglu_io_calendar.py "$OUT/data"
cp "$OUT/data/image.hex" "$OUT/image.hex"
M=physical/asap7_memory_macros
P=rtl/hbm_accel/generic/peers
sources+=($P/ot_hgi_sfu_scheduled_engine.sv $P/ot_hgi_sfu_io_calendar_static.sv $P/ot_hgi_sfu_vm_programmed_engine.sv
 $P/ot_hgi_sfu_vm_static_bridge.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 $P/ot_hgi_sfu_programmed_engine.sv $P/ot_hgi_sfu_calendar_paged_static.sv $P/ot_hgi_sfu_program_stripe_static.sv
 $P/ot_hgi_sfu_static_engine.sv $P/ot_hgi_sfu_static_operand_store.sv $P/ot_hgi_su_unit.sv
 $P/ot_hgi_sfu_programme_store.sv $P/ot_hgi_sfu_core_split.sv
 "$M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
 "$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
 "$M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v")
defs=("-DSFU_IMAGE=\"$OUT/image.hex\"" "-DSFU_DATA_DIR=\"$OUT/data\"")
if true;then
 sources+=($P/ot_hgi_sfu_split_engine.sv $P/ot_hgi_sfu_lg_relay.sv $P/ot_hgi_sfu_lg_pair_leaf.sv)
 defs+=(-DSFU_LG_R=$SFU_LG_R)
fi
# CORE2=1 (k7, opt-in): the core under test is ot_hgi_sfu_core_split2 (W/E lane ports, regional clock roots, reset relay)
if [ "${CORE2:-0}" = 1 ];then sources+=($P/ot_hgi_sfu_core_split2.sv rtl/lib/ot_rst_relay.sv); defs+=(-DSFU_CORE_SPLIT2); fi
# SYNC_RST=1 (k8, owner standard 10-16): synchronous regional resets in the SFU core files (OT_SFU_SYNC_RST)
if [ "${SYNC_RST:-0}" = 1 ];then defs+=(-DOT_SFU_SYNC_RST); fi
case "${EQ_MUT:-}" in flip) defs+=(-DOT_SFU_PSTORE_MUT_FLIP);; skip) defs+=(-DOT_SFU_CORE_MUT_SKIP_REG);; clkpw) defs+=(-DOT_SFU_CORE2_MUT_CLKPW);; "") ;; *) echo bad EQ_MUT >&2;exit 2;; esac
rows=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['rows'])" "$OUT/data/io_manifest.json")
sedge=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['scalar_prefetch_edge'])" "$OUT/data/io_manifest.json")
defs+=(-DSFU_IO_ROWS=$rows -DSFU_SCALAR_EDGE=$sedge)
sha256sum "${sources[@]}" "$0" > "$OUT/sources.sha256"
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD "${defs[@]}" --top-module tb_hgi_sfu_split_equiv --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1
set +e
"$OUT/obj/Vtb_hgi_sfu_split_equiv" > "$OUT/run.log" 2>&1
rc=$?
set -e
tail -n 4 "$OUT/run.log"
if [ -z "${EQ_MUT:-}" ];then
 [ "$rc" = 0 ] && grep -q 'SFU_SPLIT_EQUIV PASS' "$OUT/run.log" && grep -q '^PASS canonical' "$OUT/run.log" && echo "SFU_SPLIT_GATE POSITIVE PASS" && exit 0
 echo "SFU_SPLIT_GATE POSITIVE FAIL rc=$rc";exit 1
else
 [ "$rc" != 0 ] && grep -q 'SFU_SPLIT_EQUIV FAIL\|SFU_SPLIT_EQUIV_MISMATCH' "$OUT/run.log" && echo "SFU_SPLIT_GATE MUTANT ${EQ_MUT} REJECTED (expected)" && exit 0
 echo "SFU_SPLIT_GATE MUTANT ${EQ_MUT} ESCAPED rc=$rc";exit 1
fi
