#!/usr/bin/env bash
# MU-S81/SVC (10-18): per-user HBM bases on the dsdv_svc_rs 16-slice exact bench (tb_dsdv_svc_rs, TB-only MU mode; RTL
# unchanged).  Builds the protect-lib bench once (rs_bench_pl.sh, base variant: the mutants are TB plusargs), then runs:
#   single_u0   tail46 alone as user U0 (sb0 = SB0), +trace                        -> PASS, the single-user reference trace
#   mu          job 0 = tail46 as user U0 (SB0), job 1 = short300 as user U1 (SB1), both users' owned rows in ONE HBM image
#               and both users' window rings written by OWN_ROW, +trace            -> SVCRS_MU verdict=PASS, job-0 trace
#               lines identical (cycle and data) to single_u0
#   mut_sb      mu with job 1's WIN_LOAD SB = SB0 (user 0's compressed rows)     -> job 1 FAIL
#   mut_user    mu with job 1's WIN_LOAD user = U0 (user 0's window ring)        -> job 1 FAIL
#   single_u1   short300 alone as user U1 at SB1, +trace                          -> PASS (relocation reference for job 1)
#   default     tail46 with no MU plusargs                                        -> the committed single-user line
# Usage (repo root): tools/s81_dv/svc_rs/mu_bench.sh OUTDIR VECDIR
set -euo pipefail
O=$1; VEC=$2
U0=${U0:-0}; U1=${U1:-1}; SB0=${SB0:-1000}; SB1=${SB1:-a000}
START2=${START2:-8192}
export DIE=0 ST=0 SEEDS=1 SRAM_MACRO=1
tools/s81_dv/svc_rs/rs_bench_pl.sh "$O" "$VEC" base          # build only (no case)
BIN=$O/base_d0s0_m1/obj/Vtb_dsdv_svc_rs
R=$O/mu; mkdir -p "$R"
run() { local n=$1; shift; "$BIN" +seed=1 +static_io=1 +start2="$START2" "$@" > "$R/$n.log" 2>&1; }
PIDS=()
run single_u0 +dir="$VEC/tail46" +u0=$U0 +sb0=$SB0 +trace=1 & PIDS+=("$!")
run mu        +dir="$VEC/tail46" +u0=$U0 +sb0=$SB0 +dir2="$VEC/short300" +u1=$U1 +sb1=$SB1 +trace=1 & PIDS+=("$!")
run mut_sb    +dir="$VEC/tail46" +u0=$U0 +sb0=$SB0 +dir2="$VEC/short300" +u1=$U1 +sb1=$SB1 +mumut=1 & PIDS+=("$!")
run mut_user  +dir="$VEC/tail46" +u0=$U0 +sb0=$SB0 +dir2="$VEC/short300" +u1=$U1 +sb1=$SB1 +mumut=2 & PIDS+=("$!")
run single_u1 +dir="$VEC/short300" +u0=$U1 +sb0=$SB1 +tag0=5b +trace=1 & PIDS+=("$!")
run default   +dir="$VEC/tail46" & PIDS+=("$!")
STATUS=0
for p in "${PIDS[@]}"; do wait "$p" || STATUS=1; done
[ "$STATUS" = 0 ] || { echo "MU simulation process failed" >&2; exit 1; }
python3 tools/s81_dv/svc_rs/check_mu.py "$R" --start2 "$START2"
