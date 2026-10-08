#!/bin/bash
# BF native pair (PINREG=1, HITFIX=1) route for the closure loop.  The flow repairs SETUP at the SS (WC) corner: bf_m2 ran
# with --hold-corners BC, so ORFS CORNERS=BC and every repair (place, CTS, GRT) timed the FF libraries; its SS sign-off
# found -605.6 on 32k endpoints.  Here ORFS runs WC only; the route IO follows the MEASURED SS insertion
# (CK_SS_MEAN; default bf_m1's 1032 ps): in max = ss+250, in min = ss-50, out max = 100-(ss-150), out min = -(ss+50)
# (hold at WC against the SS insertion); FF hold is signed off by signoff_ref.sdc and repaired post-route at FF.
# usage: OUT=<dir> SRC=<src root> route_cl.sh <label> [extra run_abi3_physical args, e.g. --pnr-stop-after cts]
set -o pipefail
L=${1:?label}; shift; S=${SRC:-.}; O=${OUT:?out}/$L; mkdir -p $O; cd $S
SS=${CK_SS_MEAN:-1032}
export OT_ORFS_NUM_CORES=16 OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
echo "$(date -Is) START $(hostname) ss=$SS args=$*" >> $O/MANIFEST
python3 tools/s81/run_bf_native_physical.py --margin --wc-only --hitfix --work $O/work --output $O/physical.json --util 45 \
  --tag $L --ins-ss $SS --ins-ff $SS --extra="$*" > $O/run.log 2>&1; rc=$?
echo "rc=$rc" > $O/exit
if [ $rc -eq 0 ] && [[ " $* " != *"--pnr-stop-after"* ]]; then
  python3 tools/w18/corner_sta.py --orfs-dir $O/work/orfs --macro physical/asap7_memory_macros_v2/ot_rom_4096x274_m8 \
    --post-sdc physical/s81_native_bf/margin/signoff_ref.sdc --output $O/corner_sta.json > $O/sta.log 2>&1; echo "corner_rc=$?" >> $O/exit
fi
