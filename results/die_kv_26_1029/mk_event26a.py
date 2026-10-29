# DIE-KV-26 plan event26a (COORD ruling A on DIE-KV-25 ASK, 10-29 05:47): KV drops early core taps this release.
# event26 -> event26a: every type with clock.core_taps == "early" gets core_taps = "internal" (cores keep the
# partition-internal common latency 250 TT / 202.5 FF, 12.3; same form as s81_head/head_regional_one_entry.py).
# Nothing else changes (no RTL change); clock.taps entries are kept as declarations.
import json, sys, hashlib
src, dst = sys.argv[1], sys.argv[2]
raw = open(src, "rb").read(); P = json.loads(raw)
moved = []
for tn, t in sorted(P["partition_types"].items()):
    ck = t.get("clock") or {}
    if ck.get("core_taps") == "early":
        ck["core_taps"] = "internal"; moved.append(tn)
P["note"] = (P.get("note", "") + " | DIE-KV-26 event26a: core_taps early->internal on %d types (COORD ruling A 10-29 05:47, 12.17 closure-first)" % len(moved))
open(dst, "w").write(json.dumps(P, indent=1, sort_keys=False))
json.dump(dict(schema="kv_event26a/1", src=src, src_sha256=hashlib.sha256(raw).hexdigest(), types_moved=moved, n=len(moved)),
          open(dst.replace(".json", "_event.json"), "w"), indent=1)
print("moved", len(moved))
