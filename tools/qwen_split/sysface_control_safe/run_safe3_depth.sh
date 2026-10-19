#!/bin/bash
# QW-SYSFACE3 fleet step A (isolated source copy via ot-run): functional SAFE3 graphs + generic depth census.
set -u
export PATH=$HOME/.local/opentallas-tools/yosys-0.68/bin:$PATH
rc=0
for p in ${PROFILES:-cold3 legacy3}; do
 python3 tools/qwen_split/sysface_control_safe/build_profile.py --profile "$p" --out "$p" || exit 2
 /usr/bin/time -v yosys -Q -s "$p/synth.ys" > "$p/synth.log" 2> "$p/synth.time" || { echo "SYNTH_FAIL $p"; tail -20 "$p/synth.log"; exit 3; }
 python3 tools/qwen_split/sysface_control_safe/depth_census.py "$p/original.json" --out "$p/depth_census.json" || rc=1
done
exit $rc
