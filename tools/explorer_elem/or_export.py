"""Per-element post-route export for the Chip Explorer element page.  Runs INSIDE the ORFS container:

    openroad -python -exit /exp/or_export.py      (env OT_PRE, OT_CORNER, OT_OUT, OT_NPATH)

OT_PRE is the job's own corner STA preamble (read_lef / read_liberty / read_db 6_final.odb / read_sdc 6_final.sdc /
read_spef / set_propagated_clock / post-SDCs), cut from the closure loop's w18_sta_<corner>.tcl, so every timing number
here is re-timed with exactly the sign-off setup the verdict was computed with.

Writes into OT_OUT:
  <corner>.json   corner part: clock tree + per-flop clock arrival, worst paths with per-pin coordinates and delays,
                  power (tt), and (tt only) geometry facts, macros, ports, density grids and the module table
  cells.bin       (tt only) struct-of-arrays, little endian, N cells: x u16, y u16 (quantised over the die, q dbu),
                  w u16, h u16 (nm), module u16, master u16, flags u8
"""
import collections, json, math, os, re, struct, sys, time

import odb
from openroad import Design, Tech, Timing

T0 = time.time()
CORNER = os.environ.get('OT_CORNER', 'tt')
OUT = os.environ.get('OT_OUT', '/out')
NPATH = int(os.environ.get('OT_NPATH', '40'))
NOSTA = os.environ.get('OT_NOSTA') == '1'   # geometry / clock topology only (no liberty, no SDC / SPEF available)
GEOM = CORNER in ('tt', 'geom')


def log(*a):
    print('[or_export %6.1fs]' % (time.time() - T0), *a, flush=True)


tech = Tech()
design = Design(tech)
for ln in open(os.environ['OT_PRE']).read().splitlines():
    ln = ln.strip()
    if not ln or ln.startswith('#'): continue
    log(ln[:160])
    design.evalTclString(ln)
block = design.getBlock()
timing = Timing(design)
DBU = block.getDbUnitsPerMicron()
log('loaded; dbu/um', DBU)

FLAG_FLOP, FLAG_CLK, FLAG_LVT, FLAG_HOLD, FLAG_REPAIR, FLAG_INFER, FLAG_SLVT, FLAG_ICG = 1, 2, 4, 8, 16, 32, 64, 128
SKIP_PREFIX = ('FILLER', 'TAPCELL', 'DECAP')


def clean(n):
    return n.replace('\\', '')


TOOL_NAME = re.compile(r'^(clkbuf|clkload|clknet|clk_|hold|place|rebuffer|split|wire|max_length|repair|gain|delay|input|output|'
                       r'load_slew|fanout|cts|buffer|ANTENNA|PHY|TAP|FILLER|DECAP|ot_eco|eco|resizer|sizeup|dont_touch)', re.I)


def mod_path(name):
    """hierarchical module path of an RTL-named instance (yosys keeps the register path): components before the last '.',
    depth capped at 10.  Tool-generated names (CTS / repair / hold buffers that embed a net name) are not RTL paths."""
    n = clean(name)
    if TOOL_NAME.match(n): return None
    parts = n.split('.')
    if len(parts) < 2: return '(top)' if '$_' in n else None   # a yosys register of the top module itself
    return '.'.join(parts[:-1][:10])


def um(v):
    return round(v / DBU, 4)


def center(inst):
    b = inst.getBBox()
    return (b.xMin() + b.xMax()) / 2.0, (b.yMin() + b.yMax()) / 2.0


masters_seq = {}
masters_buf = {}


def is_seq(m):
    k = m.getName()
    if k not in masters_seq and NOSTA:   # no liberty loaded: ASAP7 sequential cell names
        masters_seq[k] = bool(re.match(r'(DFF|SDF|DHL|DLL|ASYNC_DFF)', k))
    if k not in masters_seq:
        masters_seq[k] = bool(design.isSequential(m)) and 'ICG' not in k
    return masters_seq[k]


def is_bufinv(m):
    k = m.getName()
    if k not in masters_buf:
        masters_buf[k] = bool(design.isBuffer(m) or design.isInverter(m))
    return masters_buf[k]


# ------------------------------------------------------------------ clock tree (both corners)
MAXMIN = Timing.Max if CORNER != 'ff' else Timing.Min
if NOSTA:
    timing = None
clock_roots = [] if NOSTA else [r for r in design.evalTclString(
    'set r {}; foreach c [all_clocks] { foreach s [get_property $c sources] { lappend r [get_full_name $s] } }; '
    'join [lsort -unique $r] " "').split() if r]
clock_names = [] if NOSTA else design.evalTclString('set r {}; foreach c [all_clocks] { lappend r [get_name $c] [get_property $c period] }; '
                                   'join $r " "').split()
log('clock roots', clock_roots, 'clocks', clock_names)


def arr(iterm):
    if NOSTA: return None
    try:
        v = timing.getPinArrival(iterm, Timing.Rise, MAXMIN)
        if timing.isTimeInf(v) or abs(v) > 1e20: return None
        return v * 1e12 if abs(v) < 1e-3 else v  # API returns seconds in some builds, ps (user units) in others
    except Exception:
        return None


nodes = []          # [x_um, y_um, parent, depth, master, arrival_ps, name]
leaves = []         # [x_um, y_um, parent, arrival_ps, inst_name]
node_of_inst = {}
leaf_insts = set()
seen_nets = set()
queue = collections.deque()
if NOSTA:   # no SDC: clock roots are the input ports whose net is a CLOCK net
    clock_roots = [clean(bt.getName()) for bt in block.getBTerms() if bt.getNet() is not None and bt.getNet().getSigType() == 'CLOCK' and bt.getIoType() == 'INPUT']
for r in clock_roots:
    bt = block.findBTerm(r)
    if bt is None or bt.getNet() is None: continue
    bb = bt.getBBox()
    nodes.append([um((bb.xMin() + bb.xMax()) / 2), um((bb.yMin() + bb.yMax()) / 2), -1, 0, 'PORT', 0.0, r])
    queue.append((bt.getNet(), len(nodes) - 1, 0))
clock_nets = []     # (net, level of its driver: 0 = clock port)
while queue:
    net, parent, depth = queue.popleft()
    if net.getId() in seen_nets: continue
    seen_nets.add(net.getId()); clock_nets.append((net, depth))
    for it in net.getITerms():
        if not it.isInputSignal() and not it.getIoType() == 'INPUT': continue
        inst = it.getInst(); m = inst.getMaster()
        x, y = center(inst)
        if m.isBlock():
            leaves.append([um(x), um(y), parent, arr(it), clean(inst.getName()), 1]); leaf_insts.add(inst.getId()); continue
        if is_seq(m):
            leaves.append([um(x), um(y), parent, arr(it), clean(inst.getName()), 0]); leaf_insts.add(inst.getId()); continue
        # pass-through: buffer / inverter / ICG / clock mux
        outs = [o for o in inst.getITerms() if o.isOutputSignal() and o.getNet() is not None]
        if not outs: continue
        if inst.getId() in node_of_inst: continue
        nodes.append([um(x), um(y), parent, depth + 1, m.getName(), arr(it), clean(inst.getName())])
        node_of_inst[inst.getId()] = len(nodes) - 1
        for o in outs: queue.append((o.getNet(), len(nodes) - 1, depth + 1))
log('clock tree: %d nodes, %d leaves' % (len(nodes), len(leaves)))

# routed clock wires (tt only): every wire segment of every clock-tree net, from the DB's routed wires
CLKSEG = None
if GEOM:
    D = odb.dbWireDecoder; segs = []; layers = []; lidx = {}
    dieb = block.getDieArea(); qd = max(1, int(math.ceil(max(dieb.xMax() - dieb.xMin(), dieb.yMax() - dieb.yMin()) / 65535.0)))
    for net, lvl in clock_nets:
        w = net.getWire()
        if w is None: continue
        dec = D(); dec.begin(w); last = None; op = dec.next()
        while op != D.END_DECODE:
            if op in (D.PATH, D.JUNCTION, D.SHORT, D.VWIRE): last = None
            elif op in (D.POINT, D.POINT_EXT):
                pt = dec.getPoint() if op == D.POINT else dec.getPoint_ext()
                xy = ((pt[0] - dieb.xMin()) // qd, (pt[1] - dieb.yMin()) // qd)
                if last is not None and xy != last:
                    ln = dec.getLayer().getName()
                    if ln not in lidx: lidx[ln] = len(layers); layers.append(ln)
                    segs.append((last[0], last[1], xy[0], xy[1], lidx[ln], min(255, lvl)))
                last = xy
            op = dec.next()
    with open(os.path.join(OUT, 'clk.bin'), 'wb') as fh:
        n = len(segs)
        for k in range(4): fh.write(struct.pack('<%dH' % n, *[min(65535, max(0, s_[k])) for s_ in segs]))
        fh.write(struct.pack('<%dB' % n, *[s_[4] for s_ in segs])); fh.write(struct.pack('<%dB' % n, *[s_[5] for s_ in segs]))
    CLKSEG = dict(n=len(segs), file='clk.bin', quantum_dbu=qd, layers=layers, nets=len(clock_nets),
                  layout='x1,y1,x2,y2 u16 (quantum_dbu from die origin); layer u8 (index into layers); level u8 (driver level, 0 = clock port)')
    log('clock wires: %d segments on %d nets' % (len(segs), len(clock_nets)))

# ------------------------------------------------------------------ worst paths


def tcl_paths(dly, n):
    script = r'''
set ot_out {}
set ot_ps [find_timing_paths -path_delay %s -group_path_count %d -endpoint_path_count 1 -sort_by_slack]
foreach p $ot_ps {
  set l [list PATH [get_property $p slack] [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]]
  set ck {}
  catch { set ck [get_name [get_property $p endpoint_clock]] }
  lappend l $ck
  foreach pt [get_property $p points] {
    lappend l [get_full_name [get_property $pt pin]] [get_property $pt arrival]
  }
  lappend ot_out [join $l "\t"]
}
join $ot_out "\n"
''' % (dly, n)
    return design.evalTclString(script)


def find_iterm(full):
    """'inst/PIN' (STA name, escaped) -> (iterm or bterm, inst)"""
    c = clean(full)
    if '/' in c:
        iname, pin = c.rsplit('/', 1)
        for cand in (iname, iname.replace('[', '\\[').replace(']', '\\]')):
            inst = block.findInst(cand)
            if inst is not None:
                it = inst.findITerm(pin)
                return it, inst
    bt = block.findBTerm(c) or block.findBTerm(full)
    return bt, None


def clock_pin_arrival(inst):
    if inst is None: return None
    for it in inst.getITerms():
        mt = it.getMTerm()
        if mt.getSigType() == 'CLOCK' or mt.getName() in ('CLK', 'CK', 'clk'):
            return arr(it)
    return None


paths = []
raw = '' if NOSTA else tcl_paths('max' if CORNER != 'ff' else 'min', NPATH)
for ln in raw.splitlines():
    f = ln.split('\t')
    if not f or f[0] != 'PATH': continue
    slack, sp, ep, ck = f[1], f[2], f[3], f[4]
    pts = []
    prev = None
    for i in range(5, len(f) - 1, 2):
        pin, a = f[i], float(f[i + 1])
        obj, inst = find_iterm(pin)
        x = y = None; master = ''; io = ''
        if inst is not None:
            cx, cy = center(inst)
            try:
                ok, px, py = obj.getAvgXY()
                if ok: cx, cy = px, py
            except Exception:
                pass
            x, y = um(cx), um(cy); master = inst.getMaster().getName()
            io = 'o' if obj is not None and obj.isOutputSignal() else 'i'
        elif obj is not None:
            bb = obj.getBBox(); x, y = um((bb.xMin() + bb.xMax()) / 2), um((bb.yMin() + bb.yMax()) / 2); io = 'port'
        pts.append([clean(pin), round(a, 2), round(a - prev, 2) if prev is not None else 0.0, master, io, x, y])
        prev = a
    _, sinst = find_iterm(sp)
    _, einst = find_iterm(ep)
    paths.append(dict(slack=round(float(slack), 2), start=clean(sp), end=clean(ep), clock=ck,
                      launch_clk_ps=None if sinst is None else (lambda v: None if v is None else round(v, 2))(clock_pin_arrival(sinst)),
                      start_arrival_ps=None if not pts else pts[0][1],
                      capture_clk_ps=None if einst is None else (lambda v: None if v is None else round(v, 2))(clock_pin_arrival(einst)),
                      points=pts))
paths.sort(key=lambda p: p['slack'])
paths = paths[:NPATH]
log('paths:', len(paths), 'worst', paths[0]['slack'] if paths else None)

ws = '' if NOSTA else design.evalTclString('sta::worst_slack_cmd %s' % ('max' if CORNER != 'ff' else 'min'))
try:
    ws = float(ws); ws = ws * 1e12 if abs(ws) < 1e-3 else ws  # worst_slack_cmd returns seconds
except ValueError:
    ws = None
part = dict(schema='opentallas.explorer_elem.corner.v1', corner=CORNER, nosta=NOSTA, worst_slack_ps=None if ws is None else round(ws, 3),
            clocks=clock_names, clock_roots=clock_roots,
            clock_tree=dict(nodes=[[n[0], n[1], n[2], n[3], n[4], None if n[5] is None else round(n[5], 1), n[6]] for n in nodes],
                            leaves=[[l[0], l[1], l[2], None if l[3] is None else round(l[3], 1), l[4], l[5]] for l in leaves]),
            paths=paths, clock_wires=CLKSEG)

if CORNER == 'tt' and not NOSTA:
    try:
        design.evalTclString('report_power > %s/power_tt.rpt' % OUT)
        txt = open('%s/power_tt.rpt' % OUT).read()
        m = re.search(r'^Total\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', txt, re.M)
        if m: part['power_w'] = dict(internal=float(m.group(1)), switching=float(m.group(2)), leakage=float(m.group(3)),
                                     total=float(m.group(4)), basis='OpenSTA report_power, TT libs, default (vectorless) activity')
    except Exception as e:
        log('power failed', e)

# ------------------------------------------------------------------ geometry (tt only)
if GEOM:
    die = block.getDieArea(); core = block.getCoreArea()
    W, H = die.xMax() - die.xMin(), die.yMax() - die.yMin()
    q = max(1, int(math.ceil(max(W, H) / 65535.0)))
    insts = []
    masters = {}; mlist = []
    mods = {}; modlist = []
    n_skip = 0; skip_area = 0
    macros = []
    for inst in block.getInsts():
        m = inst.getMaster(); mn = m.getName()
        if mn.startswith(SKIP_PREFIX):
            n_skip += 1; continue
        if m.isBlock():
            b = inst.getBBox()
            macros.append(dict(name=clean(inst.getName()), master=mn, x0=um(b.xMin()), y0=um(b.yMin()), x1=um(b.xMax()), y1=um(b.yMax())))
            continue
        insts.append(inst)
    log('insts', len(insts), 'skipped filler/tap/decap', n_skip, 'macros', len(macros))
    # module labels: named instances by path, the rest by majority vote of connected labelled cells (nets fanout <= 24)
    idx = {inst.getId(): i for i, inst in enumerate(insts)}
    label = [-1] * len(insts)
    named = 0
    for i, inst in enumerate(insts):
        p = mod_path(inst.getName())
        if p is None: continue
        if p not in mods: mods[p] = len(modlist); modlist.append(p)
        label[i] = mods[p]; named += 1
    log('named cells', named)
    nbrs = [None] * len(insts)
    for net in block.getNets():
        st = net.getSigType()
        if st in ('POWER', 'GROUND', 'CLOCK'): continue
        its = net.getITerms()
        if len(its) > 24 or len(its) < 2: continue
        ids = [idx.get(it.getInst().getId()) for it in its]
        ids = [k for k in ids if k is not None]
        for k in ids:
            if label[k] >= 0: continue
            if nbrs[k] is None: nbrs[k] = []
            nbrs[k].extend(j for j in ids if j != k)
    inferred = 0
    for rnd in range(40):
        upd = []
        for k in range(len(insts)):
            if label[k] >= 0 or not nbrs[k]: continue
            c = collections.Counter(label[j] for j in nbrs[k] if label[j] >= 0)
            if c: upd.append((k, c.most_common(1)[0][0]))
        if not upd: break
        for k, l in upd: label[k] = l
        inferred += len(upd)
    nbrs = None
    unl = sum(1 for l in label if l < 0)
    if unl:
        mods['(unattributed)'] = len(modlist); modlist.append('(unattributed)')
        for k in range(len(insts)):
            if label[k] < 0: label[k] = mods['(unattributed)']
    log('inferred', inferred, 'unattributed', unl, 'modules', len(modlist))

    clk_insts = set(node_of_inst)
    xs = []; ys = []; ws_ = []; hs = []; ms = []; mas = []; fl = []
    std_area = 0; lvt = 0; slvt = 0; nflop = 0
    cnt_master = collections.Counter()
    BIN = float(os.environ.get('OT_BIN_UM', '0'))
    if BIN <= 0: BIN = max(2.0, round(max(W, H) / DBU / 160.0, 1))
    nbx, nby = int(math.ceil(W / DBU / BIN)), int(math.ceil(H / DBU / BIN))
    dens = [0.0] * (nbx * nby); pins = [0] * (nbx * nby)
    mod_bin = collections.defaultdict(collections.Counter)
    for k, inst in enumerate(insts):
        m = inst.getMaster(); mn = m.getName(); b = inst.getBBox()
        if mn not in masters: masters[mn] = len(mlist); mlist.append(mn)
        cnt_master[mn] += 1
        w, h = b.xMax() - b.xMin(), b.yMax() - b.yMin()
        a = w * h; std_area += a
        f = 0
        if is_seq(m): f |= FLAG_FLOP; nflop += 1
        if inst.getId() in clk_insts: f |= FLAG_CLK
        if 'ICG' in mn: f |= FLAG_ICG
        if mn.endswith('_SL'): f |= FLAG_SLVT; slvt += 1
        elif mn.endswith('_L'): f |= FLAG_LVT; lvt += 1
        nm = inst.getName()
        if nm.startswith('hold'): f |= FLAG_HOLD
        elif nm.startswith(('rebuffer', 'split', 'wire', 'max_length', 'place', 'repair', 'gain')): f |= FLAG_REPAIR
        if mod_path(nm) is None and modlist[label[k]] != '(unattributed)': f |= FLAG_INFER
        xs.append(min(65535, (b.xMin() - die.xMin()) // q)); ys.append(min(65535, (b.yMin() - die.yMin()) // q))
        ws_.append(min(65535, int(round(w * 1000.0 / DBU)))); hs.append(min(65535, int(round(h * 1000.0 / DBU))))
        ms.append(label[k]); mas.append(masters[mn]); fl.append(f)
        cx, cy = (b.xMin() + b.xMax()) / 2.0 - die.xMin(), (b.yMin() + b.yMax()) / 2.0 - die.yMin()
        bi = min(nbx - 1, int(cx / DBU / BIN)) + nbx * min(nby - 1, int(cy / DBU / BIN))
        dens[bi] += a; pins[bi] += len(m.getMTerms()) - 2
        mod_bin[bi][label[k]] += 1
    N = len(insts)
    with open(os.path.join(OUT, 'cells.bin'), 'wb') as fh:
        for arr_, fmt in ((xs, 'H'), (ys, 'H'), (ws_, 'H'), (hs, 'H'), (ms, 'H'), (mas, 'H')):
            fh.write(struct.pack('<%d%s' % (N, fmt), *arr_))
        fh.write(struct.pack('<%dB' % N, *fl))
    # macros block bins too
    binA = (BIN * DBU) ** 2
    for mc in macros:
        pass
    dens = [round(min(9.99, d / binA), 3) for d in dens]
    dom = []
    for bi in range(nbx * nby):
        c = mod_bin.get(bi)
        dom.append(c.most_common(1)[0][0] if c else -1)
    # routed-length RUDY: each signal net's routed wire length spread uniformly over its bounding box
    rudy = [0.0] * (nbx * nby)
    t1 = time.time()
    for net in block.getNets():
        if net.getSigType() in ('POWER', 'GROUND'): continue
        try:
            L = design.getNetRoutedLength(net)
        except Exception:
            L = 0
        if not L: continue
        bb = None
        try:
            bb = net.getTermBBox()
        except Exception:
            pass
        if bb is None: continue
        x0 = max(0, int((bb.xMin() - die.xMin()) / DBU / BIN)); x1 = min(nbx - 1, int((bb.xMax() - die.xMin()) / DBU / BIN))
        y0 = max(0, int((bb.yMin() - die.yMin()) / DBU / BIN)); y1 = min(nby - 1, int((bb.yMax() - die.yMin()) / DBU / BIN))
        nb = (x1 - x0 + 1) * (y1 - y0 + 1)
        share = L / DBU / nb
        for yy in range(y0, y1 + 1):
            row = yy * nbx
            for xx in range(x0, x1 + 1): rudy[row + xx] += share
    rudy = [round(r / (BIN * BIN), 3) for r in rudy]  # um of routed wire per um^2 of bin
    log('rudy %.1fs' % (time.time() - t1))
    ports = []
    for bt in block.getBTerms():
        bb = bt.getBBox()
        ports.append([clean(bt.getName()), um((bb.xMin() + bb.xMax()) / 2 - die.xMin()), um((bb.yMin() + bb.yMax()) / 2 - die.yMin()),
                      bt.getIoType()[0], bt.getSigType()[0]])
    mod_count = collections.Counter(ms)
    part.update(
        top=block.getName(), dbu_per_um=DBU, quantum_dbu=q,
        die=dict(x0=um(die.xMin()), y0=um(die.yMin()), x1=um(die.xMax()), y1=um(die.yMax())),
        core=dict(x0=um(core.xMin() - die.xMin()), y0=um(core.yMin() - die.yMin()), x1=um(core.xMax() - die.xMin()), y1=um(core.yMax() - die.yMin())),
        cells=dict(n=N, file='cells.bin', layout='x,y u16 (x quantum_dbu from die origin); w,h u16 nm; module u16; master u16; flags u8',
                   flags=dict(flop=FLAG_FLOP, clock_tree=FLAG_CLK, lvt=FLAG_LVT, hold_buffer=FLAG_HOLD, repair_buffer=FLAG_REPAIR,
                              module_inferred=FLAG_INFER, slvt=FLAG_SLVT, icg=FLAG_ICG)),
        masters=mlist, modules=modlist, module_cells=[mod_count.get(i, 0) for i in range(len(modlist))],
        macros=[dict(mc, x0=round(mc['x0'] - um(die.xMin()), 4), x1=round(mc['x1'] - um(die.xMin()), 4),
                     y0=round(mc['y0'] - um(die.yMin()), 4), y1=round(mc['y1'] - um(die.yMin()), 4)) for mc in macros],
        ports=ports,
        grid=dict(bin_um=BIN, nx=nbx, ny=nby, density=dens, pins=pins, rudy=rudy, dominant_module=dom),
        stats=dict(std_cells=N, filler_tap_decap=n_skip, flops=nflop, lvt_cells=lvt, slvt_cells=slvt,
                   std_cell_area_um2=round(std_area / DBU / DBU, 1),
                   macro_area_um2=round(sum((m['x1'] - m['x0']) * (m['y1'] - m['y0']) for m in macros), 1),
                   core_area_um2=round((core.xMax() - core.xMin()) * (core.yMax() - core.yMin()) / DBU / DBU, 1),
                   die_area_um2=round(W * H / DBU / DBU, 1), named_cells=named, inferred_cells=inferred, unattributed_cells=unl,
                   clock_tree_cells=len(clk_insts), top_masters=cnt_master.most_common(12)))
    # shift clock tree / path coordinates to the die origin
    ox, oy = um(die.xMin()), um(die.yMin())
    if ox or oy:
        for n in part['clock_tree']['nodes']: n[0] -= ox; n[1] -= oy
        for l in part['clock_tree']['leaves']: l[0] -= ox; l[1] -= oy
        for p in part['paths']:
            for pt in p['points']:
                if pt[5] is not None: pt[5] -= ox; pt[6] -= oy
else:
    die = block.getDieArea()
    ox, oy = um(die.xMin()), um(die.yMin())
    if ox or oy:
        for n in part['clock_tree']['nodes']: n[0] -= ox; n[1] -= oy
        for l in part['clock_tree']['leaves']: l[0] -= ox; l[1] -= oy
        for p in part['paths']:
            for pt in p['points']:
                if pt[5] is not None: pt[5] -= ox; pt[6] -= oy

part['elapsed_s'] = round(time.time() - T0, 1)
with open(os.path.join(OUT, '%s.json' % ('tt' if CORNER == 'geom' else CORNER)), 'w') as fh:
    json.dump(part, fh, separators=(',', ':'))
log('done')
