#!/bin/bash
# bf-arch hierarchical BF block route (closure loop recipe; same structure as s81_native_bf/margin/route_var.sh).
# usage: OUT=<dir> SRC=<src root> BLOCK=col|front route_hier.sh <label> [run_bf_hier_physical args]
set -o pipefail
L=${1:?label}; shift; S=${SRC:-.}; O=${OUT:?out}/$L; mkdir -p $O; cd $S
B=${BLOCK:?BLOCK=col|front}; SS=${CK_SS_MEAN:-841}
export OT_ORFS_NUM_CORES=16 OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
POST="--post-sdc ${SIGNOFF_SDC:-physical/s81_native_bf/margin/signoff_ref.sdc}"
echo "$(date -Is) START $(hostname) block=$B ss=$SS args=$*" >> $O/MANIFEST
python3 tools/s81/run_bf_hier_physical.py --block $B --period ${PER:-.730} --work $O/work --output $O/physical.json \
  --tag $L --ins-ss $SS "$@" > $O/run.log 2>&1; rc=$?
echo "rc=$rc" > $O/exit
if [ $rc -eq 0 ]; then
  python3 tools/w18/corner_sta.py --orfs-dir $O/work/orfs --macro physical/asap7_memory_macros_v2/ot_rom_4096x274_m8 \
    $POST --output $O/corner_sta.json > $O/sta.log 2>&1; echo "corner_rc=$?" >> $O/exit
fi
