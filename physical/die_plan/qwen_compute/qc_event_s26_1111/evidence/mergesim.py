"""predict clock_taps.tcl POST_MIN on the PLANNED taps (taps.density_taps loads): a tap with 0<n<MIN merges whole into
the nearest tap with >= MIN, room under the cap, and (conservative bound) tap-tap L1 + its max sink distance <= R."""
import sys, json, collections
f, planf, MIN, R = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
plan = json.load(open(planf))
d = collections.defaultdict(list)
for l in open(f):
    r = l.rstrip("\n").split("\t")
    if r[1] == "density":
        d[r[0]].append([r[2], float(r[3]), float(r[4]), int(r[5]), float(r[6])])
BINS = [(1, 15), (16, 49), (50, 199), (200, 499), (500, 899), (900, 1199), (1200, 10**9)]
def h(rows):
    c = collections.Counter()
    for r in rows:
        if r[3] <= 0: continue
        for lo, hi in BINS:
            if lo <= r[3] <= hi: c[f"{lo}-{hi if hi < 10**9 else ''}"] += 1
    return c
before, after = collections.Counter(), collections.Counter()
merged, kept, types_small = [], [], set()
for tn, rows in sorted(d.items()):
    ck = plan["partition_types"][tn]["clock"]
    cap = min(int(ck.get("tap_max_sinks", 1500)), 10**9)
    before += h(rows)
    rows = [list(r) for r in rows]
    for r in sorted(rows, key=lambda r: (r[3], r[0])):
        if r[3] == 0 or r[3] >= MIN: continue
        types_small.add(tn)
        best = None
        for q in rows:
            if q is r or q[3] < MIN or q[3] + r[3] > cap: continue
            dd = abs(q[1]-r[1]) + abs(q[2]-r[2])
            if dd + r[4] > R: continue
            if best is None or dd < best[0]: best = (dd, q)
        if best is None:
            kept.append((tn, r[0], r[3], r[4])); continue
        best[1][3] += r[3]; merged.append((tn, r[0], r[3], best[1][0], round(best[0], 1))); r[3] = 0
    after += h(rows)
print("BEFORE", dict(sorted(before.items(), key=lambda kv: int(kv[0].split('-')[0]))), sum(before.values()))
print("AFTER ", dict(sorted(after.items(), key=lambda kv: int(kv[0].split('-')[0]))), sum(after.values()))
print("merged", len(merged), "kept", len(kept), "types with a planned tap <", MIN, ":", len(types_small))
print("MERGED", merged)
print("TYPES", ",".join(sorted(types_small)))
