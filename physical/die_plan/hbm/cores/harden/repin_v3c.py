#!/usr/bin/env python3
"""CORE-HBM-REPIN: connectivity-aware core re-pin v3c (PROPOSAL input for the HBM plan owner; the plan pins_file stays
whatever die_plan.json names until HBM-P7 adopts these files).

v3 (repin_v3.py) kept every pin on its connectivity-blind v2 face.  v3c puts each core pin on the core face toward what
its net connects to, in the partition type frame:

  1. partition-port nets: the content port is a lane source net (lane_members.json.gz) or the destination of one
     (census rows: src inst.bus -> dst inst.bus; the source net names the lane); the lane's plan port on this partition
     (ports[].face/window_um, die frame) is mapped into the type frame (partition origin + orient, as plan_backend_v2).
  2. content<->content nets inside the partition: census rows whose two ends are contents of the same partition
     instance (content uK <- die instance named in contents[].note).  Target = the other content's rect centre (the
     other piece's centre when that content is a split master).
  3. split pieces of an over-cap master: the master's hierarchical yosys netlist (the netlists ports_cut.json was cut
     from) is cut into all its pieces at once; every boundary bit of a piece is labelled exactly as netcut/busify
     labels it (= the plan pin names) and resolved to the other pieces / master ports it reaches; master ports then
     resolve through 1-2.
  4. RTL-twin pieces (score hcol, Sinkhorn step0/steady) and the SM quarter cores (lx/tp/ln/front): structural rules
     from the wrapper port lists (sm_wrap_ports.py, gen_core_ports.twin_ports), counted as 'rule'.
  5. clk/rst pins: the core's clock tap (partition clock.taps[] '<inst>.ck'), else the partition tap.
  Anything else keeps its v2 face and is counted 'unresolved'.

Faces are chosen per instance in the instance frame (ray from the core centre to the target: the face it leaves
through), mapped to the core R0 frame through the instance orient (MX: N<->S, MY: E<->W, R180: both), and voted per
pin over every in-scope instance of the type (weight = die instances of its partition type).  Pins whose instances
disagree are reported as orient/position conflicts; a type is never forked.

Placement: per face, at most floor(4.5 * (L - 2*2.16)) pins (spread evenly over the usable span, so the 10-um window
density equals the face average).  An overflowing face spills the pins with the strongest pull toward an adjacent face
with room (adjacent faces only first, then the opposite face); spills are reported.  If the whole perimeter cannot
hold the pins at 4.5/um, the minimum outline (aspect kept, 4.32-um multiples) is reported and the pins are placed on
that outline as an extra file (suffix __min).  Tracks: E/W M4 y = 0.024 + 0.048k; N/S M5 x = 0.024 + 0.048k, minus the
tracks whose 0.024-wide pin overlaps a core M5 PG stripe.  The stripes (gen_core_kit pdn.tcl: width 0.12, spacing
0.072, pitch 4.32, offset 2.064; measured with pdngen in openroad/orfs:asap7lock) sit at x mod 4.32 in
[2.004, 2.124] (VSS) and [2.196, 2.316] (VDD): a band centred at 2.16, mirror-invariant.  Blocked track window:
x mod 4.32 in [1.992, 2.328] -> tracks 2.016 ... 2.304 (7 of 90 per 4.32; the 2.16 gap track is skipped too, it has
only min spacing to both stripes).  NOTE: repin_v3.py skipped [1.932, 2.196], which leaves tracks 2.208/2.256/2.304
under the VDD stripe.  Pins within a face are ordered by the along-face position of their target (bus by bus, bit
order inside a bus), so neighbouring cores' pins face each other without crossing.

    python3 repin_v3c.py --plan ../../die_plan.json --census census_3a7e22238.json --out pins_v3c \
        --net /home/ubuntu/scratch/hbm-p5-pins-1023/net [--cache DIR] [--types t1,t2] [--alt type_id=WxH ...]
"""
import argparse
import bisect
import collections
import gzip
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'pins_cut'))

PITCH, OFF, INSET, KEEP = 0.048, 0.024, 0.019, 2.16
PG_PITCH, PG_BLK = 4.32, (1.992, 2.328)          # blocked track centres (x mod 4.32), see the docstring
CAP, HARD = 4.5, 6.0
CAP_PLACE = 4.35                                 # placement average, so every 10-um window stays <= 4.5
SKIP_PART = re.compile(r'^q_(hc|vm$|su)')         # HBM-P7 is changing these partitions (COORD 10-23)
OPP = dict(N='S', S='N', E='W', W='E')
ADJ = dict(N='EW', S='EW', E='NS', W='NS')


# ------------------------------------------------------------------------------------------------ geometry helpers
def tracks(L, layer):
    k0 = math.ceil((KEEP - OFF) / PITCH - 1e-9)
    k1 = math.floor((L - KEEP - OFF) / PITCH + 1e-9)
    out = []
    for k in range(k0, k1 + 1):
        a = round(OFF + k * PITCH, 4)
        if layer == 'M5' and PG_BLK[0] < (a % PG_PITCH) < PG_BLK[1]:
            continue
        out.append(a)
    return out


def face_cap(L, layer):
    return min(len(tracks(L, layer)), int(CAP_PLACE * max(0.0, L - 2 * KEEP)))


def v2_face(x, y, w, h):
    return min([(x, 'W'), (w - x, 'E'), (y, 'S'), (h - y, 'N')])[1]


def ray_face(cx, cy, w, h, tx, ty):
    """face of the rect (centre cx,cy; size w,h) the ray centre->target leaves through; target inside -> nearest."""
    dx, dy = tx - cx, ty - cy
    if abs(dx) <= w / 2 and abs(dy) <= h / 2:
        return v2_face(dx + w / 2, dy + h / 2, w, h)
    if abs(dx) / (w / 2) >= abs(dy) / (h / 2):
        return 'E' if dx > 0 else 'W'
    return 'N' if dy > 0 else 'S'


def orient_face(f, o):
    """instance-frame face -> core R0 frame face (MX mirrors y, MY mirrors x; self-inverse)."""
    if o in ('MX', 'R180', 'R') and f in 'NS':
        return OPP[f]
    if o in ('MY', 'R180', 'R') and f in 'EW':
        return OPP[f]
    return f


def to_core(o, w, h, x, y):
    """instance-frame offset from the core origin -> core R0 frame point."""
    if o in ('MY', 'R180', 'R'):
        x = w - x
    if o in ('MX', 'R180', 'R'):
        y = h - y
    return x, y


def bitkey(n):
    m = re.match(r'^(.*)\[(\d+)\]$', n)
    return (m.group(1), int(m.group(2))) if m else (n, -1)


def base(n):
    return bitkey(n)[0]


# ------------------------------------------------------------------------------------------------ split netlists
def split_defs(n, m):
    """pieces of master m as gen_core_ports.py cuts them: {label: (include, exclude, strip)}."""
    import gen_core_ports as g
    fp = g.find_paths
    D = {}
    if m == 'ot_hgi_sfu_core_split3':
        sfu, maps = fp(n, m, r'ot_su12_sfu'), fp(n, m, r'sfu_lane_map')
        grp, mem = fp(n, m, r'su_lgroup2'), fp(n, m, r'operand_store')
        lanes = []
        for k in range(16):
            inc = [p for p in sfu + maps if f'g_lane[{k}].' in p]
            lanes += inc
            D[f'lane{k}'] = (inc, [], inc[0].rsplit('/', 1)[0] + '/')
        gb = [p for p in grp if not re.search(r'g_operand\[[01]\]', p)]
        D['opstore_a'] = (mem, gb, mem[0] + '/')
        D['opstore_b'] = (gb, [], mem[0] + '/')
        D['ctl'] = ([''], lanes + mem, '')
    elif m == 'ot_hgi_coll_tkm_m_tp192':
        tiles = fp(n, m, r'tkm_tile_e86')
        for tp in tiles:
            D['tile' + re.search(r'g_tiles\[(\d+)\]', tp).group(1)] = ([tp], [], tp + '/')
        D['root'] = ([''], tiles, '')
    elif m == 'ot_hfd_coll_q2_hard_v8g':
        ring, red = fp(n, m, r'coll_ring_ag$'), fp(n, m, r'coll_reduce_static$')
        D['ring_ag'] = (ring, [], ring[0].rsplit('/', 1)[0] + '/')
        D['reduce'] = (red, [], red[0].rsplit('/', 1)[0] + '/')
        D['body'] = ([''], ring + red, '')
    elif m == 'ot_hbm_hc_root_static':
        tails = sorted(fp(n, m, r'hc_tail_unit'))
        for k, tp in enumerate(tails):
            sink = [s for s in fp(n, m, r'ot_hdc_sinkhorn') if s.startswith(tp + '/')]
            D[f'tail{k}_rest'] = ([tp], sink, tp + '/')
            D[f'tail{k}_sk'] = (sink, [], '')          # Sinkhorn = step0 + steady twins (rule inside)
        D['hcp_sys1'] = (fp(n, m, r'hcp_sys1'), [], '')
    elif m == 'ot_hbm_idx_score_quarter_static':
        for tp in fp(n, m, r'idx_tail_native'):
            D['tail' + re.search(r'ge\[(\d+)\]', tp).group(1)] = ([tp], [], '')
    return D


def own_labels(n, m, include, exclude):
    """netcut.Netlist.cut's labelling, plus one member pin bit id per boundary net (bit ids of member pins are the
    same strings in any view that expands the member's parents)."""
    import netcut
    exp = set()
    for p in list(include) + list(exclude):
        parts = p.split('/')
        for k in range(1, len(parts)):
            exp.add('/'.join(parts[:k]))
    insts, unions, _ = n.view(m, exp)
    uf = {}

    def find(x):
        r = x
        while uf.get(r, r) != r:
            r = uf[r]
        while uf.get(x, x) != r:
            uf[x], x = r, uf[x]
        return r
    for a, b in unions:
        ra, rb = find(a), find(b)
        if ra != rb:
            uf[ra] = rb
    cz = find('C')

    def ism(nm):
        inc = any(nm == p or nm.startswith(p + '/') for p in include) or ('' in include)
        exc = any(nm == p or nm.startswith(p + '/') for p in exclude)
        return inc and not exc
    users = collections.defaultdict(set)
    drv, lab_m, lab_o, lab_p, mbit = {}, {}, {}, {}, {}
    topm = n.mods[n.resolve(m)]
    for p in topm.ports:
        for b in n.bits(topm, p[0]):
            c = find(b)
            users[c].add('o')
            lab_p.setdefault(c, p[0])
    for name, t, cb in insts:
        mem = ism(name)
        hier = t in n.mods
        pd = n.port_dirs(t)
        for pn, bl in cb.items():
            d = (pd or {}).get(pn) or ('output' if pn in netcut.STD_OUT else 'input')
            for k, b in enumerate(bl):
                if b == 'C':
                    continue
                c = find(b)
                if c == cz:
                    continue
                users[c].add('m' if mem else 'o')
                if mem:
                    lab_m.setdefault(c, f'{name}.{pn}' if hier else None)
                    mbit.setdefault(c, b)
                    if d == 'output':
                        drv[c] = True
                elif hier:
                    lab_o.setdefault(c, f'{name}.{pn}')
    res = dict(inp=collections.Counter(), out=collections.Counter())
    lab_bits = []
    for c in lab_m:
        if 'o' not in users[c]:
            continue
        lbl = lab_p.get(c) or lab_m[c] or (('~' + lab_o[c]) if c in lab_o else 'glue')
        res['out' if c in drv else 'inp'][lbl] += 1
        lab_bits.append((lbl, mbit[c]))
    return res, lab_bits


def analyse_master(netdir, m):
    """-> {'pieces': {label: {cutname: {dest: bits}}}, 'ports': {master port: {label: bits}}, 'names': {label: [cut]}}
    dest = 'T:<master port>' | 'P:<label>' | 'G' (glue outside every piece: only the remainder's own logic)."""
    import netcut
    import gen_core_ports as g
    n = netcut.Netlist(os.path.join(netdir, f'{m}.netlist.v'))
    D = split_defs(n, m)
    exp = set()
    for inc, exc, _ in D.values():
        for p in list(inc) + list(exc):
            parts = p.split('/')
            for k in range(1, len(parts)):
                exp.add('/'.join(parts[:k]))
    insts, unions, _ = n.view(m, exp)
    uf = {}

    def find(x):
        r = x
        while uf.get(r, r) != r:
            r = uf[r]
        while uf.get(x, x) != r:
            uf[x], x = r, uf[x]
        return r
    for a, b in unions:
        ra, rb = find(a), find(b)
        if ra != rb:
            uf[ra] = rb
    cz = find('C')
    explicit = [(lb, inc, exc) for lb, (inc, exc, _) in D.items() if '' not in inc]
    rema = [(lb, inc, exc) for lb, (inc, exc, _) in D.items() if '' in inc]

    def under(nm, ps):
        return any(nm == p or nm.startswith(p + '/') for p in ps)

    def piece_of(nm):
        for lb, inc, exc in explicit:
            if under(nm, inc) and not under(nm, exc):
                return lb
        for lb, inc, exc in rema:
            if not under(nm, exc):
                return lb
        return None
    topm = n.mods[n.resolve(m)]
    tport = collections.defaultdict(set)
    lab_p = {}
    for p in topm.ports:
        for b in n.bits(topm, p[0]):
            c = find(b)
            tport[c].add(p[0])
            lab_p.setdefault(c, p[0])
    users = collections.defaultdict(set)
    per = {lb: dict(drv={}, lab_m={}, lab_o={}) for lb in D}
    for name, t, cb in insts:
        pc = piece_of(name)
        hier = t in n.mods
        pd = n.port_dirs(t)
        for pn, bl in cb.items():
            d = (pd or {}).get(pn) or ('output' if pn in netcut.STD_OUT else 'input')
            for b in bl:
                if b == 'C':
                    continue
                c = find(b)
                if c == cz:
                    continue
                users[c].add(pc)
                for lb in D:
                    if lb == pc:
                        per[lb]['lab_m'].setdefault(c, f'{name}.{pn}' if hier else None)
                        if d == 'output':
                            per[lb]['drv'][c] = True
                    elif hier:
                        per[lb]['lab_o'].setdefault(c, f'{name}.{pn}')
    out = dict(pieces={}, ports=collections.defaultdict(collections.Counter), names={})
    for lb, (inc, exc, strip) in D.items():
        res, lab_bits = own_labels(n, m, inc, exc)      # labels exactly as netcut.cut (the piece's own view)
        names = g.busify(res, strip)
        lbls = [l for k in ('inp', 'out') for l in sorted(res[k])]
        l2n = {l: nm[0] for l, nm in zip(lbls, names)}
        dest = collections.defaultdict(collections.Counter)
        for lbl, bit in lab_bits:
            cn = l2n[lbl]
            c = find(bit)
            for o in users[c] - {lb}:
                dest[cn]['P:' + o if o else 'G'] += 1
            for tp in tport.get(c, ()):
                dest[cn]['T:' + tp] += 1
                out['ports'][tp][lb] += 1
            if not (users[c] - {lb}) and c not in tport:
                dest[cn]['?'] += 1
        out['pieces'][lb] = {k: dict(v) for k, v in dest.items()}
        out['names'][lb] = [nm[0] for nm in names]
    out['ports'] = {k: dict(v) for k, v in out['ports'].items()}
    return out


# ------------------------------------------------------------------------------------------------ plan connectivity
class Plan:
    def __init__(self, plan_path):
        root = Path(plan_path).resolve().parent
        self.root = root
        self.p = json.load(open(plan_path))
        self.where = json.load(open(root / 'v2_assign.json'))['where']
        self.lm = json.load(gzip.open(root / 'lane_members.json.gz'))
        self.rows = []
        with gzip.open(root / 'census' / 'hbm_r18h5_rows.tsv.gz', 'rt') as fh:
            next(fh)
            for line in fh:
                s, sb, d, db, k, b = line.rstrip('\n').split('\t')
                self.rows.append((s, sb, d, db, int(b)))
        self.parts = {x['name']: x for x in self.p['partitions']}
        self.net2lane = collections.defaultdict(set)
        for L, v in self.lm.items():
            for nt in v['nets']:
                self.net2lane[nt].add(L)
        self.ports_by_lane = collections.defaultdict(list)
        for pt in self.p['ports']:
            m = re.match(r'^(L\d+)s\d+([a-z]?)_\d+$', pt['id'])
            if m:
                self.ports_by_lane[m.group(1) + m.group(2)].append(pt)
        self.rows_src = collections.defaultdict(list)
        self.rows_dst = collections.defaultdict(list)
        for r in self.rows:
            self.rows_src[r[0]].append(r)
            self.rows_dst[r[2]].append(r)

    def lanes_of(self, net):
        out = set(self.net2lane.get(net, ()))
        for q in ('NW', 'NE', 'SW', 'SE'):
            out |= self.net2lane.get(f'{net}_q{q}', set())
        return out

    def part_ctx(self, tn):
        """representative partition instance of type tn + content maps (type-local names <-> die instances)."""
        t = self.p['partition_types'][tn]
        u2d = {}
        for c in t['contents']:
            d = c.get('note', '').split(':')[0]
            if d in self.where:
                u2d[c['inst']] = d
        pns = collections.Counter(self.where[d] for d in u2d.values())
        pn = pns.most_common(1)[0][0] if pns else next(x['name'] for x in self.p['partitions'] if x['type'] == tn)
        u2d = {u: d for u, d in u2d.items() if self.where[d] == pn}
        P = self.parts[pn]
        w, h = t['outline_um']
        ox, oy = P['origin_um']
        op = P['orient']

        def die2type(x, y):
            lx, ly = x - ox, y - oy
            if op in ('MY', 'R180', 'R'):
                lx = w - lx
            if op in ('MX', 'R180', 'R'):
                ly = h - ly
            return lx, ly

        def port_pt(pt, end):
            f = pt['face'] if end == 'src' else OPP[pt['face']]
            lo, hi = pt['window_um']
            a = (lo + hi) / 2
            if f == 'W':
                x, y = ox, a
            elif f == 'E':
                x, y = ox + w, a
            elif f == 'S':
                x, y = a, oy
            else:
                x, y = a, oy + h
            return die2type(x, y)
        n_inst = sum(1 for x in self.p['partitions'] if x['type'] == tn)
        return dict(t=t, pn=pn, u2d=u2d, d2u={d: u for u, d in u2d.items()}, port_pt=port_pt, n_inst=n_inst, w=w, h=h)

    def content_port_targets(self, ctx, u, port):
        """content u's port -> [(kind, ref, bits)]: ('pt', (x, y)) partition-face point; ('c', (uL, portL))."""
        out = []
        d = ctx['u2d'].get(u)
        pn = ctx['pn']
        if d is None:
            for b in ctx['t']['buses']:
                if b['leaf'] == f'{u}.{port}':
                    out += self._bus_pts(ctx, b['name'], b['width'])
            return out
        net = f'{d}.{port}'
        for L in self.lanes_of(net):
            pts = [pt for pt in self.ports_by_lane.get(L, []) if pt['src']['part'] == pn]
            for pt in pts:
                out.append(('pt', ctx['port_pt'](pt, 'src'), pt['width'] / max(1, len(self.lm[L]['nets']))))
        for (s, sb, dd, db, bits) in self.rows_src.get(d, ()):
            if sb != port:
                continue
            if dd in ctx['d2u']:
                out.append(('c', (ctx['d2u'][dd], db), bits))
        for (s, sb, dd, db, bits) in self.rows_dst.get(d, ()):
            if db != port:
                continue
            if s in ctx['d2u']:
                out.append(('c', (ctx['d2u'][s], sb), bits))
                continue
            for L in self.lanes_of(f'{s}.{sb}'):
                for pt in self.ports_by_lane.get(L, []):
                    if pt['dst']['part'] == pn:
                        out.append(('pt', ctx['port_pt'](pt, 'dst'), bits))
        return out

    def _bus_pts(self, ctx, bus, width):
        out = []
        for pt in self.p['ports']:
            for end in ('src', 'dst'):
                if pt[end]['part'] == ctx['pn'] and pt[end]['bus'] == bus:
                    out.append(('pt', ctx['port_pt'](pt, end), width))
        return out


# ------------------------------------------------------------------------------------------------ per instance targets
SM_TCC = {'tcc_i_v': 'i_v', 'tcc_i_first': 'i_first', 'tcc_i_qk_last': 'i_qk_last', 'tcc_i_pv_last': 'i_pv_last',
          'tcc_i_run_first': 'i_run_first', 'tcc_i_run_last': 'i_run_last', 'tcc_i_tag': 'i_tag', 'tcc_i_w': 'i_w',
          'tcc_i_x': 'i_x', 'tcc_pub_start': 'pub_start', 'tcc_pub_slot': 'pub_slot', 'tcc_fold_start': 'fold_start',
          'tcc_fold_a': 'fold_a', 'tcc_fold_b': 'fold_b', 'tcc_ov': 'ov', 'tcc_y': 'y', 'tcc_otag': 'otag',
          'tcc_fault': 'fault', 'tcc_pub_v': 'pub_v', 'tcc_pub_data': 'pub_data', 'tcc_pub_word': 'pub_word',
          'tcc_pub_out_slot': 'pub_out_slot'}


class Resolver:
    def __init__(self, plan, split, args):
        self.plan = plan
        self.split = split          # master module -> analyse_master result
        self.ctx = {}
        self._mi = {}

    def c(self, tn):
        if tn not in self.ctx:
            self.ctx[tn] = self.plan.part_ctx(tn)
        return self.ctx[tn]

    @staticmethod
    def rect_centre(r):
        return r['origin_um'][0] + r['outline_um'][0] / 2, r['origin_um'][1] + r['outline_um'][1] / 2

    def content_rect(self, ctx, u):
        for c in ctx['t']['contents']:
            if c['inst'] == u and 'origin_um' in c:
                return c
        return None

    def master_port_points(self, ctx, u, port, depth=0):
        """points a content port reaches -> [(xy, bits, how)]."""
        res = []
        for kind, ref, bits in self.plan.content_port_targets(ctx, u, port):
            if kind == 'pt':
                res.append((ref, bits, 'port'))
            else:
                uL, pL = ref
                res += [(xy, bits * f, 'core') for xy, f in self.content_entry(ctx, uL, pL)]
        return res

    def content_entry(self, ctx, uL, pL):
        """where content uL's port pL physically is: its rect centre, or the split pieces touching pL."""
        cr = self.content_rect(ctx, uL)
        if cr is None:
            return [(r[1], 1.0) for r in self.plan.content_port_targets(ctx, uL, pL) if r[0] == 'pt']
        mod = cr['module']
        if mod in self.split:
            pcs = self.split[mod]['ports'].get(pL, {})
            tot = sum(pcs.values())
            hcs = {h['inst']: h for h in ctx['t'].get('hard_cores', [])}
            out = []
            for lb, k in pcs.items():
                h = hcs.get(f'{uL}_{lb}') or hcs.get(f'{uL}_{lb}_step0')
                if h:
                    out.append((self.rect_centre(h), k / tot))
            if out:
                return out
        return [(self.rect_centre(cr), 1.0)]

    def die_edge_point(self, ctx):
        P = self.plan.parts[ctx['pn']]
        DW, DH = self.plan.p['die']['outline_um']
        ox, oy = P['origin_um']
        w, h = ctx['w'], ctx['h']
        d = dict(W=ox, E=DW - (ox + w), S=oy, N=DH - (oy + h))
        f = min(d, key=d.get)
        if d[f] > 1.0:
            return None
        f = orient_face(f, P['orient'])                      # die frame -> type frame (mirror is self-inverse)
        return dict(W=(0, h / 2), E=(w, h / 2), S=(w / 2, 0), N=(w / 2, h))[f]

    def clock_point(self, ctx, inst):
        ck = ctx['t'].get('clock', {})
        for tp in ck.get('taps', []):
            if tp['name'].split('.')[0] == inst:
                return tp['xy']
        return ck.get('tap_um')

    def targets(self, tn, h, pins):
        """hard core instance h of partition type tn -> {pin base: [(xy type frame, bits, how)]}, how in
        port/core/rule/clock."""
        ctx = self.c(tn)
        t = ctx['t']
        inst, mod = h['inst'], h['module']
        bases = collections.OrderedDict()
        for p in pins:
            bases.setdefault(base(p['name']), 0)
            bases[base(p['name'])] += 1
        T = collections.defaultdict(list)
        hcs = {x['inst']: x for x in t.get('hard_cores', [])}
        conts = {c['inst']: c for c in t['contents']}
        for b in bases:
            if re.match(r'^(clk|rst|tile_clk|clk_pair|rst_col|ck)', b) or re.search(r'(^|_)(clk|rst_n|rst)(_|$)', b):
                xy = self.clock_point(ctx, inst)
                if xy:
                    T[b].append((tuple(xy), bases[b], 'clock'))
        if inst in conts and conts[inst]['module'] == mod:            # whole content = this hard core
            for b in bases:
                if b in T:
                    continue
                T[b] += self.master_port_points(ctx, inst, b)
                if not T[b] and b.startswith('pma_'):              # SerDes PMA: off-die, to the die-edge face
                    xy = self.die_edge_point(ctx)
                    if xy:
                        T[b].append((xy, bases[b], 'rule'))
            return T
        if inst.startswith('sm_'):
            return self.sm_rules(ctx, h, bases, T)
        m = re.match(r'^(u\d+)_(.+)$', inst)
        if not m:
            return T
        u, lb = m.groups()
        cr = conts.get(u)
        master = cr['module'] if cr else None
        A = self.split.get(master)
        if A is not None and lb in A['pieces']:
            cut = A['pieces'][lb]
            for b in bases:
                if b in T:
                    continue
                for dest, k in cut.get(b, {}).items():
                    if dest.startswith('T:'):
                        pts = self.master_port_points(ctx, u, dest[2:])
                        tot = sum(x[1] for x in pts) or 1
                        T[b] += [(xy, k * bb / tot, how) for xy, bb, how in pts]
                    elif dest == 'G' and cr and 'origin_um' in cr:
                        T[b].append((self.rect_centre(cr), k, 'rule'))
                    elif dest.startswith('P:'):
                        hh = hcs.get(f'{u}_{dest[2:]}') or hcs.get(f'{u}_{dest[2:]}_step0')
                        if hh:
                            T[b].append((self.rect_centre(hh), k, 'core'))
            return T
        # RTL twins
        if master == 'ot_hbm_hc_root_static' and re.match(r'tail\d+_sk_(step0|steady)$', lb):
            k = lb[4]
            rest, s0, st = hcs.get(f'{u}_tail{k}_rest'), hcs.get(f'{u}_tail{k}_sk_step0'), hcs.get(f'{u}_tail{k}_sk_steady')
            for b in bases:
                if b in T:
                    continue
                if b in ('load', 'pa', 'pb', 'b_q', 'bbad_q', 'abad_q'):          # step0 <-> steady
                    other = st if lb.endswith('step0') else s0
                else:                                                            # in_e / y / valid / fault ...
                    other = rest
                if other:
                    T[b].append((self.rect_centre(other), bases[b], 'rule'))
            return T
        mm = re.match(r'^r(\d)c(\d)_k(\d)h(\d)$', lb)
        if master == 'ot_hbm_idx_score_quarter_static' and mm:
            r_, c_, k_, h_ = map(int, mm.groups())
            seq = [f'r{r}c{c}_k{k}h{hh}' for r in range(2) for c in range(4) for k in range(4) for hh in range(2)]
            i = seq.index(lb)
            prv = hcs.get(f'{u}_{seq[i - 1]}') if i % 2 == 1 else None       # HALF 1 takes the HALF 0 partial
            nxt = hcs.get(f'{u}_{seq[i + 1]}') if i % 2 == 0 else None
            tail = hcs.get(f'{u}_tail{r_ % 2}') or hcs.get(f'{u}_tail0')
            for b in bases:
                if b in T:
                    continue
                if b in ('cs_in', 'cf_in') and prv:
                    T[b].append((self.rect_centre(prv), bases[b], 'rule'))
                elif b in ('cs_out', 'cf_out', 'prdy'):
                    T[b].append((self.rect_centre(nxt or tail), bases[b], 'rule'))
                elif b in ('q_b', 'qv_b', 'key', 'hid4'):
                    for xy, k, _ in self.master_inputs(ctx, u):
                        T[b].append((xy, k, 'rule'))
            return T
        return T

    def master_inputs(self, ctx, u):
        key = (ctx['pn'], u)
        if key not in self._mi:
            d = ctx['u2d'].get(u)
            ports = sorted({r[3] for r in self.plan.rows_dst.get(d, ())})
            pts = []
            for p in ports:
                pts += [x for x in self.master_port_points(ctx, u, p) if x[2] == 'port']
            self._mi[key] = pts
        return self._mi[key]

    def sm_rules(self, ctx, h, bases, T):
        """SM quarter (row = ln lx ln lx tp, +front row): lx <-> tp of its row (rl1/bk1/ohl1/g*), lx <-> the ln on its
        W (tcc_*), tp lh_* -> its two lx (first half -> W lx), tp rin/bin from the row below (S), rout/bout to the
        row above (N), front rl/rr/bl/br/ql/qr -> the bottom tile row, front command/packet/... -> smq buses."""
        t = ctx['t']
        hc = t['hard_cores']
        cx, cy = self.rect_centre(h)
        row = [x for x in hc if abs(x['origin_um'][1] - h['origin_um'][1]) < 1]
        row.sort(key=lambda x: x['origin_um'][0])
        kind = re.match(r'sm_([a-z]+)\d+', h['inst']).group(1)

        def near(k, left_only=False):
            c = [x for x in row if x['inst'].startswith('sm_' + k)]
            if left_only:
                c = [x for x in c if x['origin_um'][0] < h['origin_um'][0]]
            c.sort(key=lambda x: abs(x['origin_um'][0] - h['origin_um'][0]))
            return c[0] if c else None
        w, hh = h['outline_um']

        def add(b, xy):
            if b in bases and b not in T:
                T[b].append((xy, bases[b], 'rule'))
        if kind == 'lx':
            tp, ln = near('tp'), near('ln', True)
            for b in ('rl1', 'bk1', 'ohl1', 'gv', 'gf', 'gy', 'gt'):
                if tp:
                    add(b, self.rect_centre(tp))
            for b in bases:
                if b.startswith('tcc_') and ln:
                    add(b, self.rect_centre(ln))
        elif kind == 'ln':
            lx = [x for x in row if x['inst'].startswith('sm_lx') and x['origin_um'][0] > h['origin_um'][0]]
            lx.sort(key=lambda x: x['origin_um'][0])
            for b in set(SM_TCC.values()):
                if lx:
                    add(b, self.rect_centre(lx[0]))
        elif kind == 'tp':
            lxs = sorted([x for x in row if x['inst'].startswith('sm_lx')], key=lambda x: x['origin_um'][0])
            for b in ('lh_rl1', 'lh_bk1', 'lh_ohl1', 'lh_gv', 'lh_gf', 'lh_gy', 'lh_gt'):
                if b in bases and lxs:
                    n = bases[b]
                    k = len(lxs)
                    for j, x in enumerate(lxs):
                        T[b].append((self.rect_centre(x), n / k, 'rule'))
            for b in ('rin', 'bin', 'gin'):
                add(b, (cx, cy - 10 * hh))
            for b in ('rout', 'bout', 'gout'):
                add(b, (cx, cy + 10 * hh))
        elif kind in ('fs', 'fa'):
            tps = [x for x in hc if x['inst'].startswith('sm_tp')]
            if tps:
                tp = min(tps, key=lambda x: abs(x['origin_um'][1] - h['origin_um'][1]))
                for b in ('rl', 'rr', 'bl', 'br', 'ql', 'qr'):
                    add(b, self.rect_centre(tp))
            for b in bases:
                if b not in T:
                    pts = []
                    for bb in t['buses']:
                        if bb['leaf'] == f'smq.{b}':
                            pts += self.plan._bus_pts(ctx, bb['name'], bb['width'])
                    for _, xy, k in pts:
                        T[b].append((xy, k, 'port'))
        return T


# ------------------------------------------------------------------------------------------------ placement
def assign_faces(pins, w, h, pref, score):
    """pref: pin -> face; score: pin -> {face: pull}.  Returns (faces {f: [names]}, spills [(pin, from, to)])."""
    faces = {f: [] for f in 'NSEW'}
    for p in pins:
        faces[pref[p]].append(p)
    cap = {f: face_cap(w if f in 'NS' else h, 'M5' if f in 'NS' else 'M4') for f in 'NSEW'}
    spills = []
    for rnd in range(2):
        for f in sorted('NSEW', key=lambda f: -(len(faces[f]) - cap[f])):
            over = len(faces[f]) - cap[f]
            if over <= 0:
                continue
            cand = ADJ[f] if rnd == 0 else ADJ[f] + OPP[f]
            # move whole-bus tails first: rank pins by the best alternative pull (loss = pull here - pull there)
            opts = []
            for p in faces[f]:
                for g in cand:
                    opts.append((score[p][f] - score[p][g], bitkey(p), p, g))
            opts.sort()
            moved = set()
            for loss, _, p, g in opts:
                if over <= 0:
                    break
                if p in moved or len(faces[g]) >= cap[g]:
                    continue
                faces[g].append(p)
                moved.add(p)
                spills.append((p, f, g))
                over -= 1
            faces[f] = [p for p in faces[f] if p not in moved]
    return faces, cap


def place(faces, w, h, along):
    out, st = [], {}
    for f, names in faces.items():
        if not names:
            continue
        L = h if f in 'EW' else w
        layer = 'M4' if f in 'EW' else 'M5'
        tr = tracks(L, layer)
        # bus-level order by mean target along-coordinate, then bit order inside the bus
        busm = collections.defaultdict(list)
        for nm in names:
            busm[base(nm)].append(along[f].get(nm, L / 2))
        bm = {b: sum(v) / len(v) for b, v in busm.items()}
        names = sorted(names, key=lambda nm: (bm[base(nm)], bitkey(nm)))
        n = len(names)
        if n > len(tr):
            raise ValueError(f'{n} pins > {len(tr)} tracks on face {f}')
        pos = []
        lo, hi = tr[0], tr[-1]
        last = -1
        for j, nm in enumerate(names):
            ideal = lo + (j + 0.5) * (hi - lo) / n          # even in SPACE (PG-stripe gaps do not compress pins)
            k = bisect.bisect_left(tr, ideal)
            if k > 0 and (k >= len(tr) or ideal - tr[k - 1] < tr[k] - ideal):
                k -= 1
            k = min(max(k, last + 1), len(tr) - (n - j))
            last = k
            a = tr[k]
            pos.append(a)
            if f in 'EW':
                out.append(dict(name=nm, layer=layer, x=INSET if f == 'W' else round(w - INSET, 4), y=a))
            else:
                out.append(dict(name=nm, layer=layer, x=a, y=INSET if f == 'S' else round(h - INSET, 4)))
        pos.sort()
        worst, i0 = 0, 0
        for i1 in range(len(pos)):
            while pos[i1] - pos[i0] >= 10.0:
                i0 += 1
            worst = max(worst, i1 - i0 + 1)
        st[f] = dict(pins=n, per_um=round(n / L, 3), per_um_usable=round(n / max(1e-9, L - 2 * KEEP), 3),
                     worst_10um=worst / 10.0, layer=layer, cap=face_cap(L, layer))
    return sorted(out, key=lambda p: bitkey(p['name'])), st


def min_outline(npins, w, h):
    s = 1.0
    while True:
        W_, H_ = math.ceil(w * s / 4.32 - 1e-9) * 4.32, math.ceil(h * s / 4.32 - 1e-9) * 4.32
        cap = 2 * face_cap(W_, 'M5') + 2 * face_cap(H_, 'M4')
        if cap >= npins:
            return [round(W_, 3), round(H_, 3)]
        s *= 1.01


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default=str(HERE.parent.parent / 'die_plan.json'))
    ap.add_argument('--census', default=str(HERE / 'census_3a7e22238.json'))
    ap.add_argument('--out', default=str(HERE / 'pins_v3c'))
    ap.add_argument('--net', default='/home/ubuntu/scratch/hbm-p5-pins-1023/net')
    ap.add_argument('--cache', default='/home/ubuntu/scratch/core-hbm-repin/cache')
    ap.add_argument('--types')
    ap.add_argument('--alt', action='append', default=[], help='type_id regex=WxH: also place matching types on this outline')
    a = ap.parse_args()
    plan = Plan(a.plan)
    root = plan.root
    cen = json.load(open(a.census))['types']
    want = set(a.types.split(',')) if a.types else None
    alt = {}
    for s in a.alt:
        k, v = s.split('=')
        alt[k] = [float(x) for x in v.split('x')]
    # split masters in scope
    split = {}
    os.makedirs(a.cache, exist_ok=True)
    for m in ('ot_hgi_sfu_core_split3', 'ot_hgi_coll_tkm_m_tp192', 'ot_hfd_coll_q2_hard_v8g', 'ot_hbm_hc_root_static',
              'ot_hbm_idx_score_quarter_static'):
        cf = Path(a.cache) / f'{m}.conn.json'
        if not cf.exists():
            print('analyse', m, flush=True)
            json.dump(analyse_master(a.net, m), open(cf, 'w'))
        split[m] = json.load(open(cf))
    R = Resolver(plan, split, a)
    # group census rows -> types (one pin set per type_id; rows with a different pin set get a suffix)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summ, stats = {}, collections.Counter()
    groups = collections.OrderedDict()
    for r in cen:
        if want and r['type_id'] not in want:
            continue
        if r['excluded'].startswith('ALL'):
            continue
        parts = [p for p in r['parts'] if not SKIP_PART.match(p)]
        if not parts:
            continue
        w, h = r['outline_um']
        v2 = json.load(open(root / r['pins_file']))
        names = sorted(p['name'] for p in v2)
        fn = f"{r['module']}__{w:g}x{h:g}.json"
        if fn in groups and groups[fn]['names'] != names:
            fn = fn.replace('.json', f"__{Path(r['pins_file']).parent.name}.json")
        grp = groups.setdefault(fn, dict(r=r, v2=v2, names=names, rows=[]))
        grp['rows'].append((r, parts))
    for fn, grp in groups.items():
        r, v2 = grp['r'], grp['v2']
        tid = r['type_id']
        w, h = r['outline_um']
        names = [p['name'] for p in v2]
        parts = sorted({p for _, ps in grp['rows'] for p in ps})
        insts = []
        for rr, ps in grp['rows']:
            for tn in ps:
                t = plan.p['partition_types'][tn]
                for hc in t.get('hard_cores', []):
                    if hc['module'] == rr['module'] and hc['outline_um'] == [w, h] and \
                            hc.get('pins_file') == rr['pins_file']:
                        insts.append((tn, hc))
        votes = {nm: collections.Counter() for nm in names}
        pull = {nm: collections.Counter() for nm in names}
        alongs = {nm: collections.defaultdict(list) for nm in names}
        how = collections.Counter()
        v2f = {p['name']: v2_face(p['x'], p['y'], w, h) for p in v2}
        v2a = {p['name']: (p['x'] if v2f[p['name']] in 'NS' else p['y']) for p in v2}
        bypin_base = collections.defaultdict(list)
        for nm in names:
            bypin_base[base(nm)].append(nm)
        for b in bypin_base:
            bypin_base[b].sort(key=bitkey)
        unres = collections.Counter()
        for tn, hc in insts:
            wt = sum(1 for x in plan.p['partitions'] if x['type'] == tn)
            T = R.targets(tn, hc, v2)
            ox, oy = hc['origin_um']
            o = hc.get('orient', 'R0')
            cx, cy = ox + w / 2, oy + h / 2
            for b, nms in bypin_base.items():
                tg = [x for x in T.get(b, []) if x[1] > 0]
                if not tg:
                    for nm in nms:
                        how['unresolved'] += wt
                    unres[b] += len(nms)
                    continue
                # allocate bits to targets (grouped by face, ordered along the face) proportionally
                ft = []
                for xy, bits, hw in tg:
                    fi = ray_face(cx, cy, w, h, xy[0], xy[1])
                    fc = orient_face(fi, o)
                    px, py = to_core(o, w, h, xy[0] - ox, xy[1] - oy)
                    ft.append((fc, py if fc in 'EW' else px, bits, hw, (px - w / 2) / (w / 2), (py - h / 2) / (h / 2)))
                ft.sort(key=lambda z: ('NESW'.index(z[0]), z[1]))
                tot = sum(z[2] for z in ft)
                acc, j = 0.0, 0
                n = len(nms)
                bounds = []
                for z in ft:
                    acc += z[2]
                    bounds.append(acc / tot * n)
                for i, nm in enumerate(nms):
                    while j < len(ft) - 1 and i + 0.5 > bounds[j]:
                        j += 1
                    fc, al, _, hw, vx, vy = ft[j]
                    votes[nm][fc] += wt
                    alongs[nm][fc].append(al)
                    s = pull[nm]
                    s['E'] += wt * vx; s['W'] -= wt * vx; s['N'] += wt * vy; s['S'] -= wt * vy
                    how[hw] += wt
        npins = len(names)
        pref, score, along = {}, {}, {f: {} for f in 'NSEW'}
        conflicts = []
        for nm in names:
            if votes[nm]:
                f, k = votes[nm].most_common(1)[0]
                if len(votes[nm]) > 1:
                    conflicts.append(nm)
                pref[nm] = f
                sc = dict(pull[nm])
                tw = sum(votes[nm].values())
                score[nm] = {g: sc.get(g, 0.0) / tw + (1.0 if g == f else 0.0) for g in 'NSEW'}
                for g, v in alongs[nm].items():
                    along[g][nm] = sum(v) / len(v)
            else:
                pref[nm] = v2f[nm]
                score[nm] = {g: (1.0 if g == v2f[nm] else 0.0) for g in 'NSEW'}
            for g in 'NSEW':
                along[g].setdefault(nm, v2a[nm] if g == pref[nm] else ((w if g in 'NS' else h) / 2))
        tot_how = sum(how.values()) or 1
        resolved = 1 - how['unresolved'] / tot_how
        rec = dict(type_id=tid, module=r['module'], outline_um=[w, h], pins=npins, instances=len(insts),
                   partitions=parts, src_pins_files=sorted({rr['pins_file'] for rr, _ in grp['rows']}),
                   resolved_pct=round(100 * resolved, 1),
                   how={k: round(100 * v / tot_how, 1) for k, v in how.items()},
                   orient_conflicts=len(conflicts), conflict_examples=conflicts[:5],
                   unresolved_buses=dict(unres.most_common(12)))
        outlines = [('plan', [w, h])]
        perim_cap = 2 * face_cap(w, 'M5') + 2 * face_cap(h, 'M4')
        if npins > perim_cap:
            mo = min_outline(npins, w, h)
            rec['min_outline_um'] = mo
            outlines.append(('min', mo))
        alt_o = next((v for k, v in alt.items() if re.fullmatch(k, tid)), None)
        if alt_o:
            outlines.append(('alt', alt_o))
        for tag, (W_, H_) in outlines:
            sx, sy = W_ / w, H_ / h
            along2 = {g: {nm: v * (sx if g in 'NS' else sy) for nm, v in d.items()} for g, d in along.items()}
            faces, cap = assign_faces(names, W_, H_, pref, score)
            try:
                pins, st = place(faces, W_, H_, along2)
            except ValueError as e:
                rec[tag] = dict(error=str(e))
                continue
            sp = collections.Counter()
            fin = {nm: f for f, l in faces.items() for nm in l}
            for nm in names:
                if fin[nm] != pref[nm]:
                    sp[f'{pref[nm]}->{fin[nm]}'] += 1
            worst_avg = max(v['per_um_usable'] for v in st.values())
            worst_win = max(v['worst_10um'] for v in st.values())
            worst = max(worst_avg, worst_win)
            verdict = 'PASS' if worst <= CAP + 1e-6 else ('WARN' if worst <= HARD else 'FAIL')
            ffn = fn if tag == 'plan' else fn.replace(f'__{w:g}x{h:g}', f'__{W_:g}x{H_:g}')
            if tag != 'plan' and ffn == fn:
                ffn = fn.replace('.json', f'__{tag}.json')
            (out / ffn).write_text(json.dumps(pins, separators=(',', ':')) + '\n')
            rec[tag] = dict(pins_file=ffn, outline_um=[W_, H_], faces=st, worst_per_um=worst_avg,
                            worst_10um_window=worst_win, spills=dict(sp), spilled=sum(sp.values()),
                            verdict=verdict)
        rec['verdict'] = rec['plan'].get('verdict', 'FAIL') if 'plan' in rec else 'FAIL'
        rec['outline_change_needed'] = 'min_outline_um' in rec or rec['verdict'] == 'FAIL'
        if alt_o:
            rec['outline_change_needed'] = True
            rec['outline_change_note'] = 'synth std area 82-87% of the plan outline (CORE-HBM 10-23); alt outline placed'
        summ[fn[:-5]] = rec
        stats[rec['verdict']] += 1
        print(f"{rec['verdict']:4s} {fn[:-5]:70s} pins {npins:6d} res {rec['resolved_pct']:5.1f}% "
              f"worst {rec.get('plan', {}).get('worst_per_um', '-')} conf {len(conflicts)} "
              f"spill {rec.get('plan', {}).get('spilled', '-')}"
              f"{' MIN ' + str(rec['min_outline_um']) if 'min_outline_um' in rec else ''}", flush=True)
    tot_p = sum(v['pins'] for v in summ.values())
    tot_r = sum(v['pins'] * v['resolved_pct'] / 100 for v in summ.values())
    meta = dict(tool='repin_v3c.py', plan=str(Path(a.plan).name), census=Path(a.census).name,
                rules=dict(cap_per_um=CAP, hard_per_um=HARD, keepout_um=KEEP, inset_um=INSET,
                           m5_pg_blocked_track_mod_4p32=PG_BLK, skip_partitions=SKIP_PART.pattern),
                counts=dict(stats), types=len(summ), pins=tot_p,
                resolved_pct_pin_weighted=round(100 * tot_r / max(1, tot_p), 1))
    (out / 'summary.json').write_text(json.dumps(dict(meta=meta, types=summ), indent=1) + '\n')
    print(json.dumps(meta))


if __name__ == '__main__':
    main()
