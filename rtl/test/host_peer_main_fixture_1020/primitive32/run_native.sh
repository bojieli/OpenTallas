#!/bin/bash
set -eu
libs=();for f in real5/*;do libs+=(--liberty "$f");done
python3 native_census.py --netlist resynth.v --top qkd_hr_core_peer_n32 "${libs[@]}" --out native_resynth.json
