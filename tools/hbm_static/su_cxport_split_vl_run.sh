#!/bin/bash
# CX-IJ 10-18: cxport split (4 dl + ij + rc leaves, dl/rc/ij one-root halves) lockstep vs the hub on Verilator (the
# closure daemon pins 5.050; ot-heavy puts it first on PATH). usage: OUT [QID B39 MUT MUTONE]
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); q=${2:-2}; b=${3:-0}; mut=${4:-0}; one=${5:-0}; mkdir -p "$out"
C=rtl/hbm_accel/generic/adapters/static_su/collport
T=tb_hbm_su_cxport_split
verilator --version
verilator --binary --timing -j "${OT_THREADS:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module $T \
 -GQID=$q -GB39=$b -GMUT=$mut -GMUTONE=$one --Mdir "$out/obj" -o cx \
 $C/ot_hbm_su_static_cxport.sv $C/ot_hbm_su_static_cxport_split.sv $C/tb_hbm_su_cxport_split.sv > "$out/build.log" 2>&1 \
 || { tail -30 "$out/build.log"; exit 1; }
"$out/obj/cx" | tee "$out/bench.log" | tail -8
