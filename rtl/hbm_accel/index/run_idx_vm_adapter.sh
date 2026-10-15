#!/bin/bash
# run_idxad.sh <out> <MUT> [+MODE1]
cd "$(dirname "$0")/../../.." && O=$(realpath -m $1); M=$2; shift 2; mkdir -p $O
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-INITIALDLY -GMUT=$M --top-module tb_hbm_idx_vm_adapter -Mdir $O/obj rtl/hbm_accel/index/ot_hbm_idx_vm_adapter.sv rtl/hbm_accel/index/tb_hbm_idx_vm_adapter.sv -j 4 > $O/build.log 2>&1 || { tail -30 $O/build.log; exit 2; }
$O/obj/Vtb_hbm_idx_vm_adapter "$@" > $O/run.log 2>&1; tail -4 $O/run.log
grep -q "IDX_VM_ADAPTER PASS" $O/run.log
