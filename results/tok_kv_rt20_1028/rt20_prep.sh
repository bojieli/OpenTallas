#!/bin/bash
set -u
W=/srv/opentallas-scratch2/claude/wt/tok-kv-rt20
O=/srv/opentallas-scratch2/claude/tok-kv-rt20-1028
S2=/srv/opentallas-scratch2/claude/die-kv-8-1028/bind_s2
cd "$W"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH PYTHONDONTWRITEBYTECODE=1
H=$W/physical/die_plan/qwen_kvsys/boot_v36
AS=$O/in/codex-kv-image-1027b/asbuilt_rtl6
set -a; . "$AS/kv_flags.env"; set +a
export OT_KV_RETIRE_SUCCESSOR=$AS/health_successor.json OT_KV_RETIRE_LOGICAL=1
for n in s2:$S2 b4:$O/in/bind4; do t=${n%%:*}; b=${n#*:}
python3 "$H/kv_boot_v36.py" prep --rs "$AS/relay_stages.json" --model "$AS/static_model.json" --groups "$b/bus_groups.json" --out "$O/prep_$t" > "$O/prep_$t.log" 2>&1
echo "PREP_${t}_RC=$?"
done
python3 physical/die_plan/qwen_kvsys/boot_v36/kst.py "$S2/bus_groups.json" > "$O/kst_s2.txt"; echo KST_RC=$?
