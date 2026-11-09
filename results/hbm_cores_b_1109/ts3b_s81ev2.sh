#!/bin/bash
set -eu
B=/srv/opentallas-scratch3/claude/type-safe-3b
cd $B
P=src_s81p/physical/die_plan/s81/plan_h2_2249.json
python3 -I - <<PY
import json,os
d=json.load(open("$B/base_v3b.json"))
with open("$B/s81_bound.tsv","w") as o:
    for t,v in d["partition_types"].items():
        p=f"$B/s81_cbind3b_rtl/{v.get('module',t)}.sv"
        assert os.path.exists(p),p
        o.write(f"{t}\t{p}\n")
PY
rm -f $P
prlimit --as=48000000000 python3 -I -B tools/die_plan/ts_relay_event.py $B/base_v3b.json $B/$P $B/s81p/s81_v3b_ts3_event.json --pins-root $B/src_s81p/physical/die_plan/s81 --bound-list $B/s81_bound.tsv --skip-types "$(cat $B/signed_s81.txt)" --regen-latency 2>&1 | tail -n 4 | cut -c1-400
python3 -I - <<PY
import json,hashlib
from collections import Counter
e=json.load(open("$B/s81p/s81_v3b_ts3_event.json"))
print(e["base_plan_sha256"][:12],e["plan_output_sha256"][:16],e["totals"],sorted(Counter(e["pin_cycle_deltas"].values()).items()),e.get("latency_regen"))
print("reported",Counter(r["action"][:40] for r in e["reported"]).most_common(3))
d=json.load(open("$B/s81p/asbuilt_ts3.json"))
d["internal_stations_types"]=sorted(e["native_out_types"]);json.dump(d,open("$B/s81p/asbuilt_ts3.json","w"),indent=1);print(len(d["internal_stations_types"]))
PY
rm -f $B/s81p/bind/bind_report.json $B/s81p/bind.log
chmod a-w $B/$P
