"""collect_kv.py KITDIR -> one JSON line: gate numbers of a routed G3 kit (ELEMQK-KV)."""
import json, sys, glob, re, os
k = sys.argv[1]; r = {"kit": k}
def j(p):
    try: return json.load(open(p))
    except Exception: return None
for n in ("face_guard", "face_guard_odb", "pin_audit"):
    d = j(f"{k}/{n}.json"); r[n] = (d or {}).get("verdict", "NOT RUN")
    if d and n == "pin_audit": r["pin_audit_detail"] = {x: d[x] for x in d if x not in ("pins", "rows", "detail")} if isinstance(d, dict) else None
L = (glob.glob(f"{k}/run/logs/asap7/*/base") or [""])[0]
r["grt_overflow"] = None
if os.path.exists(f"{L}/5_1_grt.log"):
    m = re.findall(r"^Total\s+\d+\s+\d+\s+[\d.]+%\s+\d+\s*/\s*\d+\s*/\s*(\d+)", open(f"{L}/5_1_grt.log").read(), re.M); r["grt_overflow"] = int(m[-1]) if m else None
d = j(f"{L}/5_2_route.json") or {}
r["drc"] = d.get("detailedroute__route__drc_errors"); r["antenna_nets"] = d.get("detailedroute__antenna__violating__nets")
s = j(f"{k}/signoff/signoff.json")
if s:
    c = s.get("checks", {}); r["signoff"] = s.get("verdict"); r["reasons"] = s.get("reasons")
    r["checks"] = {kk: {x: v.get(x) for x in ("verdict", "wns_ps", "tns_ps", "spread_ps", "count", "value") if x in v} for kk, v in c.items()}
else:
    r["signoff"] = "NOT RUN"
print(json.dumps(r))
