#!/usr/bin/env python3
"""DIE-KV-72 11-05: kv3_pv_v8 pilot stopped in global place (OT_CLAND no legal site, collector rst_n_t153): the density taps t139, t152, t153, t156
sit inside landing ring bands, and each tap's collector and relay flops are placed at the tap. This event adds the type's 18 landing bands as
clock.keepouts_um, so tap_clear and reset_tree site them off the bands; the collector entries then follow with geom93_1031/delta_geom93_coll.py.
usage (repo root): event.py PLAN_IN PLAN_OUT"""
import json, re, sys
a, b = sys.argv[1:3]
TN = "kv3_pv_v8"
text = open(a).read()
raw = json.loads(text)
t = raw["partition_types"][TN]
ck = t["clock"]
assert not ck.get("keepouts_um")
ck["keepouts_um"] = [v["rect_um"] for v in ck["landing_contract"]["bands"].values()]
mm = re.search(r'^  "' + TN + r'": ', text, re.M)
_, j = json.JSONDecoder().raw_decode(text, mm.end())
text = text[:mm.end()] + json.dumps(t, indent=1).replace("\n", "\n  ") + text[j:]
assert json.loads(text) == raw
open(b, "w").write(text)
print(TN, "keepouts_um", len(ck["keepouts_um"]))
