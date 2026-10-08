#!/bin/bash
# Native BF pair MARGIN route (owner margin-first rule 2026-10-06): PINREG=1, routed at 770 ps with the die IO budget on a
# slot-width die (1002.888 x 190.08), signed off at 833.333 ps by tools/w18/corner_sta.py --post-sdc. Accept SS >= +40 / FF >= +15.
# Usage: route.sh <source root (clean checkout)> <out dir>
set -o pipefail
S=${1:?src}; O=${2:?out}; mkdir -p $O; cd $S
export OT_ORFS_NUM_CORES=16 OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
echo "$(date -Is) START $(hostname) $(cat SOURCE_COMMIT 2>/dev/null)" >> $O/MANIFEST
python3 tools/s81/run_bf_native_physical.py --margin --work $O/work --output $O/physical.json --util 45 --tag s81_bf_margin2 --ins-ss 1032 --ins-ff 556 > $O/route.log 2>&1; echo $? > $O/route.exit
python3 tools/w18/corner_sta.py --orfs-dir $O/work/orfs --macro physical/asap7_memory_macros_v2/ot_rom_4096x274_m8 \
  --post-sdc physical/s81_native_bf/margin/signoff_833_m2.sdc --output $O/corner_sta.json > $O/sta.log 2>&1; echo $? > $O/sta.exit
echo "$(date -Is) END route=$(cat $O/route.exit) sta=$(cat $O/sta.exit)" >> $O/MANIFEST
touch $O/DONE
