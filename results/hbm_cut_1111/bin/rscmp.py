import csv, sys, json
def load(p):
    return {r["type"]: r for r in csv.DictReader(open(p), delimiter="\t")}
a, b = load(sys.argv[1]), load(sys.argv[2])
cols = ["verdict", "p99_ratio", "core_H", "core_V", "street_H", "street_V", "face_H", "face_V"]
worse = []
print("type\t" + "\t".join(f"{c}_before\t{c}_after" for c in ["verdict", "p99_ratio", "worst"]))
for t in sorted(set(a) | set(b)):
    ra, rb = a.get(t, {}), b.get(t, {})
    def w(r):
        v = [float(r[c]) for c in cols[2:] if r.get(c) not in (None, "")]
        return max(v) if v else 0.0
    pa, pb = float(ra.get("p99_ratio") or 0), float(rb.get("p99_ratio") or 0)
    print(f"{t}\t{ra.get('verdict','-')}\t{rb.get('verdict','-')}\t{pa:.3f}\t{pb:.3f}\t{w(ra):.3f}\t{w(rb):.3f}")
    if rb and ra and (pb > pa + 1e-3 or w(rb) > w(ra) + 1e-3):
        worse.append((t, pa, pb, w(ra), w(rb)))
print("WORSE", json.dumps(worse))
