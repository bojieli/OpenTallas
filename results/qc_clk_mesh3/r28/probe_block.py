"""R28 diagnostic probe: run die_clock_mesh build and, for every failed TrackRouter.place, record what occupies the
candidate window (shape kinds / nets overlapping the segment span within the keep band).  No source edits."""
import json
import math
import sys
from collections import Counter

sys.path.insert(0, "/src/tools/die_plan")
import die_clock_128 as C
import die_clock_mesh as D

orig = C.TrackRouter.place
FAILS = []
AGG = Counter()


def place(self, layer, ideal, a0, a1, net, avoid=(), keep=None, dry=False):
    r = orig(self, layer, ideal, a0, a1, net, avoid=avoid, keep=keep, dry=dry)
    if r[0] is None and not dry:
        lo, hi = ideal - self.max_move, ideal + self.max_move
        if keep is not None:
            lo, hi = max(lo, keep[0]), min(hi, keep[1])
        alo, ahi = min(a0, a1), max(a0, a1)
        k = Counter()
        nets = Counter()
        B = self.ix.B
        seen = set()
        for i in range(int(math.floor((lo - 1.5) / B)), int(math.floor((hi + 1.5) / B)) + 1):
            for j in self.ix.bins[layer].get(i, ()):
                if j in seen:
                    continue
                seen.add(j)
                s = self.ix.shapes[j]
                if s[4] < lo - 1.5 or s[3] > hi + 1.5 or s[6] < alo - 1 or s[5] > ahi + 1:
                    continue
                k[(s[2], s[1] if s[2] in ("pg", "mesh") else "-")] += 1
                if s[2] == "tree":
                    nets[s[1]] += 1
        cls = "tree_blocked" if any(t == "tree" for t, _ in k) else "pg_mesh_only"
        AGG[(layer, cls, "keep" if keep else "free", round(hi - lo, 2))] += 1
        if len(FAILS) < 400:
            FAILS.append(dict(layer=layer, ideal=round(ideal, 3), span=[round(alo, 3), round(ahi, 3)], net=net,
                              window=[round(lo, 3), round(hi, 3)], keep=list(keep) if keep else None,
                              kinds={f"{a}:{b}": v for (a, b), v in k.items()}, tree_nets=len(nets), cls=cls))
    return r


C.TrackRouter.place = place
try:
    D.main(sys.argv[1:])
finally:
    agg = [dict(layer=a, cls=b, keep=c, window_um=d, n=v) for (a, b, c, d), v in AGG.most_common()]
    json.dump(dict(agg=agg, sample=FAILS), open("/work/probe_block.json", "w"), indent=1)
    print("PROBE", json.dumps(agg[:20]))
