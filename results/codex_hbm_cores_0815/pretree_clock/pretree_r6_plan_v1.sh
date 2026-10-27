#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-cores-0815/pretree_clock
python3 planner39.py geo2.txt pretree_r6_nativeRC.tcl --libtt libs2/buf_TT.lib --libff libs2/buf_FF.lib --islands '42.12,60.48;42.12,181.44;122.04,60.48;122.04,181.44' --nb 8,8,8,8 --leaf-n 8 --r6 --no-pad --smax 150 --rc 1.15674,0.66118 --sta-dir sta_r6_nativeRC
