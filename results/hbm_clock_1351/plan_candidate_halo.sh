#!/bin/bash
set -eu
D=/srv/opentallas-scratch2/claude/codex-hbm-clock-1351
python3 /srv/opentallas-scratch2/claude/wt/codex-hbm-clock-1351/tools/die_plan/core_infra_htree.py "$D/vmdel_proposed_geo.txt" "$D/vmdel_centre_halo.tcl" --libtt "$D/libtt.lib" --libff "$D/libff.lib" --r6 --no-pad --macro-vertical-pass --islands '17.28,28.08;17.28,84.24;133.92,28.08;133.92,84.24' --nb 4,4,4,4 --cap-balance --leaf-n 4 --smax 150 --keepout 25.92,4.32,129.384,54.024 --keepout 25.92,56.7,129.384,106.404
