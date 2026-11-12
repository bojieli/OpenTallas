#!/bin/bash
# run_rxbm3_spcyc_gate.sh OUTDIR [REPO_ROOT]   (CORES-HBM-1 rxbm3 11-12)
# Lock-step gate of the opt-in OT_RXBM3_SPCYC (+ OT_S81_RM_STAGED) form of ot_pdie_serdes_rx_bm3_rest:
#   base = defines off (kit default -DOT_RXBM3_SRAM_SPLIT), form = + OT_RXBM3_SPCYC + OT_S81_RM_STAGED, mut = form +
#   RXBM3_MUT_SPCYC (partial product 3 dropped).  PASS = form rx(t) == base rx(t-2), st[0] at -1, st[1] at 0 after reset,
#   base decodes >= 80% of the correctable frames exactly, AND the mutant FAILS.  Verilator 5.032 in docker, memory capped.
set -u
O=$1; ROOT=${2:-$(cd "$(dirname "$0")/../../../.." && pwd)}
B=$(cd "$(dirname "$0")" && pwd); mkdir -p "$O"; O=$(cd "$O" && pwd)
M=rtl/hbm_accel/cores_split/reform_1106; L=rtl/dsrom_sys/s81_link
F="/x/$M/tb_rxbm3_sram_models.sv /x/$M/tb_rxbm3_spcyc.sv /x/$M/tb_rxbm3_rest_fshell_seam7.sv /x/rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192_face/ot_hbm_face_reg.sv /x/$M/ot_pdie_serdes_rx_bm3.sv /x/$L/ot_pdie_serdes.sv /x/$L/ot_s81_kp4_common.sv /x/$L/ot_s81_kp4_bm.sv /x/$L/ot_s81_kp4_dchn.sv /x/$L/ot_s81_kp4_ddly.sv /x/$L/ot_s81_kp4_dout.sv /x/$L/ot_s81_kp4_enc.sv /x/$M/ot_s81_kp4_sp.sv"
run() {  # name defines
  mkdir -p "$O/$1"
  docker run --rm --memory 24g --user $(id -u):$(id -g) -e HOME=/o -e CCACHE_DISABLE=1 -v "$ROOT:/x:ro" -v "$O/$1:/o" -w /o verilator/verilator:v5.032 \
    --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN +incdir+/x/$M +incdir+/x/$L -DSYNTHESIS $2 \
    --top-module tb_rxbm3_spcyc --Mdir /o/obj -o tb $F > "$O/$1/build.log" 2>&1 || { echo "BUILD_FAIL $1"; return 2; }
  docker run --rm --memory 8g --user $(id -u):$(id -g) -e HOME=/o -v "$O/$1:/o" -w /o --entrypoint /o/obj/tb verilator/verilator:v5.032 +verilator+seed+11 > "$O/$1/run.log" 2>&1
  grep TB_RXBM3_SPCYC "$O/$1/run.log"
}
run base "-DOT_RXBM3_SRAM_SPLIT" & run form "-DOT_RXBM3_SRAM_SPLIT -DOT_RXBM3_SPCYC -DOT_S81_RM_STAGED" &
run mut "-DOT_RXBM3_SRAM_SPLIT -DOT_RXBM3_SPCYC -DOT_S81_RM_STAGED -DRXBM3_MUT_SPCYC" & wait
PY="docker run --rm --memory 4g -v $O:/w:ro -v $B:/b:ro -w /w python:3.12-slim python3 -I /b/compare_rxbm3_traces.py"
F1=$($PY base form 2 1 0); echo "FORM $F1"; M1=$($PY base mut 2 1 0); echo "MUT $M1"
if [[ "$F1" == *"-> PASS" && "$M1" == *"-> FAIL" ]]; then echo "RXBM3_SPCYC_GATE PASS"; else echo "RXBM3_SPCYC_GATE FAIL"; exit 1; fi
