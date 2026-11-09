#!/bin/bash
# run ON epyc2: stage private src + elab reuse for the S81 v3b + TS3 relay proof bind
set -eu
B=/srv/opentallas-scratch3/claude/type-safe-3b
mkdir -p $B/s81p/bind
cd $B
R=$(readlink -f /srv/opentallas-scratch3/claude/kw35/src_c303p)
test -L "$R" && { echo symlink src; exit 3; }
[ -d src_s81p ] || cp -al "$R" src_s81p
find src_s81p -type d -exec chmod u+w {} +
P=src_s81p/physical/die_plan/s81/plan_h2_2249.json
rm -f "$P"
scp -q -o ControlPath=none epyc4:/srv/opentallas-scratch2/claude/type-safe-3b/s81_v3b_ts3.json "$P"
scp -q -o ControlPath=none epyc4:/srv/opentallas-scratch2/claude/type-safe-3b/s81_v3b_ts3_event.json s81p/
chmod a-w "$P"
sha256sum "$P" | cut -c1-16
A0=/srv/opentallas-scratch3/claude/codex-wave-bind-1106/src_28fc7/physical/die_plan/s81/bind
python3 -I - <<P2
import json
d=json.load(open("$A0/asbuilt_b178_coll_h2_2249.json"))
e=json.load(open("$B/s81p/s81_v3b_ts3_event.json"))
d["base"]="/srv/opentallas-scratch3/claude/codex-wave-bind-1106/src_28fc7"
d["map_file"]="$A0/"+d["map_file"]
d["internal_stations_types"]=sorted(e["native_out_types"])
json.dump(d,open("$B/s81p/asbuilt_ts3.json","w"),indent=1)
print(len(d["internal_stations_types"]))
P2
