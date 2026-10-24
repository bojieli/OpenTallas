#!/bin/bash
# HBM-P6-CMP (2026-10-23): compiler side of the SFU core split (twin ot_hgi_sfu_static_engine_sp2, store pin registers).
# Same sources / lock-step tb as run_sfu_static_engine_sp2.sh, but the op horizon comes from the COMPILER instead of the
# tb hold: image = sfu_vector_calendar.compile_vector(leaf_split=LS) (LS 1 -> drain horizon + leaf_split_latency
# sfu_op_horizon = 505 rows; LS 0 -> 502 rows) and the tb holds XH 0 extra rows.
#   POS  LS=1: SP2_LOCKSTEP PASS (the compiler's +3 is sufficient)
#   NEG  LS=0: must FAIL (the pinned horizon is short by the 3 edges the twin needs)
# OUT=dir LS=0|1 [SFU_FROZEN_DIR=dir] tools/hgi_unit_tput/run_sfu_static_engine_sp2_cmp.sh
set -euo pipefail
mkdir -p "$OUT"; LS=${LS:?LS 0|1}
mapfile -t sources < results/arch/hbm_native_1013/sfu_native_quarter/r2_sources.txt
manifest=results/arch/hbm_native_1013/sfu_native_quarter/closed_ae5899467.sha256
frozen=$(realpath "${SFU_FROZEN_DIR:?SFU_FROZEN_DIR (closed ae5899467 lane copies, as run_sfu_static_engine_sp2.sh frozen/)}")
(cd "$frozen" && sha256sum -c --quiet "$OLDPWD/$manifest")
declare -A closed_paths
while read -r digest path;do closed_paths["$path"]=1;done < "$manifest"
for i in "${!sources[@]}";do
 if [ "${closed_paths[${sources[$i]}]:-0}" = 1 ];then sources[$i]="$frozen/${sources[$i]}";fi
done
rows=$(python3 - "$OUT/image.hex" "$LS" <<'PYCODE'
import sys
from pathlib import Path
sys.path.insert(0,'tools/hbm_static')
from sfu_vector_calendar import compile_vector
from sfu_control_image import encode
words=encode(compile_vector(words=7168,bases=(0,0,0,0,0),leaf_split=bool(int(sys.argv[2]))))
Path(sys.argv[1]).write_text(''.join(f'{word:0436x}\n' for word in words))
print(len(words))
PYCODE
)
echo "SFU_SP2_CMP LS=$LS image rows=$rows"
sed -e "s/localparam LWB=15,WORDS=7168,ROWS=502,XH=3,SH=2;/localparam LWB=15,WORDS=7168,ROWS=$rows,XH=0,SH=2;/" \
  rtl/test/hbm_accel/generic/tb_hgi_sfu_static_engine_sp2.sv > "$OUT/tb_hgi_sfu_static_engine_sp2.sv"
grep -q "ROWS=$rows,XH=0" "$OUT/tb_hgi_sfu_static_engine_sp2.sv"
T=rtl/hbm_accel/generic/peers/sfu_sp2
M=physical/asap7_memory_macros
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_quarter.sv "$OUT/tb_hgi_sfu_static_engine_sp2.sv"
 $T/ot_su12_sfu_sp2.sv $T/ot_hgi_sfu_arithmetic_grid_sp2.sv $T/ot_hgi_sfu_static_quarter_sp2.sv $T/ot_hgi_sfu_static_engine_sp2.sv
 $T/ot_hgi_sfu_static_operand_store_sp2.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_engine.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_operand_store.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
 "$M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
 "$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
 "$M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v")
sha256sum "${sources[@]}" "$0" tools/hbm_static/sfu_vector_calendar.py tools/hbm_static/leaf_split_latency.py > "$OUT/sources.sha256"
V="${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}"
"$V" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD "-DSFU_IMAGE=\"$OUT/image.hex\"" --Mdir "$OUT/obj" \
  --top-module tb_hgi_sfu_static_engine_sp2 "${sources[@]}" > "$OUT/build.log" 2>&1
set +e; "$OUT/obj/Vtb_hgi_sfu_static_engine_sp2" > "$OUT/run.log" 2>&1; rc=$?; set -e
grep -m2 'SP2_LOCKSTEP' "$OUT/run.log" || tail -5 "$OUT/run.log"
rm -rf "$OUT/obj"
echo "SFU_SP2_CMP LS=$LS rows=$rows rc=$rc"
exit $rc
