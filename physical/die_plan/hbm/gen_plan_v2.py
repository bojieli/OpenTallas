#!/usr/bin/env python3
"""HBM d4g die plan v2: QUADRANT-LOCAL architecture (PLAN-HBMv2, COORD ruling 10-23 06:26; design note lanes/HBM-QLOCAL.md).

v1 (gen_plan_v1.py) replayed the as-built r18h5 placement: the VM slice hubs sat on the die centre line with their 8 banks
8-12 mm away at the W/E edges, the per-SM services of the E quadrants were named after the W ones, and every quadrant
had its own RTL variant (430 types, a 32k-pin hub, G0 FAIL 2082).  v2 is generated top-down instead:

  1. LOGICAL QUADRANTS.  Every census instance gets the quadrant it serves (label propagation seeded by the SMs:
     sm/svg/vmks/xc/cp_svg _<N|S>W<k> serve quadrant <N|S><W if k<4 else E>; ctl_<N|S>W_p<pp> -> pp<16 W else E).
  2. ONE CANONICAL QUADRANT.  Each quadrant role (name without quadrant, local index) gets the UNION of its buses over
     the four quadrants (bits = max).  The plan therefore describes the parameterised RTL (HBM-QLOCAL.md step C):
     every quadrant identical up to MX/MY; roles present in one quadrant only (qdq quant + vmm merges, NW) are
     replicated; tkm and the 5th SerDes stay die-level with their SW-only lanes.
  3. TOP-DOWN FLOORPLAN.  The NW quadrant is a fixed partition table (LAYOUT, 8.64-um lattice units), mirrored MY/MX/R180.
     The VM slice (hub + 8 banks + delivery lanes) is ONE partition in the middle of the SU row, between SU0/1 and
     SU2/3 (no star: bank clients are <= 2 partitions away).  Die-level roots (IDX link/selector/ctl/xq merge, tkm,
     hc_eng, host, SU programme root, router ids, argmax) sit in ONE self-symmetric centre partition C0; every
     die-level lane is a tree C0 -> quadrant.  Cross-quadrant lanes = VM ring + COLL rings (+ obs chain) only.
  4. Small leaves are assigned to the partition that minimises their bit x distance (fixed anchors first).
  5. Lanes, routing, ports, stations, latency and types: the v1 back end (negotiated mirror-consistent routing,
     window sizing by the PLAN-TOOL pin spreader, stations ceil(L/reach), trees for broadcasts).
     V2 back-end changes (plan_backend_v2.py, marked V2): direction-sensitive window keys, mirror-consistent
     allocation of full orbits on axis segments, window length = max over the member widths (parity).
  6. Identical quadrants: every image of a bundle carries the widest member (orbit width equalisation); window
     edges on the 0.048-um grid off every M4-M7 track with odd usable-track counts for odd pin counts, so
     pin tables are mirror-exact; a die-level root drives each quadrant through its own registered output.

Outputs: die_plan.json (G0 input), lane_members.json.gz (lane -> as-built nets), v2_assign.json (instance -> partition),
plan_v2_geom.png.  Census coverage: coverage_v2.py; per-class stages for the price model: stages_v2.py.

    python3 gen_plan_v2.py [--out DIR] [--vm-ring-bits 2224] [--geom-only]
"""
import argparse, collections, gzip, json, math, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_backend_v2 as v1                               # noqa: E402  (back end: v1 graph, routing, emit, types; V2 fixes)

FT = v1.FT
G = v1.G
# ---------------------------------------------------------------------------------------------------- die
QW, QH = 1170, 1909                       # NW quadrant in lattice units (10.109 x 16.494 mm); compacted from 1400
W, H = 2 * QW * G, 2 * QH * G             # 24192.0 x 32987.52 um = 798.0 mm2 (v1 857.3)
CX, CY = W / 2, H / 2
for k, v in dict(W=W, H=H, CX=CX, CY=CY).items():
    setattr(v1, k, v)
OPS = v1.OPS
QOP = v1.QOP
mrect = v1.mrect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'die_plan'))
import schema as dp_schema                                    # noqa: E402  (PLAN-TOOL pin spreader, PG-stripe aware)
LAYER_T = {L['name']: L for L in dp_schema.ASAP7_LAYERS}
# Window edges sit on E = {0.048 j : j mod 4 != 2}: never on an M4-M7 track (M4/M5 0.024 + 0.048k, M6/M7 0.032 + 0.064k),
# mirror-symmetric on the die (W, H and 8.64 are multiples of 0.192).  Windows abut edge to edge (no shared track).
# PLAN-TOOL schema.pin_positions picks the middle track (m-1)//2 for odd n, which is not mirror-invariant when m is
# even, so windows are grown until every layer with an odd pin count has an odd usable-track count.
EQ = 0.048


def edge_ok(x):
    j = round(x / EQ)
    return abs(x - j * EQ) < 1e-6 and j % 4 != 2


def next_edge(x):
    j = math.ceil(x / EQ - 1e-6)
    while j % 4 == 2:
        j += 1
    return j * EQ


def usable(lo, hi, ln):
    L = LAYER_T[ln]; p_, off = L['pitch_um'], L['offset_um']
    k0 = math.ceil((lo - off) / p_ - 1e-9); k1 = math.floor((hi - off) / p_ + 1e-9)
    return sum(1 for k in range(k0, k1 + 1) if not dp_schema.pg_blocked(ln, off + k * p_))


def fit_len_v2(lo, pins, layers):
    a = next_edge(lo)
    nl = len(layers)
    b = next_edge(a + pins / (v1.WIN_PER_UM * max(2, nl) / 2))   # P6: a 3-layer face starts at 1.5x the density
    while True:
        ok = True
        for li, ln in enumerate(layers):
            n = len(range(li, pins, nl)); m = usable(a, b, ln)
            if n > 0.6 * m or (n % 2 == 1 and m % 2 == 0 and n > 0):
                ok = False; break
        if ok:
            pp = dp_schema.pin_positions(dict(id='w', window_um=[a, b], layers=layers, width=pins, epoch=False), LAYER_T)
            cs = sorted(c for _, _, c in pp); mx = 0; j = 0
            for i in range(len(cs)):
                while cs[i] - cs[j] > 10.0 - 1e-6:
                    j += 1
                mx = max(mx, i - j + 1)
            if mx <= v1.FACE_LIM * max(2, nl) / 2:
                return b - lo
        b = next_edge(b + 1e-4)


def snap_win(lo, hi):
    return next_edge(lo - 1e-4), next_edge(hi - 1e-4)


v1.fit_len = fit_len_v2
v1.FACE_LIM = 54          # pins per 10-um window inside one window (adjacent windows add up to the 60 budget)
v1.WIN_PER_UM = 5.5       # window sizing density: <= 6/um in any 10-um window across window boundaries

# ---------------------------------------------------------------------------------------------------- NW layout
# (name, x0, y0, x1, y1) in lattice units; x from the die W edge, y from the die centre line (y=0) up to the N edge.
# Rows: RC centre band | R1 hc ring + SFU/SU cores | R2 SU row with the VM slice in the middle | R3 SM row |
#       R4 per-SM service row (svg, vmks, xc, cp_svg, 4 HBM pseudo-channel ctl leaves) | R5 PHY row.
SMC = [(230, 455), (455, 680), (680, 905), (905, 1130)]           # SM columns (1.944 mm)
LAYOUT = [
    # compacted (no empty strips): RC centre band 0-200; io = this quadrant's SerDes pair at the die edge;
    # C0 corner = x 970-1170 (die-level centre)
    ('io', 0, 0, 230, 200), ('rc2', 230, 0, 455, 200), ('rc3', 455, 0, 725, 200), ('rc4', 725, 0, 970, 200),
    # R1 (200-479): fabric/fault leaves, SFU core, hc ring 3x3 (93), r1e above C0
    ('r1c', 0, 200, 450, 479), ('sfuc', 450, 200, 720, 479), ('r1e', 720 + 3 * int(os.environ.get('OT_HBM_RING_X', '105')), 200, 1170, 479),
    # R2 (479-814): SU0 SU1 [VM slice] SU2 SU3
    ('su0', 0, 479, 225, 814), ('su1', 225, 479, 450, 814), ('vm', 450, 479, 720, 814),
    ('su2', 720, 479, 945, 814), ('su3', 945, 479, 1170, 814),
    # R3 (814-1619): outer strip (IDX score quarter) + 4 SM columns (each 4 stacked partitions)
    ('os1', 0, 814, 270, 1216), ('os2', 0, 1216, 270, 1619),
    # R4 (1619-1772): per-SM service partitions
    ('os3', 0, 1619, 270, 1772), ('svc0', 270, 1619, 495, 1772), ('svc1', 495, 1619, 720, 1772),
    ('svc2', 720, 1619, 945, 1772), ('svc3', 945, 1619, 1170, 1772),
    # R5 (1772-1909): PHY row (PHY_N = die x QW-492..QW+492, i.e. NW x 678..1170)
    ('r5a', 0, 1772, 339, 1909), ('r5b', 339, 1772, 678, 1909),
]
SMC = [(270, 495), (495, 720), (720, 945), (945, 1170)]
RING = 93
# P6 (COORD 10-23 18:23 (2)): q_hc2/hc7 G2 congestion is real (3 x 363-um bankq cores + 2.5-3.8 kb ft in an 803-um
# square, M1-M5 blocked over 61%).  The die height is at the 33-mm reticle, so the hc tiles grow in x only (RING_X
# lattice units; r1e above C0 gives up the width).  The ring's N/S faces and the free channel beside the cores grow.
RING_X = int(os.environ.get('OT_HBM_RING_X', '105'))
HC_X0, HC_Y0 = 720, 200
# hc ring: as-built relative order (col0: 7,0,1 bottom->top; top row 1,2,3; col2: 3,4,5; bottom 7,6,5; qhub centre)
HC_POS = {7: (0, 0), 0: (0, 1), 1: (0, 2), 2: (1, 2), 3: (2, 2), 4: (2, 1), 5: (2, 0), 6: (1, 0), 'q': (1, 1)}
for k, (i, j) in HC_POS.items():
    LAYOUT.append((f'hc{k}', HC_X0 + i * RING_X, HC_Y0 + j * RING, HC_X0 + (i + 1) * RING_X, HC_Y0 + (j + 1) * RING))
SM_ROWS = [814, 1015, 1216, 1417, 1619]
for k, (a, b) in enumerate(SMC):
    for j in range(4):
        LAYOUT.append((f'sm{k}{"abcd"[j]}', a, SM_ROWS[j], b, SM_ROWS[j + 1]))
C0_G = (QW - 200, QH - 200, QW + 200, QH + 200)       # die-level centre partition (die lattice units), 3.46 mm square
PHY_N_G = (QW - 492, 2 * QH - 137, QW + 492, 2 * QH)  # 8501.76 x 1183.68

# explicit role -> NW partition (first match wins); everything else is assigned by bit x distance
FIXED = [
    (r'^sm(\d)$', None),                                   # SM: split over sm<k>a..d (SPLIT_OF)
    (r'^su_Q(\d)$', r'su\1'),
    (r'^(vmb_Q\d|hb_vms_Q|vmdel_Q\d|vm_status_q)$', 'vm'),
    (r'^hcb_Q(\d)$', r'hc\1'), (r'^hc_Q$', 'hcq'),
    (r'^(svg|vmks|xc|cp_svg)(\d)$', r'svc\2'),
    (r'^sfucore_Q$', 'sfuc'),
    (r'^hb_idx__s_Q$', 'os2'),
    (r'^hb_coll_Q$', 'rc4'),
    (r'^(lk_|ep_|epcal_)', 'io'),
]
# P5 (COORD HBM PRICE RULING 10-23 14:44 (1)): the VM -> SM x data path is routed directly.  The x-load egress /
# broadcast-dequeue engines (xq_Q_p<k>_bd/eg; all inputs come from the VM slice: xl aq/ctl, bfq) sit IN the VM slice
# partition, which abuts the SM a quarters, instead of the svc row 7 mm away on the far side of the SM stacks.  The
# xw lanes then run VM -> sm<k>c through the SM's own a/b quarters (COORD option C inner-face capacity).
XDIRECT = os.environ.get('OT_HBM_XDIRECT', '1') == '1'
if XDIRECT:
    # p1 serves SM 2/3 (above SU2/SU3): its egress + broadcast-dequeue sit in SU2 (abuts sm2a, next to the VM), so the
    # 2 x 2079-b xw trees do not cross the full vm|su2 face; only bfq rwq + qq + lane_en (1.6 kb) do.
    FIXED.insert(0, (r'^(xq_Q_p0_(bd|eg|bfq\d)|xq_Q_p1_bfq\d|xl_Q_(ctl|aqhi|aqlo))$', 'vm'))
    FIXED.insert(0, (r'^xq_Q_p1_(bd|eg)$', 'su2'))
# P6 (COORD 10-23 18:23 (1)): the VM slice perimeter is saturated (52.5 kb on 10.45 mm, vm|su2 5.37/um -> window
# overflow).  hb_idx__op_Q narrows the die-level IDX index_rr (2056 b from C0) to block_data/head (~1.08 kb) for
# hb_idx__q_Q in the VM; placing it next to C0 moves ~1 kb of C0 -> VM traffic off the VM faces.
IDXOP_PART = os.environ.get('OT_HBM_IDXOP_PART', '')
if IDXOP_PART:
    FIXED.insert(0, (r'^hb_idx__op_Q$', IDXOP_PART))
CTL_RE = re.compile(r'^ctl_p(\d\d)$')

# ---------------------------------------------------------------------------------------------------- labels / roles
HALF = re.compile(r'^(sm|svg|vmks|xc|cp_svg)_(N|S)W(\d)$')
CTL = re.compile(r'^ctl_(N|S)W_p(\d\d)$')
QRE = re.compile(r'(?:^|_)(NW|NE|SW|SE)(?:\d|_|$)')
DIE_LEVEL = {'hb_idx__ctl', 'hb_idx__link', 'hb_idx__selector', 'hb_idx__xq_N', 'hb_idx__xq_S', 'hb_idx__xqr',
             'hb_router_ids', 'hc_eng', 'host_N', 'host_cp_ingress', 'host_cp_rxs', 'host_ep', 'host_status',
             'obs_C', 'str_C', 'su_prog', 'vm_status4', 'hb_argmax', 'hb_ckgen', 'col_idx', 'col_su', 'tkm_SW'}
IO_SPARE = {'lk_S1', 'ep_S1'}            # the 5th SerDes pair (SW only in r18h5): die-level IO, kept in IO_SW
PART_OF_HALF_PHY = {'phy_NW': 'N', 'phy_SW': 'S'}


def nlab(n):
    m = QRE.search(n)
    return m.group(1) if m else 'G'


def logical_labels(names, groups):
    """Quadrant each instance serves.  Seeds: SM-side half-named families by index, quadrant-named anchors by name;
    the rest by bit-weighted majority of its seeded neighbours (2-3 sweeps converge)."""
    adj = collections.defaultdict(collections.Counter)
    for g in groups:
        adj[g['src']][g['dst']] += g['bits']; adj[g['dst']][g['src']] += g['bits']
    lab, seed = {}, set()
    for n in names:
        m = HALF.match(n)
        if m:
            lab[n] = m.group(2) + ('W' if int(m.group(3)) < 4 else 'E'); seed.add(n); continue
        m = CTL.match(n)
        if m:
            lab[n] = m.group(1) + ('W' if int(m.group(2)) < 16 else 'E'); seed.add(n); continue
        if n in DIE_LEVEL or n in PART_OF_HALF_PHY or re.match(r'^(lk_|ep_)', n):
            lab[n] = 'G'; seed.add(n); continue
        if n == 'hb_idx__nwsh':
            lab[n] = 'NW'; seed.add(n); continue
        if re.match(r'^(hb_vms|vmb|su|hcb|hc|sfu|xq|smw|hb_coll|hcollb|hb_idx__s|hb_idx__op|wbk|pgp|sfup|sfucore|sfus|sucore)_(NW|NE|SW|SE)', n):
            lab[n] = nlab(n); seed.add(n); continue
        lab[n] = nlab(n)
    free = [n for n in names if n not in seed]
    for _ in range(20):
        ch = 0
        for n in free:
            cnt = collections.Counter()
            for m_, b in adj[n].items():
                if lab.get(m_, 'G') != 'G':
                    cnt[lab[m_]] += b
            if cnt:
                best = cnt.most_common(1)[0][0]
                if best != lab[n]:
                    lab[n] = best; ch += 1
        if not ch:
            break
    return lab


def role_of(n, lab):
    q = lab.get(n, 'G')
    m = HALF.match(n)
    if m:
        return q, f'{m.group(1)}{int(m.group(3)) % 4}'
    m = CTL.match(n)
    if m:
        return q, f'ctl_p{int(m.group(2)) % 16:02d}'
    if n in PART_OF_HALF_PHY:
        return 'G', 'phy'
    if n == 'hb_idx__nwsh':
        return q, 'idx_share_Q'
    if q == 'G':
        return 'G', n
    return q, re.sub(r'_(NW|NE|SW|SE)(?=\d|_|$)', '_Q', n)


QS = ['NW', 'NE', 'SW', 'SE']
REL = {('NW', 'NE'): 'h', ('NE', 'NW'): 'h', ('SW', 'SE'): 'h', ('SE', 'SW'): 'h',
       ('NW', 'SW'): 'v', ('SW', 'NW'): 'v', ('NE', 'SE'): 'v', ('SE', 'NE'): 'v',
       ('NW', 'SE'): 'd', ('SE', 'NW'): 'd', ('NE', 'SW'): 'd', ('SW', 'NE'): 'd'}


def partner(q, rel):
    for (a, b), r in REL.items():
        if a == q and r == rel:
            return b


# ---------------------------------------------------------------------------------------------------- model
BUSW = {}
ROLEW = {}           # (src role, canonical bus) -> source bus width cap (min(width, row sum))


def load_model(vm_ring_bits):
    insts_raw = {}
    cen = json.load(gzip.open(f'{FT}/census/hbm_census.json.gz'))
    ends = {g['src'] for g in cen['groups']} | {g['dst'] for g in cen['groups']}
    for line in open(f'{FT}/dumps/dump-hbm/blocks.tsv'):
        f = line.rstrip('\n').split('\t')
        n = f[0]
        if n not in ends and (n.startswith('hbfd_') or re.match(r'^(rf\d|rfr_|hidxr_)', n) or f[1].startswith('hbfd_')):
            continue
        insts_raw[n] = dict(name=n, master=f[1], fam=v1.fam(f[1]), w=float(f[4]), h=float(f[5]))
    lab = logical_labels(list(insts_raw), cen['groups'])
    # roles: per (quadrant, role) the real instance; canonical size = NW (else any)
    rinst = {}
    rsize = {}
    for n, i in insts_raw.items():
        q, r = role_of(n, lab)
        rinst[(q, r)] = n
        if r not in rsize or q == 'NW':
            rsize[r] = (i['w'], i['h'], i['fam'])
    # source bus widths (master pins): a source bus carries min(width, sum of its census rows) bits -- rows repeat
    # broadcast nets per destination instance / bus, and a split bus (vm_kq 562 = 2 banks x 281) needs its full width
    mw = {}
    with gzip.open(f'{FT}/dumps/dump-hbm/mpins.tsv.gz', 'rt') as fh:
        for line in fh:
            f = line.rstrip('\n').split('\t')
            mw[(f[0], f[1])] = int(f[3])
    BUSW.clear()
    tot = collections.Counter()
    for g in cen['groups']:
        tot[(g['src'], g['src_bus'], g['kind'])] += g['bits']
    for (si, sb, kd), b in tot.items():
        m = insts_raw.get(si, {}).get('master')
        w = mw.get((m, sb))
        if w is not None:
            BUSW[f'{si}.{sb}'] = w
        tot[(si, sb, kd)] = min(b, w) if w is not None else b
    # canonical source behaviour: per (src role, src bus, kind) -> max bits + union of destination (rel, role)
    canon = collections.OrderedDict()
    census_bits = collections.Counter()
    for g in cen['groups']:
        qs, rs = role_of(g['src'], lab)
        qd, rd = role_of(g['dst'], lab)
        if rs == rd and qs == qd:
            continue
        if qs == 'G':
            srel, sk = 'G', rs
        else:
            srel, sk = 'Q', rs
        if qd == 'G':
            drel = 'G'
        elif qs == 'G':
            drel = 'Q'
        else:
            drel = 'L' if qs == qd else REL[(qs, qd)]
        # cross-quadrant lanes as built (census coverage: planned >= as-built per directed partition pair): the VM and
        # COLL rings, the obs status chain and its run_done / done taps.  The canonical union makes every quadrant
        # carry both ring directions (a ring with a programmable chain end: step C).
        XQ_ROLES = r'^(hb_vms_Q|hb_coll_Q|hcollb_Q|obs_Q)$'
        if drel in ('h', 'v', 'd') and not (re.match(XQ_ROLES, rs) or re.match(XQ_ROLES, rd)):
            drel = 'L'
        # ring buses are named by geometric neighbour (v/h), not by ring direction (mirror-consistent RTL ports)
        bus = g['src_bus']
        if drel in ('h', 'v') and re.match(r'^(cw|ccw|pr_cw|pr_ccw)', bus):
            bus = re.sub(r'^(pr_)?c?cw', lambda m: (m.group(1) or '') + 'ring_' + drel, bus)
        kind = 'ctl' if g['kind'] == 'reset' else g['kind']   # hc ring reset forwarding -> in-band epoch (step C)
        key = (srel, sk, bus, kind)
        e = canon.setdefault(key, dict(bits=0, dbits={}, dsts=set(), src_q=set(), gq=collections.defaultdict(set)))
        ROLEW[(sk, bus)] = max(ROLEW.get((sk, bus), 0), tot.get((g['src'], g['src_bus'], g['kind']), 0))
        if drel == 'G':
            e['gq'][(rd, g['dst_bus'])].add(qs)
        elif srel == 'G':
            e['gq'][(rd, g['dst_bus'])].add(qd)
        bits = g['bits']
        if rs == 'hb_vms_Q' and drel in ('h', 'v'):
            bits = min(bits, vm_ring_bits)
        e['bits'] = max(e['bits'], bits)
        dk = (drel, rd, g['dst_bus'])
        e['dbits'][dk] = max(e['dbits'].get(dk, 0), bits)      # per destination (role, bus): rows are additive
        e['dsts'].add((drel, rd, g['dst_bus']))
        e['src_q'].add(qs)
        census_bits[(srel, drel)] += g['bits']
    return insts_raw, cen, lab, rinst, rsize, canon, census_bits




def synth_groups(canon, rinst, rsize, lab):
    """Census-like groups of the parameterised die: every quadrant role carries the union of its buses."""
    insts = {}
    groups = []

    def inst(q, r):
        if q == 'G':
            n = rinst.get(('G', r)) or r
        else:
            n = rinst.get((q, r)) or f'{r}@{q}'
        if n not in insts:
            w, h, fam = rsize[r]
            insts[n] = dict(name=n, fam=fam, master=fam, w=w, h=h, role=r, q=q, synthetic=n not in RINST_ALL)
        return n

    def add(g):
        g['wcap'] = ROLEW.get((sk, bus))           # source bus width cap (min(width, census row sum))
        groups.append(g)

    for (srel, sk, bus, kind), e in canon.items():
        srcs = ['G'] if srel == 'G' else QS
        for qs in srcs:
            if sk == 'phy':
                for drel, rd, dbus in sorted(e['dsts']):
                    for qd in (QS if small_rep(e, rd) else sorted(e['gq'][(rd, dbus)])):
                        add(dict(src='phy_NW' if qd in ('NW', 'NE') else 'phy_SW', src_bus=bus,
                                           dst=inst(qd, rd), dst_bus=dbus, kind=kind, bits=e['dbits'][(drel, rd, dbus)]))
                continue
            s = inst(qs, sk)
            for drel, rd, dbus in sorted(e['dsts']):
                if drel == 'G':
                    if rd == 'phy':
                        dn = 'phy_NW' if qs in ('NW', 'NE') else 'phy_SW'
                        add(dict(src=s, src_bus=bus, dst=dn, dst_bus=dbus, kind=kind, bits=e['dbits'][(drel, rd, dbus)]))
                        continue
                    if srel == 'Q' and qs not in e['gq'][(rd, dbus)] and not small_rep(e, rd):
                        continue                   # die-level data lanes stay per quadrant as built
                    dn = inst('G', rd)
                    add(dict(src=s, src_bus=bus, dst=dn, dst_bus=dbus, kind=kind, bits=e['dbits'][(drel, rd, dbus)]))
                elif drel == 'Q':          # die-level source -> every quadrant (a tree)
                    for qd in (QS if small_rep(e, rd) else sorted(e['gq'][(rd, dbus)])):
                        add(dict(src=s, src_bus=bus, dst=inst(qd, rd), dst_bus=dbus, kind=kind, bits=e['dbits'][(drel, rd, dbus)]))
                elif drel == 'L':
                    add(dict(src=s, src_bus=bus, dst=inst(qs, rd), dst_bus=dbus, kind=kind, bits=e['dbits'][(drel, rd, dbus)]))
                else:
                    add(dict(src=s, src_bus=bus, dst=inst(partner(qs, drel), rd), dst_bus=dbus, kind=kind,
                                       bits=e['dbits'][(drel, rd, dbus)]))
    # a die-level root drives each quadrant through its own registered output (4 mirror-image subtrees, not one
    # die-wide tree): keeps every quadrant's ports identical up to MX/MY
    for g in groups:
        qs_, qd_ = insts[g['src']]['q'] if g['src'] in insts else 'G', insts[g['dst']]['q'] if g['dst'] in insts else 'G'
        if qs_ == 'G' and qd_ != 'G':
            g['src_bus'] = f"{g['src_bus']}_q{qd_}"
    for pn in ('phy_NW', 'phy_SW'):
        w, h, fam = rsize['phy']
        insts[pn] = dict(name=pn, fam=fam, master=fam, w=w, h=h, role='phy', q='G', synthetic=False)
    return insts, groups


SMALL_REP = 400


def small_rep(e, rd):
    """Status / config lanes (<= 400 b) between a quadrant role and a die-level root that exist in only some quadrants
    (obs chain end, host cfg collars via hleaf_SE, smw status, run_v to router ids) are made per-quadrant: every
    quadrant has the port, the root reduces/muxes them (parameterised RTL, step C).  tkm (SW coll, 2.3 kb) and the
    IDX root's VM read path (SW slice) stay as built."""
    return e['bits'] <= SMALL_REP and rd not in ('tkm_SW',) and not rd.startswith(('ep_', 'lk_'))


IO_OF = {'NW': dict(ep='ep_N0', lk='lk_N0'), 'NE': dict(ep='ep_N2', lk='lk_N2'),
         'SW': dict(ep='ep_S0', lk='lk_S0'), 'SE': dict(ep='ep_S3', lk='lk_S3')}
IO_Q = {v[k]: q for q, v in IO_OF.items() for k in v}
IO_Q.update({'lk_S1': 'SW', 'ep_S1': 'SW'})
RINST_ALL = set()


# ---------------------------------------------------------------------------------------------------- partitions
def build_parts():
    parts = []
    for name, x0, y0, x1, y1 in LAYOUT:
        r = (x0 * G, CY + y0 * G, x1 * G, CY + y1 * G)
        kind = 'io' if name == 'io' else ('anchor' if re.match(r'^(sm\d|su\d|vm$|hc|sfuc|svc)', name) else 'fabric')
        for q, op in QOP.items():
            parts.append(dict(name=f'{q}_{name}', base=name, op=op, r=mrect(op, r), kind=kind,
                              cls=('io' if name == 'io' else 'q_' + name), anchor_nw=None))
    c0 = tuple(v * G for v in C0_G)
    parts.append(dict(name='C0', base='c0', op='I', r=c0, kind='centre', cls='c0', anchor_nw=None))
    pn = tuple(v * G for v in PHY_N_G)
    parts.append(dict(name='PHY_N', base='phy', op='I', r=pn, kind='phy', cls='phy', anchor_nw=None))
    parts.append(dict(name='PHY_S', base='phy', op='MX', r=mrect('MX', pn), kind='phy', cls='phy', anchor_nw=None))
    return parts


def overlap_check(parts):
    bad = []
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            if v1.ov(a['r'], b['r']):
                bad.append((a['name'], b['name']))
    area = sum((p['r'][2] - p['r'][0]) * (p['r'][3] - p['r'][1]) for p in parts)
    return bad, area


def assign_roles(insts, groups, parts):
    """inst -> partition.  Fixed rules first, then bit x distance descent (capacity: content <= 70% of outline)."""
    P = {p['name']: p for p in parts}
    where = {}
    cap = {p['name']: 0.70 * (p['r'][2] - p['r'][0]) * (p['r'][3] - p['r'][1]) for p in parts}
    used = collections.Counter()
    for n, i in insts.items():
        r, q = i['role'], i['q']
        tgt = None
        if q == 'G':
            if n.startswith('phy_'):
                tgt = 'PHY_N' if n == 'phy_NW' else 'PHY_S'
            elif n in IO_Q:
                tgt = f'{IO_Q[n]}_io'
            else:
                tgt = 'C0'
        else:
            m = CTL_RE.match(r)
            if m:
                tgt = f'{q}_svc{int(m.group(1)) // 4}'
            for pat, rep in FIXED:
                if tgt:
                    break
                mm = re.match(pat, r)
                if mm:
                    if rep is None:
                        tgt = 'SPLIT'
                    else:
                        tgt = f'{q}_' + mm.expand(rep)
        if tgt == 'SPLIT':
            k = int(re.match(r'^sm(\d)$', r).group(1))
            v1.SPLIT_OF[n] = [f'{q}_sm{k}{s}' for s in 'abcd']
            if v1.SM_MODE != 'off':
                # inner: COORD R6 R2-alt, SM ports at the front quarter c (reachable only laterally);
                # inner_d: R2, SM ports at the svc-facing end quarter d (+ registered relay d<->c inside the SM)
                v1.SPLIT_LAND[n] = f'{q}_sm{k}' + ('d' if v1.SM_MODE == 'inner_d' else 'c')
            where[n] = f'{q}_sm{k}a'
            continue
        if tgt:
            where[n] = tgt; used[tgt] += i['w'] * i['h']
    # free roles: NW canonical decision, mirrored to the other quadrants
    adj = collections.defaultdict(collections.Counter)
    for g in groups:
        adj[g['src']][g['dst']] += g['bits']; adj[g['dst']][g['src']] += g['bits']
    C = {p['name']: v1.centre(p['r']) for p in parts}
    nwparts = [p['name'] for p in parts if p['name'].startswith('NW_') and p['kind'] != 'io'
               and not re.match(r'^NW_(sm\d|hc)', p['name'])]
    free = sorted({i['role'] for n, i in insts.items() if n not in where and i['q'] != 'G'})
    rep = {}
    for r in free:
        rep[r] = next(n for n, i in insts.items() if i['role'] == r and i['q'] == 'NW')

    def pos(n):
        if n in v1.SPLIT_OF:
            return C[v1.SPLIT_OF[n][-1]]
        return C[where[n]] if n in where else None

    choice = {}
    for it in range(6):
        for r in sorted(free, key=lambda r: -sum(adj[rep[r]].values())):
            n = rep[r]
            if r in choice:
                used[choice[r]] -= insts[n]['w'] * insts[n]['h']
            best = None
            for pn in nwparts:
                if used[pn] + insts[n]['w'] * insts[n]['h'] > cap[pn]:
                    continue
                c = C[pn]; cost = 0.0
                for m_, b in adj[n].items():
                    pp = pos(m_)
                    if pp is None:
                        continue
                    cost += b * (abs(c[0] - pp[0]) + abs(c[1] - pp[1]))
                if best is None or cost < best[0]:
                    best = (cost, pn)
            choice[r] = best[1]
            used[best[1]] += insts[n]['w'] * insts[n]['h']
            where[n] = best[1]
    for n, i in insts.items():
        if n in where or i['q'] == 'G':
            continue
        base = choice[i['role']][3:]
        where[n] = f'{i["q"]}_{base}'
    # mirrored roles of the NW decision for the other quadrants are already set (same base)
    for n, i in insts.items():
        if i['q'] != 'G' and i['q'] != 'NW' and i['role'] in choice:
            where[n] = f'{i["q"]}_{choice[i["role"]][3:]}'
    return where, used, cap


def place_in_parts(insts, where, parts):
    """Shelf-pack contents inside their partition (NW frame, mirrored) -> instance x/y (for contents + G2 OBS)."""
    P = {p['name']: p for p in parts}
    byp = collections.defaultdict(list)
    for n, pn in where.items():
        if n in v1.SPLIT_OF:
            continue
        byp[pn].append(n)
    over = []
    for pn, lst in byp.items():
        p = P[pn]; r = p['r']
        x0, y0, x1, y1 = r
        lst.sort(key=lambda n: (-insts[n]['h'], n))
        x, y, rowh = x0 + 17.28, y0 + 17.28, 0.0
        for n in lst:
            i = insts[n]
            if x + i['w'] > x1 - 17.28 and x > x0 + 17.28 + 1e-6:
                x, y, rowh = x0 + 17.28, y + rowh + 8.64, 0.0
            i['x'], i['y'] = x, y
            x += i['w'] + 8.64; rowh = max(rowh, i['h'])
        if y + rowh > y1 + 1e-6:
            over.append((pn, round((y + rowh - y1)), len(lst)))
    for n, i in insts.items():
        if n in v1.SPLIT_OF:
            ps = [P[s]['r'] for s in v1.SPLIT_OF[n]]
            i['x'], i['y'] = ps[0][0] + 2.16, min(r[1] for r in ps)
        i.setdefault('x', 0.0); i.setdefault('y', 0.0)
        i['cx'], i['cy'] = i['x'] + i['w'] / 2, i['y'] + i['h'] / 2
    return over


# ---------------------------------------------------------------------------------------------------- census report
def xq_report(groups, where, parts):
    """Lane-level cross-quadrant bits of the plan (unique source buses; broadcast counted once per quadrant)."""
    P = {p['name']: p for p in parts}

    def q(pn):
        m = re.match(r'^(NW|NE|SW|SE)_', pn)
        return m.group(1) if m else 'C'
    seen = {}
    for g in groups:
        s, t = where.get(g['src']), where.get(g['dst'])
        if s is None or t is None:
            continue
        qa, qb = q(s), q(t)
        cls = 'local' if qa == qb and qa != 'C' else ('xq' if 'C' not in (qa, qb) else 'centre')
        if s.startswith('PHY') or t.startswith('PHY'):
            cls = 'phy (own HBM channels)'
        elif qa == 'C' and qb == 'C':
            cls = 'centre_internal'
        k = (g['src'], g['src_bus'], qb, cls)
        seen[k] = max(seen.get(k, 0), g['bits'])
    out = collections.Counter()
    for (s, b, qb, cls), bits in seen.items():
        out[cls] += bits
    return dict(out)


# ---------------------------------------------------------------------------------------------------- main
SMQ_WHERE = {}
SM_SPLIT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sm_split', 'sm_split.json')


GROUPS_FOR_XLAND = []


def sm_internal_groups(where):
    """SM-internal quarter-to-quarter traffic (sm_split/sm_split.json crossings, HBM-P3-SM) as census rows between
    pseudo-instances smq_<Q><k><quarter> (one per SM quarter partition).  COORD R6 R2-alt: the die lanes into the SM
    land on c directly, so the R2 rows (SM inputs relayed d -> c) are dropped; R1/R3/R4 rows stay (registered by the
    Step C RTL changes).  Bits are summed per direction."""
    sp = json.load(open(SM_SPLIT_JSON))
    per = collections.Counter()
    for x in sp['crossings']:
        if str(x.get('rtl_change') or '').startswith('R2') and v1.SM_MODE != 'inner_d':
            continue
        a_, b_ = x['dir'].split('->')
        per[(a_, b_)] += x['bits']
    rows = []
    xa = collections.Counter()       # P4 XLAND=a: VM-side SM lane bits that land on a and are relayed to/from c
    if v1.XLAND in ('a', 'xw'):
        for g in GROUPS_FOR_XLAND:
            for sm, peer, d, bus in ((g['dst'], g['src'], 'in', g['dst_bus']), (g['src'], g['dst'], 'out', g['src_bus'])):
                if sm in v1.SPLIT_OF and v1.xland_a(where.get(peer), bus):
                    xa[(sm, d)] = max(xa[(sm, d)], 0) + g['bits']
    for n, subs in sorted(v1.SPLIT_OF.items()):
        q, k = re.match(r'^(NW|NE|SW|SE)_sm(\d)a$', subs[0]).groups()
        pn = collections.Counter(per)
        if xa:
            pn[('a', 'b')] += xa[(n, 'in')]; pn[('b', 'c')] += xa[(n, 'in')]
            pn[('c', 'b')] += xa[(n, 'out')]; pn[('b', 'a')] += xa[(n, 'out')]
        for (a_, b_), bits in sorted(pn.items()):
            sn, dn = f'smq_{q}{k}{a_}', f'smq_{q}{k}{b_}'
            SMQ_WHERE[sn] = f'{q}_sm{k}{a_}'; SMQ_WHERE[dn] = f'{q}_sm{k}{b_}'
            rows.append(dict(src=sn, src_bus=f'x_{a_}{b_}', dst=dn, dst_bus=f'x_{a_}{b_}', kind='data', bits=bits,
                             wcap=bits))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument('--vm-ring-bits', type=int, default=2224,
                    help='VM slice ring link width per direction (r18h5 2224 = one 8-bank line per beat)')
    ap.add_argument('--geom-only', action='store_true')
    a = ap.parse_args()
    insts_raw, cen, lab, rinst, rsize, canon, census_bits = load_model(a.vm_ring_bits)
    RINST_ALL.update(insts_raw)
    insts, groups = synth_groups(canon, rinst, rsize, lab)
    parts = build_parts()
    bad, area = overlap_check(parts)
    print('partitions', len(parts), 'overlaps', bad[:5], 'area', round(area / 1e6, 2), 'die', round(W * H / 1e6, 2))
    if bad:
        raise SystemExit('overlap')
    where, used, cap = assign_roles(insts, groups, parts)
    over = place_in_parts(insts, where, parts)
    fill = sorted(((used[p] / cap[p] * 0.7, p) for p in used if p.startswith('NW_') or p in ('C0',)), reverse=True)
    print('fill (content/outline) top', [(p, round(f, 2)) for f, p in fill[:8]], 'shelf overflow', over[:6])
    xr = xq_report(groups, where, parts)
    print('plan lane bits', xr)
    os.makedirs(a.out, exist_ok=True)
    v1.render(parts, insts, where, os.path.join(a.out, 'plan_v2_geom.png'), title='HBM d4g plan v2 (geometry)')
    json.dump(dict(where=where, xq=xr, census_bits={f'{k[0]}>{k[1]}': v for k, v in census_bits.items()},
                   synthetic=sorted(n for n, i in insts.items() if i.get('synthetic'))),
              open(os.path.join(a.out, 'v2_assign.json'), 'w'), indent=1)
    if a.geom_only:
        return
    GROUPS_FOR_XLAND[:] = groups
    smrows = sm_internal_groups(where) if v1.SM_MODE != 'off' else []   # COORD R6 (1): SM-internal quarter lanes
    groups = groups + smrows
    cen2 = dict(groups=groups)
    segs, adj = v1.build_graph(parts)
    for s_ in segs.values():
        s_['cap'] *= float(os.environ.get('OT_HBM_LONG_CAP', '0.86')) if s_['len'] >= 1000 else float(os.environ.get('OT_HBM_SHORT_CAP', '0.65'))   # window parity / 10-um margins cost up to ~15% of the face over the routing estimate (P5: more on sub-mm faces, the 803-um hc ring)
    P = {p['name']: p for p in parts}
    B = v1.bundles(cen2, {**where, **SMQ_WHERE}, P)
    orb = v1.orbits(B, P)
    widened = 0
    for mem in orb:                # identical quadrants: every image of a bundle carries the widest member's bits
        mx = max(B[k]['bits'] for k in mem.values())
        for k in mem.values():
            widened += mx - B[k]['bits']; B[k]['bits'] = mx
    print('orbit width equalisation: +', widened, 'bits')
    print('segments', len(segs), 'bundles', len(B), 'orbits', len(orb), 'asym orbits', sum(1 for o in orb if len(o) == 1))
    paths, load = v1.route_all(parts, segs, adj, B, orb)
    em = v1.emit(parts, segs, B, orb, paths, insts, {**where, **SMQ_WHERE}, cen2, a.out)
    for pt in em['ports']:
        lo, hi = pt['window_um']
        a_, b_ = snap_win(lo, hi)
        pt['window_um'] = [round(a_, 3), round(b_, 3)]
    types, plist, tgroups = v1.types_and_plan(parts, insts, where, em)
    print('ports', len(em['ports']), 'lanes', len(em['lanes']), 'types', len(types), 'warn', dict(em['warn']),
          'hop_max', round(em['hop_max']))
    LAYERS = None
    plan = {
        'schema': 'opentallas.die_plan.v1',
        'note': ('HBM d4g die plan v2 (PLAN-HBMv2 2026-10-23), QUADRANT-LOCAL (COORD ruling 10-23 06:26; lanes/HBM-QLOCAL.md). '
                 'Generated by gen_plan_v2.py from the r18h5 FT-TOOL census: logical quadrants, one canonical quadrant '
                 '(union of the four RTL variants = the parameterised RTL of HBM-QLOCAL step C), top-down floorplan, '
                 'VM slice = one partition between SU0/1 and SU2/3, die-level roots in C0, cross-quadrant = VM ring '
                 f'({a.vm_ring_bits} b/dir/link) + COLL rings only.'),
        'die': dict(name='hbm_d4g', label='HBM d4g die plan v2 (quadrant-local)', tech='asap7',
                    outline_um=[round(W, 3), round(H, 3)], period_ps=833, reach_um=v1.REACH, rep_um=450.0, grid_um=G,
                    layer_budget=dict(partition_signal_max='M7', die_layers=['M8', 'M9'],
                                      die_use=['clock_spine', 'pg', 'ft_reserved'], cut_avail={'M8': 0.6, 'M9': 0.6}),
                    pg=dict(partition_pg_max='M7', grid=[
                        dict(layer='M8', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS']),
                        dict(layer='M9', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS'])])),
        'partition_types': types,
        'partitions': plist,
        'ports': em['ports'],
        'lanes': em['lanes'],
        'clock': dict(insertion_ps=250.0, insertion_tol_ps=40.0, neighbour_skew_ps=80.0, face_xing='budgeted',
                      spine=dict(layers=['M8', 'M9'], root_um=[round(CX, 3), round(CY, 3)], topology='htree')),
        'reset': dict(sync_stages=2, data_reset=False, epoch_bit=True, release='counted'),
        'latency': dict(lanes=em['lat']),
        'budgets': dict(face_pins_per_um=6.0, face_pin_layers=2, face_window_um=10.0, pin_track_max=0.6,
                        cut_ratio_max=0.6, cut_step_um=250.0, pin_reg_p90_um=30.0),
    }
    # G0 census coverage (PLAN-TOOL census_cov.py): as-built r18h5 rows (slim TSV) + the instance map of this plan
    os.makedirs(os.path.join(a.out, 'census'), exist_ok=True)
    with gzip.open(os.path.join(a.out, 'census', 'hbm_r18h5_rows.tsv.gz'), 'wt') as fh:
        fh.write('src\tsrc_bus\tdst\tdst_bus\tkind\tbits\n')
        for g in cen['groups'] + smrows:
            fh.write(f"{g['src']}\t{g['src_bus']}\t{g['dst']}\t{g['dst_bus']}\t{g['kind']}\t{g['bits']}\n")
    smg = {}
    parts_map = {}
    for n, pn in where.items():
        if '@' in n:
            continue                                   # synthetic replicas (step C RTL) have no as-built rows
        if n in v1.SPLIT_OF:                           # one SM macro over its 4 stacked partitions
            gname = re.sub(r'[abcd]$', '', v1.SPLIT_OF[n][0])
            smg[gname] = list(v1.SPLIT_OF[n]); parts_map[n] = gname
        else:
            parts_map[n] = pn
    parts_map.update(SMQ_WHERE)                        # SM-internal quarter pseudo-instances (sm_split)
    json.dump(BUSW, gzip.open(os.path.join(a.out, 'census', 'bus_widths.json.gz'), 'wt'))
    json.dump(dict(parts=parts_map, groups=smg, rules=[], collapse=[], bus_widths='census/bus_widths.json.gz',
                   exempt=[dict(match='^clock$', kind='clock', replaced_by='die clock spine + per-partition tap',
                                reason='clock nets are not plan lanes')]),
              open(os.path.join(a.out, 'census', 'map_v2.json'), 'w'), indent=0)
    plan['census'] = [dict(rows='census/hbm_r18h5_rows.tsv.gz', map='census/map_v2.json',
                           note='r18h5 FT census (hbm_census.json.gz, 35075 groups); SM = group of 4 stacked partitions')]
    # COORD option (A): types with a 3-layer (M7/M5 + die M9) N/S face list it in face_layers (both ends must)
    ptype = {p['name']: p['type'] for p in plist}
    porient = {p['name']: p.get('orient', 'R0') for p in plist}
    for pt in em['ports']:
        if len(pt['layers']) > 2:
            for e in ('src', 'dst'):
                fl = types[ptype[pt[e]['part']]].setdefault('face_layers', {})
                if pt['face'] in ('N', 'S'):
                    for f_ in ('N', 'S'):
                        fl[f_] = ['M7', 'M5', 'M9']
                else:
                    # P6 VM3: E/W face on die M8; the face of this end in its TYPE frame (MY / R180 swap E and W)
                    f_ = pt['face'] if e == 'src' else {'E': 'W', 'W': 'E'}[pt['face']]
                    if porient[pt[e]['part']] in ('MY', 'R180'):
                        f_ = {'E': 'W', 'W': 'E'}[f_]
                    fl[f_] = ['M6', 'M4', 'M8']
    __import__('taps_cores_v2').apply(plan, a.out, where)   # HBM-P3-TAPS post-pass: hard cores, cells, clock taps
    json.dump(plan, open(os.path.join(a.out, 'die_plan.json'), 'w'), indent=None, separators=(',', ':'))
    mem = {}
    for oi, m in enumerate(orb):
        for gb, k in m.items():
            b = B[k]
            mem[f'L{oi}{"abcd"[gb]}'] = dict(src=b['src'], dsts=b['dsts'], kind=b['kind'], bits=b['bits'],
                                            nets=[f'{x}.{y}' for x, y in b['nets']])
    json.dump(mem, gzip.open(os.path.join(a.out, 'lane_members.json.gz'), 'wt'))
    json.dump(dict(where=where, xq=xr, warn=dict(em['warn']), types=len(types), partitions=len(plist),
                   census_bits={f'{k[0]}>{k[1]}': v for k, v in census_bits.items()},
                   synthetic=sorted(n for n, i in insts.items() if i.get('synthetic'))),
              open(os.path.join(a.out, 'v2_assign.json'), 'w'), indent=1)
    print('wrote die_plan.json', os.path.getsize(os.path.join(a.out, 'die_plan.json')) // 1024, 'KB')


if __name__ == '__main__':
    main()
