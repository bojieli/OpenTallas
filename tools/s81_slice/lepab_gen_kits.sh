#!/usr/bin/env bash
set -euo pipefail
for k in s81sl_lepab_r1a s81sl_lepab_r1b dscoll_lane_w_s12g dscoll_lane_w_s12h dscoll_lane_e_s12g dscoll_lane_e_s12h;do
 python3 tools/ref_tile/ref_tile.py gen "physical/ref_tile/$k/spec.json"
done
