#!/bin/bash
set -eu
L=${1:?label}; shift
O=${OUT:?out}/$L
cd "${SRC:-.}"
mkdir -p "$O"
export OT_ORFS_NUM_CORES=16 OT_FS_MARGIN=1
export OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
python3 tools/s81/run_pq_r128_expanded.py --work "$O/work_c1r128_expanded" --output "$O/c1r128_expanded.json" "$@" > "$O/run.log" 2>&1
if [[ " $* " != *"--pnr-stop-after"* ]]; then
  python3 physical/s81_pq_r128_expanded/terminal.py "$O" c1r128_expanded > "$O/terminal.log" 2>&1
fi
