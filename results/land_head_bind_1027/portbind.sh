#!/bin/bash
# strict port-bind (tools/die_port_bind.py, NO STUBS rule) of a generated HEAD die top.  usage: portbind.sh GEN
set -u
R=/srv/opentallas-scratch2/claude/land-head-bind-1
W=/srv/opentallas-scratch2/claude/wt/land-head-bind-1
g=$1
cd "$W"
python3 -I tools/die_port_bind.py "$R/$g/s81_head_top.sv" --top s81_head_top -f "$R/${g}_lint.f" \
    --strap-file "$R/straps.json" --out "$R/$g.portbind.json" > "$R/$g.portbind.txt" 2>&1
echo "portbind rc=$?" >> "$R/$g.portbind.txt"
