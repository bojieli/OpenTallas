#!/bin/bash
# fg_raw.sh KIT: the kit's face_guard_core.py (main face_guard.py beside it, no pair lines) on the RAW Yosys netlist
cd "$1" || exit 2
TOP=$(sed -n 's/^export DESIGN_NAME = //p' config.mk); SKIP=$(cat face_guard_skip.txt)
N=$(ls run/results/asap7/*/base/1_2_yosys.v | tail -1)
python3 -I face_guard_core.py "$N" "$TOP" "$SKIP" pins.json face_guard_raw.json > face_guard_raw.log 2>&1; rc=$?
echo "$(basename $1) rc=$rc $(head -2 face_guard_raw.log | tr '\n' ' ') md5(face_guard.py)=$(md5sum < face_guard.py | cut -c1-8) pairs=$(grep -c '^pair' ft_stations.txt) post_synth=$(grep -c POST_SYNTH config.mk)"
