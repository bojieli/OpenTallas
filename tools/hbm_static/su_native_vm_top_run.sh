#!/usr/bin/env bash
# Full512lane native VM composition. Run only under fleet admission (160GB LAT4).
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}
top=${SU_NATIVE_TOP:-tb_hbm_su_native_vm_top}
mkdir -p "$out"
mlat=${SU_TOP_MLAT:-4}; alat=${SU_TOP_ALAT:-3}; leaf=${SU_TOP_LEAF:-1}; relay=${SU_TOP_RF_RELAY:-8}
[ -f "$out/vec/prog.mem" ] || python3 tools/hbm_static/su_top_compile.py "$out/vec" --rf-relay "$relay" --mlat "$mlat" --alat "$alat" --leaf "$leaf" > "$out/vec.log"
python3 tools/hbm_static/su_native_vm_calendar.py "$out/vec/prog.mem" "$out/vec/cal.mem" > "$out/calendar.log"
read -r NE NW NS < <(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["edges"],d["expected_vm_writes"],d["expected_scalars"])' "$out/vec/programme.json")
S=rtl/hbm_accel/generic/adapters/static_su
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
obj="$out/obj_m$mut"
"$vl" --binary --timing --hierarchical -O1 -j "${SU_TOP_JOBS:-4}" -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
 --top-module "$top" -GNE="$NE" -GNW="$NW" -GNS="$NS" -GRF_RELAY="$relay" -GMUT="$mut" \
 -GMLAT="$mlat" -GALAT="$alat" -GLEAF="$leaf" --Mdir "$obj" \
 $S/arithmetic/ot_hbm_su_static_ins.sv $S/arithmetic/ot_hbm_su_static_lane.sv $S/arithmetic/ot_hbm_su_static_side.sv \
 $S/data_store/ot_hbm_su_static_data_store.sv $S/data_store/ot_hbm_su_static_pinned_bank.sv \
 $S/register_file/ot_hbm_su_static_rf.sv $S/reduction/ot_hbm_su_reduce_static.sv $S/ot_hbm_su_static_vm_ports.sv \
 $S/top/ot_hbm_su_static_pgslice.sv $S/top/ot_hbm_su_static_qcore.sv $S/top/ot_hbm_su_static_quarter.sv \
 $S/top/ot_hbm_su_static_top.sv $S/native_vm/ot_hbm_su_native_vm.sv \
 $S/native_vm/tb_hbm_su_native_vm_top.sv ${SU_NATIVE_EXTRA_SOURCES:-} \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_split.sv \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv \
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv \
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 > "$out/build_m$mut.log" 2>&1
bin="$obj/V$top"
run(){ local name=$1; shift; set +e; "$bin" +DIR="$out/vec" "$@" > "$out/$name.log" 2>&1; local rc=$?; set -e; echo "exit=$rc" >> "$out/$name.log"; }
run positive
if [ "$mut" = 0 ]; then
 grep -q 'SU_NATIVE_VM_TOP PASS' "$out/positive.log"
 for m in DATA ADDR RF RED CAL; do
  run "mut_$m" "+MUT_$m"
  grep -q 'SU_NATIVE_VM_TOP FAIL' "$out/mut_$m.log"
 done
 echo SU_NATIVE_VM_TOP_GATE_PASS
else
 grep -q 'SU_NATIVE_VM_TOP FAIL' "$out/positive.log"
 echo SU_NATIVE_VM_TOP_RTL_MUTANT_REJECTED
fi
