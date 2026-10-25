#!/usr/bin/env python3
"""ELEM-S81 bind48 10-24: S81 v4.8 R8 landing table under the LANDED BUNDLES rule (847f8568f3, S81-P9-R8EQ).

main's tools/die_plan/r8.py lost the --landed options after 847f8568f3 (a later merge took the pre-rule r8.py), and
bind.py align_r8 checks a member's `asbuilt` against the bind's per-lane as-built depth.  So:
  1. the table is made with r8.py as of 847f8568f3 (git show 847f8568f3:tools/die_plan/r8.py, main schema.py):
     pads PLAN BUS_GROUPS --replica type --bus leaf --exempt '(?i)(^|_)(fault|flt)(_o|_q)?$'
          --landed '^(x|xo)_[WE][0-5]_' --landed '^xring__' --landed '^sid_s_'       (keep: 13 bundles over margin)
  2. this script restores each collapsed member's `asbuilt` to its per-lane as-built depth (`asbuilt_lane`, already the
     depth in the member id); pad / landed (the one bundle depth) are unchanged, so bind.py applies the rule's pads.
Usage: r8_landed_v48.py IN.json OUT.json"""
import json
import sys

js = json.load(open(sys.argv[1]))
n = 0
for m in js["members"]:
    if "asbuilt_lane" in m:
        m["asbuilt_bundle"] = m["asbuilt"]
        m["asbuilt"] = m.pop("asbuilt_lane")
        n += 1
js["note"] = js.get("note", "") + " | ELEM-S81 bind48: asbuilt restored to the per-lane depth for %d landed-bundle members " \
    "(bind/r8_landed_v48.py)" % n
json.dump(js, open(sys.argv[2], "w"), indent=0)
print(json.dumps(dict(members=len(js["members"]), restored=n, summary=js.get("summary"))))
