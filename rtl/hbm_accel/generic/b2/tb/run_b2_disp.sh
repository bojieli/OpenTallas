#!/bin/bash
# usage: run_b2_disp.sh <outdir> <tag> [DMUT RMUT N SEED]  (run from the repo root)
set -e
O=$1; T=$2; DM=${3:-0}; RM=${4:-0}; N=${5:-4000}; S=${6:-1}
B=rtl/hbm_accel/generic/b2
mkdir -p $O/$T
verilator --binary -j 8 -Wno-fatal -Wno-WIDTH -Wno-lint --timing -O2 --top-module tb_hgi_b2_disp -GDMUT=$DM -GRMUT=$RM \
  --Mdir $O/$T/obj $B/ot_hgi_b2_disp.sv $B/ot_hgi_b2_rq.sv $B/tb/tb_hgi_b2_disp.sv > $O/$T/build.log 2>&1 || { tail -30 $O/$T/build.log; exit 1; }
$O/$T/obj/Vtb_hgi_b2_disp +N=$N +SEED=$S > $O/$T/run.log 2>&1 || true
grep -E "B2DISP|FAIL" $O/$T/run.log | head -5; grep -q "B2DISP PASS" $O/$T/run.log
