#!/bin/bash
set -u
r=/srv/opentallas-scratch/claude/controller-sta-recovery-2f22d245c
cd "$r/src"
/usr/bin/time -v python3 tools/w18/corner_sta_ref.py --orfs-dir "$r/orfs" --extra-sdc "$r/signoff.sdc" --output "$r/corner_sta.json" > "$r/sta.log" 2> "$r/time.log"
echo $? > "$r/exit"
