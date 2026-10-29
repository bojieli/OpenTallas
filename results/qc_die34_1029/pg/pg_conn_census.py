"""DIE-QC-34: whole-die connectivity census of the materialized mixed PG access (provider_pg.odb).
Every planned contact (clock CKINV + provider cell, VDD and VSS) must reach a canonical M8/M9 grid stripe through
actual SWire conductors (wires + technology-via layer boxes), with abutting native M1 rails of the contact cells
unioned (touching edge counts), same rail model as the scoped vehicle (and its VIA12 mutant control).
Intra-layer touch/overlap only; inter-layer only through via boxes."""
import json, sys, time, collections
from pathlib import Path
import numpy as np
import odb
sys.path.insert(0, '/srv/opentallas-scratch2/claude/wt/codex-qc-import-0824/tools/die_plan'); sys.path.insert(0, sys.argv[1] + '/src')
from pg_census import transformed_rect
import shapely
from shapely.strtree import STRtree

R = Path(sys.argv[1]); odbp = sys.argv[2]; out = Path(sys.argv[3]); out.mkdir(exist_ok=True)
F = R / "reachfix"
plan = json.load(open(F / "pg_candidate/access_plan.json"))
contacts = sorted({(m, q["net"]) for q in plan["paths"] for m in q["members"]})
t0 = time.time()
d = odb.dbDatabase.create(); odb.read_db(d, odbp); b = d.getChip().getBlock()
res = dict(source_odb=odbp, contacts=len(contacts))
fails = []
for n in ["VDD", "VSS"]:
    L = []; X = []; groups = []; grid = []
    for sw in b.findNet(n).getSWires():
        for z in sw.getWires():
            if z.isVia():
                tv = z.getTechVia(); x, y = z.getViaXY(); g = []
                for sh in tv.getBoxes():
                    ly = sh.getTechLayer()
                    if ly and ly.getRoutingLevel() > 0:
                        g.append(len(L)); L.append(ly.getName()); X.append((x + sh.xMin(), y + sh.yMin(), x + sh.xMax(), y + sh.yMax()))
                groups.append(g)
            else:
                ly = z.getTechLayer().getName()
                if ly in ("M8", "M9") and (z.xMax() - z.xMin() > 1000000 or z.yMax() - z.yMin() > 1000000):
                    grid.append(len(L))
                L.append(ly); X.append((z.xMin(), z.yMin(), z.xMax(), z.yMax()))
    rail = {}
    names = [m for m, nn in contacts if nn == n]
    for m in names:
        inst = b.findInst(m); it = inst.findITerm(n)
        rr = [tuple(transformed_rect(inst, z)) for mp in it.getMTerm().getMPins() for z in mp.getGeometry()
              if z.getTechLayer() and z.getTechLayer().getName() == "M1"]
        assert len(rr) == 1, (m, n, rr)
        rail[m] = len(L); L.append("M1"); X.append(rr[0])
    N = len(L); parent = np.arange(N)
    def find(i):
        r = i
        while parent[r] != r: r = parent[r]
        while parent[i] != r: parent[i], i = r, parent[i]
        return r
    def union(i, j):
        a, c = find(i), find(j)
        if a != c: parent[a] = c
    for g in groups:
        for j in g[1:]: union(g[0], j)
    A = np.array(X, dtype=np.int64); Ls = np.array(L)
    for ly in sorted(set(L)):
        ids = np.nonzero(Ls == ly)[0]
        boxes = shapely.box(A[ids, 0], A[ids, 1], A[ids, 2], A[ids, 3])
        tree = STRtree(boxes)
        p, q = tree.query(boxes, predicate="intersects")
        k = p < q
        for i, j in zip(ids[p[k]], ids[q[k]]): union(int(i), int(j))
        print("LAYER", n, ly, len(ids), int(k.sum()), round(time.time() - t0), flush=True)
    roots = {find(i) for i in grid}
    bad = [m for m in names if find(rail[m]) not in roots]
    fails += [dict(inst=m, pin=n) for m in bad]
    comp = collections.Counter(find(i) for i in range(N))
    res[n] = dict(contacts=len(names), connected=len(names) - len(bad), grid_stripes=len(grid), shapes=N,
                  grid_components=len(roots))
    print("NET", n, res[n], flush=True)
res["failed"] = len(fails); res["seconds"] = round(time.time() - t0)
res["verdict"] = "PASS_PG_CONTACT_CONNECTIVITY" if not fails else "FAIL_PG_CONTACT_CONNECTIVITY"
res["scope"] = "Contact-to-canonical-grid conductor connectivity only. Not DRC, not IR, not native-cell PG, not clock route."
json.dump(res, open(out / "census.json", "w"), indent=2); json.dump(fails[:2000], open(out / "fails.json", "w"))
print(json.dumps(res, indent=2), flush=True)
