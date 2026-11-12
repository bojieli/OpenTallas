"""SC-REFLOOR-1: landing bands of sc types + die neighbourhood of sc instances + lanes whose route crosses sc."""
import json, sys, collections
p = json.load(open(sys.argv[1]))
T = p["partition_types"]
for n in ("sle_sc_v1__cl115da35f", "sle_sc_v2", "slw_sc_v2"):
    lc = ((T[n].get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
    print(f"== {n} landing bands {len(lc)}")
    tb = 0
    for bn, bd in lc.items():
        tb += float(bd.get("width") or 0)
        print(f"  {bn:<18} rect={bd.get('rect_um')} w={bd.get('width')} flops={bd.get('padded_data_storage_flops') or bd.get('live_data_storage_flops')} face={bd.get('face')}")
    print("  ring bits total", tb)
    print("  clock keys", list((T[n].get("clock") or {}).keys()))
parts = {q["name"]: q for q in p["partitions"]}
def rect(q):
    W, H = T[q["type"]]["outline_um"]
    o = q.get("orient", "R0")
    if o in ("R90", "R270", "MXR90", "MYR90"):
        W, H = H, W
    x, y = q["origin_um"]
    return (x, y, x + W, y + H)
for sn in ("sl_W3_sc", "sl_E1_sc"):
    r0 = rect(parts[sn])
    print(f"\n== neighbours of {sn} {r0}")
    for q in p["partitions"]:
        r = rect(q)
        if q["name"] == sn:
            continue
        if r[0] <= r0[2] + 50 and r[2] >= r0[0] - 50 and r[1] <= r0[3] + 50 and r[3] >= r0[1] - 50:
            side = []
            if abs(r[2] - r0[0]) < 50: side.append("W")
            if abs(r[0] - r0[2]) < 50: side.append("E")
            if abs(r[3] - r0[1]) < 50: side.append("S")
            if abs(r[1] - r0[3]) < 50: side.append("N")
            print(f"  {q['name']:<22} {q['type']:<34} {tuple(round(v,1) for v in r)} side={side}")
# slice extent: all partitions sl_W3_*
print("\n== slice sl_W3_* members")
for q in p["partitions"]:
    if q["name"].startswith("sl_W3_"):
        print(f"  {q['name']:<22} {q['type']:<34} {tuple(round(v,1) for v in rect(q))}")
L = p["lanes"]
print("\nlane keys example", json.dumps(L[0])[:300], "n", len(L))
ks = collections.Counter()
for l in L:
    for k in l:
        ks[k] += 1
print(ks)
