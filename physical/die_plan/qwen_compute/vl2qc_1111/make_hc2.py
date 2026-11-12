"""VISLAYOUT2-QC sl_hc2 structural fix (AMENDMENT 4): the S-face b_hw_i 1573-b landing ring (8000 padded storage
flops) was reserved in a 272 x 45 um band at the face (100% of its area_reserve) -> GRT V overflow in the band rows.
Re-site: deepen the band to y1 = Y1 (default 103.68, 8.64 lattice) on the same x span, so the ring spreads at ~50%
and its pin/V-row demand per gcell halves.  Positions/band rect only, no cycle change.
usage: make_hc2.py BASE.json OUT.json DELTA.json [Y1]"""
import hashlib, json, sys
base, out, dout = sys.argv[1:4]
Y1 = float(sys.argv[4]) if len(sys.argv) > 4 else 103.68
raw = open(base, "rb").read(); p = json.loads(raw)
edits = []
for n, t in p["partition_types"].items():
    if "_hc2" not in n:
        continue
    b = t["clock"]["landing_contract"]["bands"]["b_hw_i"]
    was = list(b["rect_um"]); r = list(was); assert r[3] < Y1
    r[3] = Y1; b["rect_um"] = r
    b["resize"] = (b.get("resize", "") + "; VISLAYOUT2-QC 11-11: deepened to spread the 8000-flop ring (AMENDMENT 4)").lstrip("; ")
    edits.append(dict(type=n, path="clock.landing_contract.bands.b_hw_i.rect_um", was=was, now=r))
s = json.dumps(p, indent=1)
open(out, "w").write(s)
sha = hashlib.sha256(s.encode()).hexdigest()
json.dump(dict(base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, edits=edits), open(dout, "w"), indent=1)
print("hc2 edits", len(edits), "sha256", sha[:12])
