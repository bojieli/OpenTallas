#!/bin/bash
# CBC-RULES-1119 (COORD r713 fallback): hourly post of the CBC-FALLBACK families (owners_sweep.py --cbc-post).  Read-only on
# coord state except the post (bin/post.sh).  Writes its sweep table to ~/.local/state, never lanes/OWNERS-SWEEP.tsv.
cd / || exit 1
st=$HOME/.local/state; mkdir -p "$st"
out=$(timeout 600 python3 -I "$HOME/coord/bin/owners_sweep.py" --out "$st/cbc-fallback-sweep.tsv" --cbc-post 2>&1) || exit 0
cnt=$(printf '%s\n' "$out" | grep -E '^[A-Z0-9]+ CBC-FALLBACK [0-9]+' | awk '{printf "%s %s types; ", $1, $3}')
line=$(printf '%s\n' "$out" | grep '^CBC-POST ' | head -1 | sed 's/^CBC-POST //')
[ -n "$line" ] || exit 0
msg="HOURLY [CBC-RULES-1119 -> COORD; cc S81-DIE-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned ${cnt}${line:0:1800}"
bash "$HOME/coord/bin/post.sh" CBC-RULES-1119 "$msg" >> "$st/cbc-fallback-post.log" 2>&1
