# DS85-HEHOT probe 2 (DO_NOT_COUNT): M6/M7 PDN geometry over he e11 and over a std-cell region; M6 track coverage
import os, odb, collections
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"])
b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron(); tech = db.getTech()
I = b.findInst("u_bound.u_u_e11_u_e"); ib = I.getBBox()
regions = {"he_e11": (ib.xMin(), ib.yMin(), ib.xMax(), ib.yMax()), "std_x600_y380": (int(600*u), int(360*u), int(800*u), int(500*u))}
for rn, (X0, Y0, X1, Y1) in regions.items():
    for ln in ("M6", "M7"):
        segs = []
        for net in b.getNets():
            if not net.isSpecial(): continue
            for sw in net.getSWires():
                for w in sw.getWires():
                    if w.isVia() or w.getTechLayer().getName() != ln: continue
                    if w.xMin() < X1 and w.xMax() > X0 and w.yMin() < Y1 and w.yMax() > Y0:
                        segs.append((net.getName(), w.xMin(), w.yMin(), w.xMax(), w.yMax()))
        horiz = ln == "M6"
        ws = collections.Counter(((s[4]-s[2]) if horiz else (s[3]-s[1]))/u for s in segs)
        ls = collections.Counter(round(((s[3]-s[1]) if horiz else (s[4]-s[2]))/u, 2) for s in segs)
        pos = sorted(set((s[2] if horiz else s[1]) for s in segs))
        d = collections.Counter(round((pos[k+1]-pos[k])/u, 3) for k in range(len(pos)-1))
        print(rn, ln, "n", len(segs), "widths", dict(ws), "lengths", ls.most_common(4), "pos-steps", d.most_common(5))
        # fraction of tracks within region blocked (centre within width/2+spacing)
        l = tech.findLayer(ln); tg = b.findTrackGrid(l)
        tr = sorted(set(tg.getGridY() if horiz else tg.getGridX()))
        lo, hi = (Y0, Y1) if horiz else (X0, X1)
        tr = [t for t in tr if lo <= t <= hi]
        keep = l.getSpacing() + l.getWidth()//2
        blk = 0
        for t in tr:
            for s in segs:
                a, c = (s[2], s[4]) if horiz else (s[1], s[3])
                if a - keep < t < c + keep: blk += 1; break
        print("   tracks", len(tr), "blocked(full-span assumption)", blk, round(blk/max(1,len(tr)),3))
