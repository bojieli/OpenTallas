#!/bin/bash
set -u
r=/srv/opentallas-scratch/claude/embedding-sta-recovery-2f22d245c
cd "$r/src"
for kind in scale code; do
 /usr/bin/time -v python3 tools/w18/corner_sta_ref.py --orfs-dir "$r/$kind/orfs" --extra-sdc "$r/$kind/signoff.sdc" --macro physical/asap7_memory_macros/ot_rom_4096x266_m8 --output "$r/$kind/corner_sta.json" > "$r/$kind/sta.log" 2> "$r/$kind/time.log"
 echo $? > "$r/$kind/exit"
done
