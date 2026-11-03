"""DIE-S81-49 11-02 S81 rtobs/tap census of a plan with the tools of a tree (plan as given, no override):
grid+explicit / explicit tap legality (taps.grid_explicit_taps / explicit_taps) on every type, and published landing collector_tree relays vs
reset_tree.for_type.   usage: census.py TOOLS_ROOT PLAN [OUT.json]"""
import sys, json
W, pl = sys.argv[1:3]
sys.path.insert(0, W + "/tools/die_plan")
import schema as S, taps, reset_tree as RT
raw = S.load(pl); P = S.Plan(raw, pl)
def key(rs):
    return sorted((r.get("q"), r.get("d"), round(float(r["xy"][0]), 3), round(float(r["xy"][1]), 3)) for r in rs)
tap_bad, ct_bad, ct_n, ok = [], [], 0, 0
for tn in sorted(P.types):
    t = P.types[tn]
    mode = (t.get("clock") or {}).get("tap_mode")
    if mode in ("grid+explicit", "explicit"):
        try:
            (taps.explicit_taps if mode == "explicit" else taps.grid_explicit_taps)(P, tn)
        except Exception as e:
            tap_bad.append([tn, str(e)[:300]])
    ct = ((raw["partition_types"][tn].get("clock") or {}).get("landing_contract") or {}).get("collector_tree")
    if ct and not t.get("hard"):
        ct_n += 1
        if key(RT.for_type(P, tn).get("relays", [])) != key(ct["relays"]):
            ct_bad.append(tn)
rep = dict(plan=pl, tools=W, types=len(P.types), tap_ok=len(P.types) - len(tap_bad), tap_bad=tap_bad,
           collector_tree=ct_n, collector_tree_match=ct_n - len(ct_bad), collector_tree_mismatch=ct_bad)
if len(sys.argv) > 3:
    json.dump(rep, open(sys.argv[3], "w"), indent=1)
print(json.dumps(dict((k, v) for k, v in rep.items() if k not in ("plan", "tools"))))
