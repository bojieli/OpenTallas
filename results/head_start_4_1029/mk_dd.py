"""HEAD-START-4 V1 input: per start port MEASURED START data delay [dd_min_FF, dd_max_TT] (HEAD-START-3 sta/dd_rows: launch
CLK -> capture D, report_checks on the routed r1 vehicle, GRT RC, TT max incl x1.10/x1.05 droop, FF min) keyed by the
plan port of the capture stage region, + a bounding hop model for unmeasured (candidate / part-capture) ports.
usage: mk_dd.py dd_rows.json start_stages.json plan.json out.json"""
import json
import statistics as S
import sys

rows = json.load(open(sys.argv[1]))["rows"]
st = {s["id"]: s for s in json.load(open(sys.argv[2]))["stages"]}
plan = json.load(open(sys.argv[3]))
P = {g["region"]: g for g in plan["regions"]}
ports, bad = {}, 0
for r in rows:
    s = st.get(r["cap"])
    sf = (P.get(s["region"]) or {}).get("start_from") if s else None
    if not sf or r["dd_max_TT"] is None or r["dd_min_FF"] is None:
        bad += 1
        continue
    lo, hi = r["dd_min_FF"], r["dd_max_TT"]
    o = ports.get(sf["port"])
    ports[sf["port"]] = [lo, hi] if o is None else [min(o[0], lo), max(o[1], hi)]
H = [(r["hop_um"], r["dd_min_FF"], r["dd_max_TT"]) for r in rows if r.get("hop_um") and r["dd_max_TT"] is not None]


def slope(i):
    xs = [h[0] for h in H]
    ys = [h[i] for h in H]
    mx, my = S.mean(xs), S.mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


bl, bh = slope(1), slope(2)
al = min(l - bl * h for h, l, _ in H)      # bounding envelope: lo below every measured row
ah = max(u - bh * h for h, _, u in H)      # hi above every measured row
doc = dict(basis="MEASURED HEAD-START-3 sta/dd_rows (routed r1 vehicle, report_checks -to D; lo = FF min, hi = TT max "
                 "incl droop); model = bounding linear envelope over hop_um of the same rows (UNCHECKED for unmeasured "
                 "ports)",
           ports=ports, model=dict(lo_ps=[round(al, 1), round(bl, 4)], hi_ps=[round(ah, 1), round(bh, 4)]),
           stats=dict(rows=len(rows), ports=len(ports), unmapped=bad, fit_rows=len(H)))
json.dump(doc, open(sys.argv[4], "w"), indent=0, sort_keys=True)
print(json.dumps(dict(doc["stats"], model=doc["model"])))
