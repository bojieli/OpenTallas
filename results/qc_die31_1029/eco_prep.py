"""DIE-QC-31 c1 ECO prep: freeze every non-rerouted net as obstructions (exact shapes; M8/M9 bloated to the
CK2W2S/CK4W NDR spacing 0.32), disconnect them, rip RR nets, add the variant's mesh keep-out.
usage: openroad -python eco_prep.py IN.odb OUT.odb MODE RR_NETS(comma)   MODE: K (keep-out band) | T (planned tracks)
UNCHECKED until NUMBER-CHECK."""
import odb, sys, json
inp, outp, mode, rr = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
db = odb.dbDatabase.create(); odb.read_db(db, inp)
blk = db.getChip().getBlock(); tech = db.getTech()
U = lambda v: int(round(v * 1000))
NDR_BLOAT = 0                # DRT keeps the routed net's CK2W2S NDR spacing (0.32) to obstructions itself (r1 corridor test)
def boxes(net):
    out = []
    w = net.getWire()
    if not w: return out
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath()
    while it.getNextPath(p):
        ps = odb.dbWirePathShape()
        while it.getNextShape(ps):
            s = ps.shape
            if s.isVia():
                tv = s.getTechVia()
                bs = list(tv.getBoxes())
                ox = s.xMin() - min(b.xMin() for b in bs); oy = s.yMin() - min(b.yMin() for b in bs)
                for b in bs:
                    out.append((b.getTechLayer(), ox + b.xMin(), oy + b.yMin(), ox + b.xMax(), oy + b.yMax()))
            else:
                out.append((s.getTechLayer(), s.xMin(), s.yMin(), s.xMax(), s.yMax()))
    return out
log = dict(mode=mode, rr=rr, obs=0, frozen=[])
mesh_m9 = []
for net in list(blk.getNets()):
    nn = net.getName()
    if nn in rr:
        if net.getWire(): odb.dbWire_destroy(net.getWire())
        continue
    for (L, x0, y0, x1, y1) in boxes(net):
        b = NDR_BLOAT if L.getName() in ("M8", "M9") else 0
        if L.getType() != "ROUTING" and L.getType() != "CUT": continue
        odb.dbObstruction_create(blk, L, x0 - b, y0 - b, x1 + b, y1 + b); log["obs"] += 1
        if nn == "ck_mesh" and L.getName() == "M9": mesh_m9.append((x0, y0, x1, y1))
    for it in list(net.getITerms()): it.disconnect()
    if not net.isSpecial():
        for bt in list(net.getBTerms()): odb.dbBTerm_destroy(bt)
    if net.getWire(): odb.dbWire_destroy(net.getWire())
    log["frozen"].append(nn)
M9 = tech.findLayer("M9")
if mode == "K":
    # keep-out band: a further 0.32 (one NDR space) beyond the NDR spacing on each side of every mesh M9 strap,
    # except a 6-um window at the clip-harness entry port (port sits on the strap x by construction).
    K = U(0.32)   # band = one extra NDR space each side of the strap -> routed legs >= 0.64 um from the strap
    port = (U(546.52), U(1308.96))
    for (x0, y0, x1, y1) in mesh_m9:
        for (a, b) in ((x0 - NDR_BLOAT - K, x0 - NDR_BLOAT), (x1 + NDR_BLOAT, x1 + NDR_BLOAT + K)):
            segs = [(y0, y1)]
            if y0 < port[1] < y1: segs = [(y0, port[1] - U(3)), (port[1] + U(3), y1)]
            for (c, d) in segs:
                if d > c: odb.dbObstruction_create(blk, M9, a, c, b, d); log["obs"] += 1
elif mode == "T":
    # planned tracks: n_B1 trunk on x=545.236 (mirror of its lower leg), n_P1u trunk on x=545.636 (n_P1d's track);
    # M9 closed over the column band x 543.2-548.0 except those two corridors (y-limited per net).
    cor = [(U(545.236), U(945.0), U(1672.0)), (U(545.636), U(1665.0), U(2033.0))]
    X0, X1, Y0, Y1 = U(543.2), U(548.0), U(940.0), U(2040.0)
    hw = U(0.40)  # corridor half width: wire .04 + NDR .32 + .04 slack; P1u wire edge 545.676 is 0.724 from the strap
    xs = sorted({X0, X1} | {c[0] - hw for c in cor} | {c[0] + hw for c in cor})
    for i in range(len(xs) - 1):
        a, b = xs[i], xs[i + 1]
        free = [c for c in cor if c[0] - hw <= a and b <= c[0] + hw]
        if not free:
            odb.dbObstruction_create(blk, M9, a, Y0, b, Y1); log["obs"] += 1
        else:
            for (_, c0, c1) in free:
                if c0 > Y0: odb.dbObstruction_create(blk, M9, a, Y0, b, c0); log["obs"] += 1
                if c1 < Y1: odb.dbObstruction_create(blk, M9, a, c1, b, Y1); log["obs"] += 1
odb.write_db(db, outp)
print("ECO_PREP", json.dumps(log))
