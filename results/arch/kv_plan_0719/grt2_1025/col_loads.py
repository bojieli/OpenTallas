"""per N-S boundary channel loads in hg/hgi columns, die-frame core projection, at a die share."""
import json, sys, collections
sys.path.insert(0, sys.argv[2] + "/tools/die_plan")
from pathlib import Path
import schema as S
raw = json.load(open(sys.argv[1])); P = S.Plan(raw, Path(sys.argv[1]).resolve())
CAP = 0.25 * (1 / 0.048 + 1 / 0.064)
parts = {p["name"]: p for p in raw["partitions"]}
def xspan(n):
    t = raw["partition_types"][parts[n]["type"]]; w, h = t["outline_um"]
    o = parts[n]["origin_um"]; orient = parts[n].get("orient", "R0")
    a = P.to_die(n, (0, 0)); b = P.to_die(n, (w, h)); return min(a[0], b[0]), max(a[0], b[0]), min(a[1],b[1]), max(a[1],b[1])
def cores_x(n):
    t = raw["partition_types"][parts[n]["type"]]; out = []
    for c in t.get("hard_cores", []):
        x0, y0 = c["origin_um"]; w, h = c["outline_um"]
        if c.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"): w, h = h, w
        a, b = P.to_die(n, (x0, y0)), P.to_die(n, (x0 + w, y0 + h))
        if w > 100 and h > 100: out.append((min(a[0], b[0]), max(a[0], b[0])))
    return sorted(set((round(a, 2), round(b, 2)) for a, b in out))
def chans(n):
    lo, hi, _, _ = xspan(n); cur = lo; out = []
    for a, b in cores_x(n):
        if a > cur + 1: out.append((cur, a))
        cur = max(cur, b)
    if hi > cur + 1: out.append((cur, hi))
    return out
res = {}
for col in sys.argv[3].split(","):
    for r in range(7):
        a, b = f"{col}_{r}", f"{col}_{r+1}"
        if a not in parts or b not in parts: continue
        ch = chans(a); chb = chans(b)
        ld = collections.Counter(); who = collections.defaultdict(list)
        for pr in raw["ports"]:
            if {pr["src"]["part"], pr["dst"]["part"]} != {a, b} or "window_um" not in pr: continue
            m = sum(pr["window_um"]) / 2
            k = next((i for i, (u, v) in enumerate(ch) if u - 1 <= m <= v + 1), -1)
            ld[k] += pr["width"]; who[k].append(pr["id"].split("_")[0] + f":{pr['width']}")
        res[f"{a}|{b}"] = {str(k): dict(chan=[round(x, 1) for x in ch[k]] if k >= 0 else None, bits=v,
                         util=round(v / ((ch[k][1] - ch[k][0]) * CAP), 3) if k >= 0 else None, who=who[k])
                         for k, v in sorted(ld.items())}
        if chb != ch: res[f"{a}|{b}"]["chan_mismatch"] = [ch, chb]
json.dump(res, open(sys.argv[4], "w"), indent=1)
for k, v in res.items():
    print(k, " ".join(f"{c}:{x['bits']}/{x['util']}" for c, x in v.items() if c != "chan_mismatch"), "MISMATCH" if "chan_mismatch" in v else "")
