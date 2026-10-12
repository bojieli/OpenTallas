"""Lossless layout extraction for the Chip Explorer layout viewer.  Runs INSIDE the ORFS container, on the fleet host
that holds the element's final routed DB:

    openroad -python -exit lv_extract.py        (env OT_DB=<6_final.odb>, OT_OUT=<dir>)

Reads the DB through the OpenDB Python API only (no DEF text) and writes into OT_OUT, all little-endian int32:

  meta.json    dbu, die / core, layer table (routing + cut layers, tech order), track-grid patterns, via-type table (every
               via used, with its exact cut + enclosure boxes relative to the via origin), master table (pin + OBS boxes
               in the master frame, routing / cut layers only), net / instance / bterm name tables, macro list, counts
  rects.i32    7 x N: layer, x0, y0, x1, y1, net (1-based, 0 = none), kind
               kind 0 signal wire segment or RECT patch (decoded from the wire opcodes: dbWirePathItr skips them), 1 special stripe, 2 special followpin, 3 other special (ring / blockwire /
               padring / ...), 4 block pin (bterm), 5 routing obstruction, 6 metal fill
  vias.i32     5 x M: x, y, via type, net, kind (0 signal-wire via, 1 special-wire via)
  insts.i32    9 x I: origin x, origin y, orient (odb enum order R0 R90 R180 R270 MY MYR90 MX MXR90), master,
               bbox x0, y0, x1, y1, flags (1 = macro / block, 2 = fixed, 4 = physical-only: filler / tap / decap)
  inets.i32    for every instance, in master pin order: the net index of that pin (0 = unconnected)
  truth.i32    5 x T: layer, x0, y0, x1, y1 -- the canonical expanded shape set produced by OpenDB itself (wire segments,
               via boxes from each via's own boxes, special-via boxes from dbSBox.getViaBoxes, instance shapes from
               dbInstShapeItr, bterm pin boxes, obstructions, fills).  The round-trip check compares the decoded viewer
               tiles against this list rectangle by rectangle.
"""
import array, json, os, sys, time

import odb
from openroad import Design, Tech

T0 = time.time()
OUT = os.environ.get('OT_OUT', '/out')
TRUTH = os.environ.get('OT_TRUTH', '1') == '1'


def log(*a):
    print('[lv_extract %7.1fs]' % (time.time() - T0), *a, flush=True)


tech = Tech()
design = Design(tech)
design.evalTclString('read_db ' + os.environ['OT_DB'])
block = design.getBlock()
dbt = block.getDataBase().getTech()
DBU = block.getDbUnitsPerMicron()
log('loaded', os.environ['OT_DB'], 'dbu', DBU)

# ------------------------------------------------------------------ layers
LAY = []          # tech layers kept: routing + cut, tech order
LIDX = {}         # tech layer number -> our index
for l in dbt.getLayers():
    if l.getType() in ('ROUTING', 'CUT'):
        LIDX[l.getNumber()] = len(LAY)
        LAY.append(l)


def lidx(tl):
    return LIDX.get(tl.getNumber(), -1) if tl is not None else -1


tracks = {}
for g in block.getTrackGrids():
    tl = g.getTechLayer()
    if tl is None or tl.getNumber() not in LIDX: continue
    tracks[tl.getName()] = dict(x=[list(g.getGridPatternX(i)) for i in range(g.getNumGridPatternsX())],
                                y=[list(g.getGridPatternY(i)) for i in range(g.getNumGridPatternsY())])
layers = []
for l in LAY:
    e = dict(name=l.getName(), type=l.getType(), level=l.getRoutingLevel())
    if l.getType() == 'ROUTING':
        e.update(dir=l.getDirection(), width=l.getWidth(), pitch=l.getPitch(), tracks=tracks.get(l.getName()))
    layers.append(e)

rects = array.array('i')
vias = array.array('i')
truth = array.array('i')


def T(li, x0, y0, x1, y1):
    truth.extend((li, x0, y0, x1, y1))


# ------------------------------------------------------------------ via table
VIA = {}          # ('T'|'B', name) -> index
via_tab = []


def via_index(tv, bv):
    key = ('T', tv.getName()) if tv is not None else ('B', bv.getName())
    k = VIA.get(key)
    if k is None:
        v = tv if tv is not None else bv
        boxes = []
        for bx in v.getBoxes():
            li = lidx(bx.getTechLayer())
            if li >= 0: boxes.append([li, bx.xMin(), bx.yMin(), bx.xMax(), bx.yMax()])
        k = VIA[key] = len(via_tab)
        via_tab.append(dict(name=key[1], tech=key[0] == 'T', boxes=boxes))
    return k


# ------------------------------------------------------------------ nets: routed wires + special wires
nets = list(block.getNets())
net_names, net_sig = [], []
NETIDX = {}
for i, n in enumerate(nets):
    NETIDX[n.getId()] = i + 1
    net_names.append(n.getName())
    net_sig.append(n.getSigType())
SHAPE_KIND = {'STRIPE': 1, 'FOLLOWPIN': 2}
n_seg = n_via = n_rect = 0
D = odb.dbWireDecoder
for n in nets:
    ni = NETIDX[n.getId()]
    w = n.getWire()
    if w is not None:
        it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); ps = odb.dbWirePathShape()
        while it.getNextPath(p):
            while it.getNextShape(ps):
                s = ps.shape
                if s.isVia():
                    tv = s.getTechVia(); bv = None if tv is not None else s.getVia()
                    k = via_index(tv, bv)
                    x, y = s.getViaXY()
                    vias.extend((x, y, k, ni, 0)); n_via += 1
                    if TRUTH:
                        for b in via_tab[k]['boxes']: T(b[0], x + b[1], y + b[2], x + b[3], y + b[4])
                elif s.isViaBox():
                    continue
                else:
                    li = lidx(s.getTechLayer())
                    if li < 0: continue
                    r = (li, s.xMin(), s.yMin(), s.xMax(), s.yMax())
                    rects.extend(r + (ni, 0)); n_seg += 1
                    if TRUTH: truth.extend(r)
        # RECT patches ("NEW M2 ( x y ) RECT ( dx1 dy1 dx2 dy2 )"): dbWirePathItr does not yield them; decode them from the
        # wire's opcode stream (the four operands after the RECT opcode, relative to the last point)
        dec = D(); dec.begin(w); op = dec.next(); last = None
        while op != D.END_DECODE:
            if op == D.POINT: last = dec.getPoint()
            elif op == D.POINT_EXT: last = dec.getPoint_ext()
            elif op == D.RECT and last is not None:
                li = lidx(dec.getLayer())
                if li >= 0:
                    j = dec.getJunctionId(); d = [w.getData(j + t) for t in range(4)]
                    r = (li, last[0] + min(d[0], d[2]), last[1] + min(d[1], d[3]), last[0] + max(d[0], d[2]), last[1] + max(d[1], d[3]))
                    rects.extend(r + (ni, 0)); n_rect += 1
                    if TRUTH: truth.extend(r)
            op = dec.next()
    for sw in n.getSWires():
        for bx in sw.getWires():
            if bx.isVia():
                tv = bx.getTechVia(); bv = None if tv is not None else bx.getBlockVia()
                k = via_index(tv, bv)
                x, y = bx.getViaXY()
                vias.extend((x, y, k, ni, 1)); n_via += 1
                if TRUTH:
                    for s in bx.getViaBoxes([]):
                        li = lidx(s.getTechLayer())
                        if li >= 0: T(li, s.xMin(), s.yMin(), s.xMax(), s.yMax())
            else:
                li = lidx(bx.getTechLayer())
                if li < 0: continue
                kind = SHAPE_KIND.get(bx.getWireShapeType(), 3)
                r = (li, bx.xMin(), bx.yMin(), bx.xMax(), bx.yMax())
                rects.extend(r + (ni, kind)); n_seg += 1
                if TRUTH: truth.extend(r)
log('wires: %d rects (+%d RECT patches), %d vias, %d via types, %d nets' % (n_seg, n_rect, n_via, len(via_tab), len(nets)))

# ------------------------------------------------------------------ block pins, obstructions, fills
bterms = list(block.getBTerms())
bt_names, bt_io = [], []
for i, bt in enumerate(bterms):
    bt_names.append(bt.getName()); bt_io.append(bt.getIoType())
    net = bt.getNet(); ni = NETIDX.get(net.getId(), 0) if net is not None else 0
    for bp in bt.getBPins():
        for bx in bp.getBoxes():
            li = lidx(bx.getTechLayer())
            if li < 0: continue
            r = (li, bx.xMin(), bx.yMin(), bx.xMax(), bx.yMax())
            rects.extend(r + (ni, 4))
            if TRUTH: truth.extend(r)
for ob in block.getObstructions():
    bx = ob.getBBox(); li = lidx(bx.getTechLayer())
    if li < 0: continue
    r = (li, bx.xMin(), bx.yMin(), bx.xMax(), bx.yMax())
    rects.extend(r + (0, 5))
    if TRUTH: truth.extend(r)
for f in block.getFills():
    rr = f.getRect(); li = lidx(f.getTechLayer())
    if li < 0: continue
    r = (li, rr.xMin(), rr.yMin(), rr.xMax(), rr.yMax())
    rects.extend(r + (0, 6))
    if TRUTH: truth.extend(r)

# ------------------------------------------------------------------ masters + instances
ORIENT = ['R0', 'R90', 'R180', 'R270', 'MY', 'MYR90', 'MX', 'MXR90']
OI = {o: i for i, o in enumerate(ORIENT)}
MAS = {}
masters = []


def master_index(m):
    k = MAS.get(m.getName())
    if k is not None: return k
    pins, boxes = [], []
    for pi, mt in enumerate(m.getMTerms()):
        pins.append(dict(name=mt.getName(), sig=mt.getSigType(), io=mt.getIoType()))
        for mp in mt.getMPins():
            for bx in mp.getGeometry():
                if bx.isVia():
                    tv = bx.getTechVia(); x, y = bx.getViaXY()
                    if tv is None: continue
                    for b in tv.getBoxes():
                        li = lidx(b.getTechLayer())
                        if li >= 0: boxes.append([li, x + b.xMin(), y + b.yMin(), x + b.xMax(), y + b.yMax(), pi])
                    continue
                li = lidx(bx.getTechLayer())
                if li >= 0: boxes.append([li, bx.xMin(), bx.yMin(), bx.xMax(), bx.yMax(), pi])
    for bx in m.getObstructions():
        if bx.isVia():
            tv = bx.getTechVia(); x, y = bx.getViaXY()
            if tv is None: continue
            for b in tv.getBoxes():
                li = lidx(b.getTechLayer())
                if li >= 0: boxes.append([li, x + b.xMin(), y + b.yMin(), x + b.xMax(), y + b.yMax(), -1])
            continue
        li = lidx(bx.getTechLayer())
        if li >= 0: boxes.append([li, bx.xMin(), bx.yMin(), bx.xMax(), bx.yMax(), -1])
    k = MAS[m.getName()] = len(masters)
    masters.append(dict(name=m.getName(), w=m.getWidth(), h=m.getHeight(), type=m.getType(), block=bool(m.isBlock()),
                        origin=list(m.getOrigin()), pins=pins, boxes=boxes))
    return k


insts = array.array('i')
inets = array.array('i')
inst_names = []
macros = []
PHYS = ('FILLER', 'TAPCELL', 'DECAP', 'TAP')
for inst in block.getInsts():
    m = inst.getMaster(); mi = master_index(m)
    ox, oy = inst.getOrigin(); bb = inst.getBBox()
    fl = (1 if m.isBlock() else 0) | (2 if inst.getPlacementStatus() in ('FIRM', 'LOCKED', 'COVER') else 0) | \
         (4 if m.getName().upper().startswith(PHYS) or m.getType() in ('CORE_SPACER', 'CORE_WELLTAP', 'ENDCAP') else 0)
    insts.extend((ox, oy, OI[inst.getOrient()], mi, bb.xMin(), bb.yMin(), bb.xMax(), bb.yMax(), fl))
    nm = inst.getName(); inst_names.append(nm)
    if m.isBlock(): macros.append(dict(i=len(inst_names) - 1, name=nm, master=m.getName(), bbox=[bb.xMin(), bb.yMin(), bb.xMax(), bb.yMax()],
                                       orient=inst.getOrient(), origin=[ox, oy]))
    mts = m.getMTerms()
    if mts:
        nets_of = {}
        for itm in inst.getITerms():
            net = itm.getNet()
            if net is not None: nets_of[itm.getMTerm().getName()] = NETIDX.get(net.getId(), 0)
        inets.extend([nets_of.get(mt.getName(), 0) for mt in mts])
    if TRUTH:
        it = odb.dbInstShapeItr(False); it.begin(inst, odb.dbInstShapeItr.ALL); s = odb.dbShape()
        while it.next(s):
            tl = s.getTechLayer()
            if s.isVia():   # a via inside a master's pin geometry: dbInstShapeItr yields its boxes as VIA_BOX shapes
                continue
            li = lidx(tl)
            if li >= 0: T(li, s.xMin(), s.yMin(), s.xMax(), s.yMax())
log('instances: %d (%d macros, %d masters)' % (len(inst_names), len(macros), len(masters)))

# ------------------------------------------------------------------ write
os.makedirs(OUT, exist_ok=True)
for nm, a in (('rects', rects), ('vias', vias), ('insts', insts), ('inets', inets), ('truth', truth)):
    with open(os.path.join(OUT, nm + '.i32'), 'wb') as fh:
        if sys.byteorder != 'little': a.byteswap()
        a.tofile(fh)
die, core = block.getDieArea(), block.getCoreArea()
meta = dict(schema='opentallas.layout_viewer.extract.v1', db=os.environ['OT_DB'], top=block.getName(), dbu=DBU,
            die=[die.xMin(), die.yMin(), die.xMax(), die.yMax()], core=[core.xMin(), core.yMin(), core.xMax(), core.yMax()],
            layers=layers, vias=via_tab, masters=masters, macros=macros, orients=ORIENT,
            nets=net_names, net_sig=net_sig, insts=inst_names, bterms=bt_names, bterm_io=bt_io,
            counts=dict(rects=len(rects) // 7, vias=len(vias) // 5, insts=len(insts) // 9, inets=len(inets), truth=len(truth) // 5),
            truth=TRUTH, seconds=round(time.time() - T0, 1))
with open(os.path.join(OUT, 'meta.json'), 'w') as fh:
    json.dump(meta, fh, separators=(',', ':'))
log('done', meta['counts'])
