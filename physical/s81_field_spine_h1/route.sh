#!/bin/bash
# usage: OUT=<dir> SRC=<src> route.sh <label> <R> <geom> [--pnr-stop-after cts]   (tag c1r<R>_h1<geom>)
set -eu
L=${1:?label}; R=${2:?R}; G=${3:?geom}; shift 3
T=c1r${R}_h1${G}
O=${OUT:?out}/$L
cd "${SRC:-.}"
mkdir -p "$O"
export OT_ORFS_NUM_CORES=16 OT_FS_MARGIN=1
export OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
python3 tools/s81/run_field_spine_h1.py --R "$R" --geom "$G" --work "$O/work_$T" --output "$O/$T.json" "$@" > "$O/run.log" 2>&1
if [[ " $* " != *"--pnr-stop-after"* ]]; then
  python3 physical/s81_pq_r128_expanded/terminal.py "$O" "$T" > "$O/terminal.log" 2>&1
fi
