# summarise escape_drt.py output: pins under an M5 PG strap (escape_check.py criterion) and whether DRT routed them
import sys, json, collections
pins, straps = [], []
for l in open(sys.argv[1]):
    f = l.split()
    if f[0] == "STRAP": straps.append(tuple(map(float, f[3:7]))); continue
    pins.append(dict(inst=f[0], pin=f[1], net=f[2], layer=f[3], box=list(map(float, f[4:8])), T=f[8][2:].split(",") if f[8][2:] else [], V=f[9][2:].split(",") if f[9][2:] else []))
out = collections.Counter(); bad = []
for p in pins:
    bx = p["box"]
    p["under"] = any(s[0] < bx[2] and bx[0] < s[2] and s[1] <= bx[3] + 8.64 and s[3] >= bx[1] - 8.64 for s in straps)
    routed = bool(p["T"])
    out[("under" if p["under"] else "free", "routed" if routed else "UNROUTED")] += 1
    if not routed: bad.append(p)
r = dict(n_pins=len(pins), n_under_m5_strap=sum(p["under"] for p in pins), counts={"%s/%s" % k: v for k, v in out.items()},
         under_via_at_pin=sum(1 for p in pins if p["under"] and p["V"]), unrouted=bad[:20])
json.dump(r, open(sys.argv[2], "w"), indent=1); print(json.dumps({k: v for k, v in r.items() if k != "unrouted"}))
