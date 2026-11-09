/home/ubuntu/.local/bin/ot-run --status </dev/null 2>/dev/null | head -3 | tr '|' '\n' | cut -c1-170
cd /srv/opentallas-scratch2/claude/kw36/wt_e/tools/autopilot
sed -n 802,870p kit_wave.py | cut -c1-200
sed -n 1,12p /home/ubuntu/.local/bin/ot-run | cut -c1-260
python3 -I - <<'PY'
import json
d=json.load(open("/home/ubuntu/coord/autopilot/kit_wave_state.json"))
from collections import Counter
print(Counter((v.get("die"),v.get("status")) for v in d["items"].values() if v.get("status") in("RUNNING","RETRY-INFRA")))
c=json.load(open("/home/ubuntu/coord/autopilot/kit_wave.json"))
print({k:c.get(k) for k in("max_inflight","max_launch_per_tick","die_max_inflight","gen_disk_min_gb","root_floor_gb","root_gen_room_gb","load_hold")})
for k,v in c["dies"].items(): print(k,v.get("die_max_inflight"),v.get("max_inflight"),v.get("max_launch_per_tick"),v.get("stop"),v.get("enabled"))
PY
