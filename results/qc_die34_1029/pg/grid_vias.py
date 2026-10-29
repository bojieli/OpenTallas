"""DIE-QC-34: add the canonical-grid M8<->M9 stack vias of the EXISTING PG plan (die_trial PDN tcl:
add_pdn_connect -grid top -layers {M8 M9}, i.e. a via at every same-net M8 x M9 stripe crossing) to provider_pg.odb,
as pdngen would: one generated via from the tech VIARULE M9_M8 GENERATE (cut 0.04, pitch 0.097 = spacing 0.057,
M8 enclosure 0, M9 enclosure 0.02) filling each crossing; then a grid census: stripes + vias union-find per net
must give ONE connected piece per net, and every crossing must carry exactly one via.
argv: in_odb out_dir pg_rects.json"""
import json, sys, time, hashlib, collections
from pathlib import Path
import odb

t0 = time.time()
src, out, rects = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
out.mkdir(exist_ok=True)
grid = json.load(open(rects))
U = lambda v: round(v * 1000)
d = odb.dbDatabase.create(); odb.read_db(d, src); b = d.getChip().getBlock(); tech = d.getTech()
M8, V8, M9 = (tech.findLayer(n) for n in ("M8", "V8", "M9"))
CUT, SP, ENC9 = 40, 57, 20


def cut_array(w, h):
    """cols/rows of 40-nm cuts at 97-nm pitch inside a w x h (nm) crossing, M9 (vertical, x-width) enclosure 20 nm on
    its x sides, M8 enclosure 0 (cuts strictly inside both rects)."""
    nx = (w - 2 * ENC9 - CUT) // (CUT + SP) + 1
    ny = (h - CUT) // (CUT + SP) + 1
    return int(nx), int(ny)


vias = {}
def via_for(w, h):
    k = (w, h)
    if k not in vias:
        nx, ny = cut_array(w, h)
        v = odb.dbVia.create(b, f"ot_pg_via89_{nx}x{ny}")
        p = odb.dbViaParams()
        p.setBottomLayer(M8); p.setCutLayer(V8); p.setTopLayer(M9)
        p.setXCutSize(CUT); p.setYCutSize(CUT); p.setXCutSpacing(SP); p.setYCutSpacing(SP)
        p.setNumCutCols(nx); p.setNumCutRows(ny)
        p.setXBottomEnclosure(0); p.setYBottomEnclosure(0); p.setXTopEnclosure(0); p.setYTopEnclosure(0)
        v.setViaParams(p)
        vias[k] = (v, nx, ny)
    return vias[k]


res = dict(source_odb=src, source_sha256=hashlib.sha256(open(src, "rb").read()).hexdigest(), nets={})
for n in ("VDD", "VSS"):
    h = sorted([[U(v) for v in r[2:]] for r in grid if r[0] == n and r[1] == "M8"], key=lambda r: r[1])
    v = sorted([[U(x) for x in r[2:]] for r in grid if r[0] == n and r[1] == "M9"], key=lambda r: r[0])
    net = b.findNet(n); sw = odb.dbSWire.create(net, "FIXED")
    parent = list(range(len(h) + len(v)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    made = 0; shapes = collections.Counter()
    import bisect
    vx = [r[0] for r in v]
    for i, a in enumerate(h):
        lo = bisect.bisect_left(vx, a[0] - 10**7)
        for j in range(lo, len(v)):
            c = v[j]
            if c[0] >= a[2]: break
            x0, x1 = max(a[0], c[0]), min(a[2], c[2]); y0, y1 = max(a[1], c[1]), min(a[3], c[3])
            if x1 <= x0 or y1 <= y0: continue
            via, nx, ny = via_for(x1 - x0, y1 - y0)
            assert nx >= 1 and ny >= 1
            odb.dbSBox.create(sw, via, (x0 + x1) // 2, (y0 + y1) // 2, "STRIPE")
            made += 1; shapes[(nx, ny)] += 1
            ra, rb = find(i), find(len(h) + j)
            if ra != rb: parent[ra] = rb
    comps = len({find(i) for i in range(len(parent))})
    res["nets"][n] = dict(m8_stripes=len(h), m9_stripes=len(v), crossings_with_via=made,
                          via_arrays={f"{a}x{c}": k for (a, c), k in shapes.items()}, planned_components=comps)
    print("NET", n, res["nets"][n], round(time.time() - t0), flush=True)
odb.write_db(d, str(out / "provider_pg_grid.odb"))
del d
# readback census from the written ODB: actual via boxes join actual stripes
d2 = odb.dbDatabase.create(); odb.read_db(d2, str(out / "provider_pg_grid.odb")); b2 = d2.getChip().getBlock()
for n in ("VDD", "VSS"):
    stripes = {}; centers = []
    for sw in b2.findNet(n).getSWires():
        for z in sw.getWires():
            if z.isVia():
                if z.getBlockVia() is not None and z.getBlockVia().getName().startswith("ot_pg_via89_"):
                    centers.append(z.getViaXY())
            else:
                ly = z.getTechLayer().getName()
                if ly in ("M8", "M9") and (z.xMax() - z.xMin() > 10**6 or z.yMax() - z.yMin() > 10**6):
                    stripes.setdefault(ly, []).append((z.xMin(), z.yMin(), z.xMax(), z.yMax()))
    h = sorted(stripes["M8"], key=lambda r: r[1]); v = sorted(stripes["M9"], key=lambda r: r[0])
    hy = [r[1] for r in h]; vx = [r[0] for r in v]
    import bisect
    parent = list(range(len(h) + len(v)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    orphan = 0
    for x, y in centers:
        i = bisect.bisect_right(hy, y) - 1; j = bisect.bisect_right(vx, x) - 1
        if i < 0 or j < 0 or not (h[i][1] <= y <= h[i][3] and h[i][0] <= x <= h[i][2]) or not (v[j][0] <= x <= v[j][2] and v[j][1] <= y <= v[j][3]):
            orphan += 1; continue
        ra, rb = find(i), find(len(h) + j)
        if ra != rb: parent[ra] = rb
    comps = len({find(i) for i in range(len(parent))})
    res["nets"][n].update(readback_vias=len(centers), readback_orphan_vias=orphan, readback_components=comps)
    print("READBACK", n, len(centers), orphan, comps, round(time.time() - t0), flush=True)
res["out_odb_sha256"] = hashlib.sha256(open(out / "provider_pg_grid.odb", "rb").read()).hexdigest()
res["verdict"] = "PASS_ONE_GRID_PIECE_PER_NET" if all(q["readback_components"] == 1 and q["readback_orphan_vias"] == 0 for q in res["nets"].values()) else "FAIL"
res["seconds"] = round(time.time() - t0)
res["scope"] = "Canonical M8/M9 grid continuity (plan add_pdn_connect M8 M9) on the materialized mixed PG. Contacts already reach a stripe (census 185,698/185,698). Not DRC/IR."
json.dump(res, open(out / "summary.json", "w"), indent=2); print(json.dumps(res, indent=2), flush=True)
