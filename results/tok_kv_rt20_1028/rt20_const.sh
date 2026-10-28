#!/bin/bash
set -u
W=/srv/opentallas-scratch2/claude/wt/tok-kv-rt20
O=/srv/opentallas-scratch2/claude/tok-kv-rt20-1028
S2=/srv/opentallas-scratch2/claude/die-kv-8-1028/bind_s2
Q=$O/in/fresh_v3
K4=$O/in/bind4
cd "$W"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH PYTHONDONTWRITEBYTECODE=1
for n in s2:$S2 b4:$K4; do t=${n%%:*}; b=${n#*:}
python3 tools/die_plan/regen_constants.py --die qwen_kvsys --bound "$b" --peer "$Q" --src-root "$W" --out-json "$O/kv_constants_$t.json" --out-sv "$O/kv_constants_$t.svh" > "$O/kv_constants_$t.log" 2>&1
echo "KV_CONSTANTS_${t}_RC=$?"
done
