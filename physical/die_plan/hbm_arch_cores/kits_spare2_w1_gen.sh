#!/bin/bash
cd /srv/opentallas-scratch2/claude/wt/kits-spare2-w1/physical/die_plan/hbm_arch_cores || exit 9
v=$1
python3 -E -s gen_core_kit_hbm.py --views views_b2n.json --view "$v" --out /srv/opentallas-scratch2/claude/kits-spare2/w1/gen --hold-margin 0 --face-shell on --face-shell-drop off --core-insertion none --clock-taps density
