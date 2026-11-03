#!/bin/bash
# T7 bound elaboration lint (TOK-DS-3): original, LAND-only (from original), PMEM+PVQ+LAND (from joint).
set -uo pipefail
ulimit -c 0
D=$(cd "$(dirname "$0")" && pwd); cd "$D"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
DEF="-DSYNTHESIS -DS81CTRL_SRAM_FIFO -DS81CTRL_SRAM_P192 -DS81CTRL_NATIVE32 -DOT_S81ENG_TAP_N32R2 -DOT_SVC_ALLQ -DSU_SMU_T -DOT_ATTN_HCORE -DOT_S81ENG_RR_N32 -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED"
BOUND=$(grep 't7_bound.sv$' sim.f)
run() { # name boundfile extra...
  local n=$1 b=$2; shift 2
  grep -v 't7_bound.sv$' sim.f > "$n.f"; echo "$b" >> "$n.f"; for x in "$@"; do echo "$D/$x" >> "$n.f"; done
  /usr/bin/time -v "$V" --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN $DEF --top-module s81p_svc_lo_dsdv_svc_rs__t7 -f "$n.f" > "$n.log" 2> "$n.err"
  echo "$n rc=$? errors=$(grep -c '%Error' "$n.err") warnings=$(grep -c '%Warning' "$n.err")" | tee -a summary.txt
}
: > summary.txt
#run original "$BOUND"
run landonly "$D/landcut_s81_T7_pmem_bound_cut_0900_native_parent.sv" ot_t7_land_capture_candidate.sv
#run jointpre "$D/joint_pre.sv" ot_t7_pmem_capture_candidate.sv ot_t7_pvq_capture_candidate.sv
run jointland "$D/landcut_s81_T7_pvq_bound_cut_1040_PMEM_PVQ_joint_bound.sv" ot_t7_pmem_capture_candidate.sv ot_t7_pvq_capture_candidate.sv ot_t7_land_capture_candidate.sv
