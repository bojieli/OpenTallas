#!/bin/bash
set -u
r=/srv/opentallas-scratch2/scratch/codex/su64-sta-recovery-2f22d245c
cd "$r/src"
/usr/bin/time -v python3 tools/w18/corner_sta.py --orfs-dir "$r/orfs" --post-sdc physical/hbm_su_c12/signoff_833_io150.sdc --post-sdc physical/hbm_su_div64/full_generated_clocks_candidate.sdc --post-sdc physical/hbm_su_div64/propagate_signoff.sdc --output "$r/corner_sta.json" > "$r/sta.log" 2> "$r/time.log"
echo $? > "$r/exit"
