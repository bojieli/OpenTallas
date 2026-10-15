#!/usr/bin/env bash
# Whole static SU (ot_hbm_su_static_top) exact full-shape bench: vectors (su_top_compile.py), Verilator build of the real
# top (512 lanes, 3,072 store SRAM models, 4 reducers, 4 RF replicas), positive run + bench mutants on the same binary.
# Usage: su_top_run.sh OUT [MUT]   (MUT = RTL mutant build: 0 positive/bench mutants, 1 fill phase, 2 drain group,
#                                   4 RF-broadcast phase, 8 missing relay route)
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}
mkdir -p "$out"
mlat=${SU_TOP_MLAT:-3}; alat=${SU_TOP_ALAT:-3}; leaf=${SU_TOP_LEAF:-0}; relay=${SU_TOP_RF_RELAY:-8}
[ -f "$out/vec/prog.mem" ] || python3 tools/hbm_static/su_top_compile.py "$out/vec" --rf-relay "$relay" --mlat "$mlat" --alat "$alat" --leaf "$leaf" > "$out/vec.log"
read -r NE NW NS < <(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["edges"],d["expected_vm_writes"],d["expected_scalars"])' "$out/vec/programme.json")
S=rtl/hbm_accel/generic/adapters/static_su
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
obj="$out/obj_m$mut"
"$vl" --binary --timing --hierarchical -O1 -j "${SU_TOP_JOBS:-4}" -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
 --top-module tb_hbm_su_static_top -GNE="$NE" -GNW="$NW" -GNS="$NS" -GRF_RELAY="$relay" -GMUT="$mut" \
 -GMLAT="$mlat" -GALAT="$alat" -GLEAF="$leaf" --Mdir "$obj" \
 $S/arithmetic/ot_hbm_su_static_ins.sv $S/arithmetic/ot_hbm_su_static_lane.sv $S/arithmetic/ot_hbm_su_static_side.sv \
 $S/data_store/ot_hbm_su_static_data_store.sv $S/data_store/ot_hbm_su_static_pinned_bank.sv \
 $S/register_file/ot_hbm_su_static_rf.sv $S/reduction/ot_hbm_su_reduce_static.sv $S/ot_hbm_su_static_vm_ports.sv \
 $S/top/ot_hbm_su_static_pgslice.sv $S/top/ot_hbm_su_static_qcore.sv $S/top/ot_hbm_su_static_quarter.sv \
 $S/top/ot_hbm_su_static_top.sv $S/top/tb_hbm_su_static_top.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv \
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 > "$out/build_m$mut.log" 2>&1
bin="$obj/Vtb_hbm_su_static_top"
run(){ local name=$1; shift; ( set +e; "$bin" +DIR="$out/vec" "$@" > "$out/$name.log" 2>&1; echo "exit=$?" >> "$out/$name.log" ); }
if [ "$mut" = 0 ]; then
  run m0 & run mut_DATA +MUT_DATA & run mut_ADDR +MUT_ADDR & run mut_RF +MUT_RF & run mut_RED +MUT_RED & wait
  grep -q '^SU_TOP PASS' "$out/m0.log"
  for m in DATA ADDR RF RED; do grep -q 'SU_TOP FAIL' "$out/mut_$m.log"; done
  echo SU_TOP_GATE PASS
else
  run rtl_mut$mut
  grep -q 'SU_TOP FAIL' "$out/rtl_mut$mut.log"
  echo "SU_TOP_RTL_MUT$mut FAILS_AS_EXPECTED"
fi
