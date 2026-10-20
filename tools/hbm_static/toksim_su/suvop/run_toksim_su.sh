#!/usr/bin/env bash
# TOKSIM-HBM-su fork A: build the whole static SU (die-bound parameters) once per profile and run record programmes.
# usage: run_toksim_su.sh build PROFILE   PROFILE = mr10: the die-bound MULTIRATE pgslice at stream 10/7 seen on serial edges
#   (bridge SRD=ceil((3*10+18)/4)=12 read, SWD=10 done -> single-clock READ_RETURN 12 / WRITE_RETURN 10);
#   mr18: stream 18/15 (HBM-BANKLAT-SU budget) -> SRD 18 / SWD 16;  sc10: single-clock 10/7 (reference)
#        run_toksim_su.sh run PROFILE VECDIR [plusargs...]
# Die-bound parameters (artifacts/hdie-d4/d4g_gen2e3/pb0/die.v): pgslice_lg MLAT 4 ALAT 3 LEAF 1 RF_LOCAL 1, stree
# RF_TREE 1 (L_TREE 32).  Single clock: every edge is a SERIAL (SU) edge; MULTIRATE / COLLPORT are 0 in this bench
# (MULTIRATE's serial<->stream bridge offsets are applied by the compiler's srd() fill rule; COLLPORT adds no VOP edge).
set -euo pipefail
cd "$(dirname "$0")"
B=$(pwd)            # bundle root (= repo layout)
mode=$1; prof=$2
case $prof in mr10) RR=12; WR=10;; mr18) RR=18; WR=16;; sc10) RR=10; WR=7;; *) echo bad profile; exit 2;; esac
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
obj=$B/obj_$prof
NE=${NE_MAX:-65536}; NW=${NW_MAX:-131072}; NS=${NS_MAX:-4096}
if [ "$mode" = build ]; then
 "$vl" --version
 S=rtl/hbm_accel/generic/adapters/static_su
 /usr/bin/time -v "$vl" --binary --timing --hierarchical -O1 -j "${JOBS:-8}" -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_toksim_su_top -GNE=$NE -GNW=$NW -GNS=$NS -GRF_RELAY=32 -GMUT=0 -GMLAT=4 -GALAT=3 -GLEAF=1 -GRF_LOCAL=1 \
  -GRF_TREE=1 -GRR=$RR -GWR=$WR --Mdir "$obj" \
  $S/arithmetic/ot_hbm_su_static_ins.sv $S/arithmetic/ot_hbm_su_static_lane.sv $S/arithmetic/ot_hbm_su_static_side.sv \
  $S/data_store/ot_hbm_su_static_data_store.sv $S/data_store/ot_hbm_su_static_pinned_bank.sv \
  $S/register_file/ot_hbm_su_static_rf.sv $S/reduction/ot_hbm_su_reduce_static.sv $S/ot_hbm_su_static_vm_ports.sv \
  $S/top/ot_hbm_su_static_pgslice.sv $S/top/ot_hbm_su_static_qcore.sv $S/top/ot_hbm_su_static_quarter.sv \
  $S/top/ot_hbm_su_stree.sv $S/top/ot_hbm_su_static_top.sv tb_toksim_su_top.sv \
  rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv \
  rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
  rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
  rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
  rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  > "$B/build_$prof.log" 2>&1
 ls -la "$obj/Vtb_toksim_su_top"; echo BUILD_DONE $prof
else
 v=$(realpath "$3"); shift 3
 read -r ne nw ns < <(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["edges"],d["expected_vm_writes"],d["expected_scalars"])' "$v/programme.json")
 /usr/bin/time -v "$obj/Vtb_toksim_su_top" +DIR="$v" +NE_RUN=$ne +NW_RUN=$nw +NS_RUN=$ns "$@" > "$v/sim_$prof${TAG:-}.log" 2>&1 || true
 grep -E "SU_TOP (PASS|FAIL)|TOKSIM_LAST|ERROR" "$v/sim_$prof${TAG:-}.log" | head -50
fi
