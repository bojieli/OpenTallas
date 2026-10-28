"""FLOW-SHARED-6 2026-10-27: clock-net COVERED-GEOMETRY equality of two routed ODBs (run with `openroad -python`).

Why: OpenRCX extract_parasitics re-encodes the dbWire path segmentation of routed nets (splits/merges path segments at
junctions) without moving any metal.  An opcode/shape-stream compare (clk_geom_diff.py) of a pre-RCX ECO input against
the post-RCX 6_final therefore reports clock nets as changed although no wire moved (QC VMR F4K: the kit's own signed
route 5_2_route -> 6_final shows 80/106 clock nets 'changed', +1779/-866 path shapes, region-equal).  The blocking
opcode diff runs on the ECO's pre-RCX DB (5_2_route.odb); this check proves the RCX'd final DB carries the SAME metal:
for every clock net and every routing layer / via type, the union of its wire rectangles is identical (coordinate-
compressed raster, exact in DBU).  Any differing net-layer region -> FAIL.

  openroad -python -exit clk_geom_cover.py   (env OT_A=ref.odb OT_B=final.odb OT_NETS=nets.txt [OT_JSON=out.json])
Exit 0 PASS, 1 FAIL, 2 cannot check.
"""
import json, os, sys
try:
    import odb
except ImportError:
    print("CLK_GEOM_COVER FAIL: run under openroad -python"); sys.exit(2)


def shapes(path, names):
    db = odb.dbDatabase.create(); odb.read_db(db, path); b = db.getChip().getBlock(); out = {}
    for nm in names:
        n = b.findNet(nm)
        if n is None:
            out[nm] = None; continue
        w = n.getWire(); d = {}
        if w:
            it = odb.dbWirePathItr(); it.begin(w); pth = odb.dbWirePath(); ps = odb.dbWirePathShape()
            while it.getNextPath(pth):
                while it.getNextShape(ps):
                    sh = ps.shape
                    if sh.isVia():
                        v = sh.getTechVia(); key = "V:" + (v.getName() if v else "block")
                    else:
                        key = sh.getTechLayer().getName()
                    d.setdefault(key, []).append((sh.xMin(), sh.yMin(), sh.xMax(), sh.yMax()))
        out[nm] = d
    return out


def region(rs, xs, ys):
    xi = {x: i for i, x in enumerate(xs)}; yi = {y: j for j, y in enumerate(ys)}; cells = set()
    for (a, b, c, d) in rs:
        for i in range(xi[a], xi[c]):
            for j in range(yi[b], yi[d]):
                cells.add((i, j))
    return cells


def compare(A, B, names):
    bad = []
    for nm in names:
        if A[nm] is None or B[nm] is None:
            bad.append((nm, "net missing")); continue
        for k in sorted(set(A[nm]) | set(B[nm])):
            ra, rb = A[nm].get(k, []), B[nm].get(k, [])
            xs = sorted({r[0] for r in ra + rb} | {r[2] for r in ra + rb})
            ys = sorted({r[1] for r in ra + rb} | {r[3] for r in ra + rb})
            if region(ra, xs, ys) != region(rb, xs, ys):
                bad.append((nm, k))
    return bad


def main():
    try:
        a, b, nf = os.environ["OT_A"], os.environ["OT_B"], os.environ["OT_NETS"]
        names = [l.split()[0] for l in open(nf) if l.strip() and not l.startswith("#")]
        if not names:
            raise ValueError(f"empty net list {nf}")
        A, B = shapes(a, names), shapes(b, names)
    except Exception as e:  # fail closed
        print(f"CLK_GEOM_COVER FAIL: cannot check: {e}"); return 2
    bad = compare(A, B, names)
    verdict = "PASS" if not bad else "FAIL"
    rep = dict(schema="opentallas.clk_geom_cover.v1", verdict=verdict, a=a, b=b, nets=len(names),
               differ=[list(x) for x in bad])
    if os.environ.get("OT_JSON"):
        json.dump(rep, open(os.environ["OT_JSON"], "w"), indent=1)
    print(f"CLK_GEOM_COVER {verdict} clock nets {len(names)}: net-layer regions differ {len(bad)} {bad[:10]}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
