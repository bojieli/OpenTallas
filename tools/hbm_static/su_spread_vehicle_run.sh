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
    python3 "$ROOT/tools/hbm_static/su_f2_spread.py" --vectors "$OUT/$d" --design $d --out "$RES/spread_$d.json" --vehicle "$OUT/veh_$d" \
        --map "$RES/address_map_$d.json" >"$RES/compile_$d.log"
    # LAT4 (MLAT 4) physical candidate: same placement, calendar only (sensitivity, not executed on the vehicle)
    python3 "$ROOT/tools/hbm_static/su_f2_spread.py" --vectors "$OUT/$d" --design $d --mlat 4 --out "$RES/spread_${d}_lat4.json" \
        >"$RES/compile_${d}_lat4.log"
done
# the frozen G25 rank-0 profile the h_vm allocator binds (284d8fa0e): map + calendar on THAT source, never mixed
G25=$ROOT/results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json
python3 "$ROOT/tools/hgi_unitrate/su_prod_vec.py" --out "$OUT/ds_g25" --unit both --allow-incomplete-coverage --ds-program "$G25" >/dev/null
python3 "$ROOT/tools/hbm_static/su_f2_spread.py" --vectors "$OUT/ds_g25" --design deepseek --ds-program "$G25" \
    --out "$RES/spread_deepseek_g25.json" --map "$RES/address_map_deepseek_g25.json" >"$RES/compile_deepseek_g25.log"
iverilog -g2012 -s tb_hbm_su_static_spread_vehicle -o "$OUT/sim/m0.vvp" "${SRC[@]}"
for m in PG LG CAL; do iverilog -g2012 -s tb_hbm_su_static_spread_vehicle -Ptb_hbm_su_static_spread_vehicle.MUT_$m=1 -o "$OUT/sim/mut_$m.vvp" "${SRC[@]}"; done
pids=()
for d in qwen deepseek; do for b in m0 mut_PG mut_LG mut_CAL; do
    ( set +e; vvp "$OUT/sim/$b.vvp" +stem="$OUT/veh_$d" 2>&1 | grep -v WARNING >"$RES/${b}_$d.log"; echo "exit=${PIPESTATUS[0]}" >>"$RES/${b}_$d.log" ) & pids+=($!)
done; done
wait "${pids[@]}"
for d in qwen deepseek; do
    grep -q '^SU_SPREAD_VEHICLE PASS' "$RES/m0_$d.log"
    for m in PG LG CAL; do grep -q 'SU_SPREAD_VEHICLE FAIL' "$RES/mut_${m}_$d.log"; done
done
echo SPREAD_VEHICLE_GATE PASS
