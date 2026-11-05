#!/usr/bin/env bash
# compile the already-verilated lockstep model wide, then run the gate (run_lock.sh skips an existing binary)
O=$1; J=${2:-48}
make -j"$J" -C "$O/lock/obj" -f Vtb_dsdv_idx_rg3.mk OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O1 > "$O/lock/make.log" 2>&1 \
  || { echo "IDXLOCK_GATE FAIL make"; tail -5 "$O/lock/make.log"; exit 2; }
exec bash results/rtl/s81_svc_idx_fit_1103/run_lock.sh "$O" 7
