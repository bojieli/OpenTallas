#!/usr/bin/env bash
# Regenerate the canonical SU fixtures, compile the per-quarter VM spread calendar (su_f2_spread.py) and execute it on
# the static SU VM vehicle (port groups -> LG SU station -> 32 static banks -> SRAM models): positive + 2 mutants.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$(realpath -m "${1:?scratch output directory}")
RES=${2:-$ROOT/results/arch/hbm_su_f2_static_1014/spread}
mkdir -p "$OUT/sim" "$RES"
V=$ROOT/rtl/hbm_accel/generic
SRC=("$V/adapters/static_su/tb_hbm_su_static_spread_vehicle.sv" "$V/adapters/static_su/ot_hbm_su_static_vm_ports.sv"
     "$V/vm/static/ot_hbm_vm_lg_static_bank.sv" "$V/vm/static/ot_hbm_vm_lg_static_split.sv" "$V/vm/static/ot_vms_bank_static.sv"
     "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v")
python3 "$ROOT/tools/hgi_unitrate/su_prod_vec.py" --out "$OUT/qwen" --unit both --allow-incomplete-coverage >/dev/null
python3 "$ROOT/tools/hgi_unitrate/su_prod_vec.py" --out "$OUT/deepseek" --unit both --allow-incomplete-coverage \
    --ds-program "$ROOT/results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json" >/dev/null
for d in qwen deepseek; do
    python3 "$ROOT/tools/hbm_static/su_f2_spread.py" --vectors "$OUT/$d" --design $d --out "$RES/spread_$d.json" --vehicle "$OUT/veh_$d" >"$RES/compile_$d.log"
done
iverilog -g2012 -s tb_hbm_su_static_spread_vehicle -o "$OUT/sim/m0.vvp" "${SRC[@]}"
for m in PG LG; do iverilog -g2012 -s tb_hbm_su_static_spread_vehicle -Ptb_hbm_su_static_spread_vehicle.MUT_$m=1 -o "$OUT/sim/mut_$m.vvp" "${SRC[@]}"; done
pids=()
for d in qwen deepseek; do for b in m0 mut_PG mut_LG; do
    ( set +e; vvp "$OUT/sim/$b.vvp" +stem="$OUT/veh_$d" 2>&1 | grep -v WARNING >"$RES/${b}_$d.log"; echo "exit=${PIPESTATUS[0]}" >>"$RES/${b}_$d.log" ) & pids+=($!)
done; done
wait "${pids[@]}"
for d in qwen deepseek; do
    grep -q '^SU_SPREAD_VEHICLE PASS' "$RES/m0_$d.log"
    for m in PG LG; do grep -q 'SU_SPREAD_VEHICLE FAIL' "$RES/mut_${m}_$d.log"; done
done
echo SPREAD_VEHICLE_GATE PASS
