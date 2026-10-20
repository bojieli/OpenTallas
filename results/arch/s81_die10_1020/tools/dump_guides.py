# S81-DIE10 10-20: dump GRT guides + macro OBS + instances from a post-GRT ODB (read-only), for the mu5 class table.
# usage (inside ORFS image): openroad -python -exit dump_guides.py <grt.odb> <outdir>
import odb, struct, sys, json, re, time
odbp, outd = sys.argv[1], sys.argv[2]
t0 = time.time()
db = odb.dbDatabase.create(); odb.read_db(db, odbp)
blk = db.getChip().getBlock(); tech = db.getTech()
dbu = blk.getDbUnitsPerMicron()
gg = blk.getGCellGrid()
meta = {'dbu': dbu, 'die': [blk.getDieArea().xMin(), blk.getDieArea().yMin(), blk.getDieArea().xMax(), blk.getDieArea().yMax()],
        'gx': list(gg.getGridX()) if gg else None, 'gy': list(gg.getGridY()) if gg else None, 'layers': {}, 'read_s': time.time() - t0}
lid = {}
for L in tech.getLayers():
    if L.getType() == 'ROUTING':
        lid[L.getName()] = L.getRoutingLevel()
        meta['layers'][L.getName()] = {'level': L.getRoutingLevel(), 'dir': L.getDirection(), 'pitch': L.getPitch()}
cls = {}
def ncls(n):
    m = re.match(r'([A-Za-z]+(?:_[A-Za-z]+)?)', n)
    k = m.group(1) if m else 'other'
    if k.startswith('net') and re.match(r'net\d', n): k = 'net#'
    if k not in cls:
        if len(cls) >= 250: k = 'other'
        cls.setdefault(k, len(cls))
    return cls[k]
ng = 0; nn = 0
with open(f'{outd}/guides.bin', 'wb') as f:
    for net in blk.getNets():
        gs = net.getGuides()
        if not gs: continue
        c = ncls(net.getName()); nn += 1
        sp = 1 if net.isSpecial() else 0
        buf = bytearray()
        for g in gs:
            b = g.getBox(); L = g.getLayer()
            buf += struct.pack('<BBBiiii', lid.get(L.getName(), 0), c, sp, b.xMin(), b.yMin(), b.xMax(), b.yMax())
            ng += 1
        f.write(buf)
meta.update(nets_with_guides=nn, guides=ng, classes=cls, guide_s=time.time() - t0)
insts = []; no = 0
with open(f'{outd}/obs.bin', 'wb') as f:
    for inst in blk.getInsts():
        m = inst.getMaster(); bb = inst.getBBox()
        insts.append([inst.getName(), m.getName(), bb.xMin(), bb.yMin(), bb.xMax(), bb.yMax(), 1 if m.isBlock() else 0])
        if not m.isBlock(): continue
        ori = str(inst.getOrient()).split('.')[-1]
        OR = {'R0': lambda x, y: (x, y), 'R90': lambda x, y: (-y, x), 'R180': lambda x, y: (-x, -y), 'R270': lambda x, y: (y, -x),
              'MY': lambda x, y: (-x, y), 'MX': lambda x, y: (x, -y), 'MXR90': lambda x, y: (y, x), 'MYR90': lambda x, y: (-y, -x)}[ori]
        mw, mh = m.getWidth(), m.getHeight()
        cx = [OR(0, 0), OR(mw, mh)]; ox = bb.xMin() - min(c[0] for c in cx); oy = bb.yMin() - min(c[1] for c in cx)
        def tr(b):
            a_ = OR(b.xMin(), b.yMin()); b_ = OR(b.xMax(), b.yMax())
            return min(a_[0], b_[0]) + ox, min(a_[1], b_[1]) + oy, max(a_[0], b_[0]) + ox, max(a_[1], b_[1]) + oy
        for ob in m.getObstructions():
            L = ob.getTechLayer()
            if L is None or L.getType() != 'ROUTING': continue
            f.write(struct.pack('<Biiii', lid[L.getName()], *tr(ob))); no += 1
        for mt in m.getMTerms():
            for mp in mt.getMPins():
                for ob in mp.getGeometry():
                    L = ob.getTechLayer()
                    if L is None or L.getType() != 'ROUTING': continue
                    f.write(struct.pack('<Biiii', 100 + lid[L.getName()], *tr(ob))); no += 1
    for ob in blk.getObstructions():
        b = ob.getBBox(); L = b.getTechLayer()
        if L is None or L.getType() != 'ROUTING': continue
        f.write(struct.pack('<Biiii', lid[L.getName()], b.xMin(), b.yMin(), b.xMax(), b.yMax())); no += 1
meta.update(obs=no, total_s=time.time() - t0)
json.dump(insts, open(f'{outd}/insts.json', 'w'))
json.dump(meta, open(f'{outd}/meta.json', 'w'))
print('DUMP_DONE', json.dumps({k: meta[k] for k in ('nets_with_guides', 'guides', 'obs', 'total_s')}))
