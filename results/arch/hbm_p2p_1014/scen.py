"""P2P study scenarios on the v13 window model (pickle from tools/hbm_r25gq_windows.py --dump-model).
A changed logical bus is replaced by one direct hop per (source, sink) between the nearest points of the two boxes
(L-shape demand); untouched buses keep their v13 pin-to-pin relay hops."""
import pickle, re, sys, json, collections, copy, math, os, importlib.util
# P2P_TOOLS: a tools/ dir holding hbm_r25gq_windows.py + hbm_r25gq_cuts.py (branch claude/hbm-native-die-1013 31a02920b)
# P2P_MODEL: the v13 window-model pickle (hbm_r25gq_windows.py --ds-var r25gqn_v13 --dump-model)
TOOLS = os.environ.get('P2P_TOOLS', '/tmp/claude-1000/p2p14/tools')
def _load(name, fn):
    sp = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, fn)); mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod); return mod
W = _load('windows', 'hbm_r25gq_windows.py'); CU = _load('cuts', 'hbm_r25gq_cuts.py')
m0 = pickle.load(open(os.environ.get('P2P_MODEL', '/tmp/claude-1000/p2p14/v13.pkl'), 'rb'))
OUT = os.environ.get('P2P_OUT', '/tmp/claude-1000/p2p14')
def logical(bid): return re.sub(r'(_\d+)?(_e)?(_[twqr]\d+(n\d+)?)*$', '', bid)
# logical bus graph from m['buses'] (first end = driver)
G = collections.defaultdict(lambda: dict(cls=None, bits=0, edges=[]))
for bid, cls, bits, eps in m0['buses']:
    if cls in W.SKIP_CLS: continue
    g = G[logical(bid)]; g['cls'] = cls; g['bits'] = max(g['bits'], bits)
    if len(eps) >= 2:
        for e in eps[1:]: g['edges'].append((eps[0][0], e[0]))
def ends(lg, I):
    g = G[lg]; src = {a for a, b in g['edges']}; dst = {b for a, b in g['edges']}
    S = [a for a in src if a not in dst or I.get(a, ('', 'x'))[1] != 'waypoint']
    T = [b for b in dst if b not in src or I.get(b, ('', 'x'))[1] != 'waypoint']
    return S, T
def near(a, b):
    ca, cb = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2), ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    cl = lambda bx, q: (min(max(q[0], bx[0]), bx[2]), min(max(q[1], bx[1]), bx[3]))
    p, q = cl(a, cb), cl(b, ca)
    return cl(a, q), cl(b, p)
def box(I, n): v = I[n]; return (v[2], v[3], v[2] + v[4], v[3] + v[5])

def scenario(name):
    I = dict(m0['insts']); segs = list(m0['segs'])
    drop = set(); add = []          # logical buses to drop; new (bus, cls, bits, a_inst, b_inst)
    moved = set()
    def mv(n, x, y, w=None, h=None):
        v = I[n]; I[n] = (v[0], v[1], x, y, w or v[4], h or v[5], v[6]); moved.add(n)
    def new(n, master, x, y, w, h, kind='hub'):
        I[n] = (master, kind, x, y, w, h, 'R0'); moved.add(n)
    def rew(lg, a, b, bits=None, nm=None):
        drop.add(lg); add.append((nm or lg, G[lg]['cls'] or 'hub', bits or G[lg]['bits'], a, b))
    F = set(name.split('+'))
    if 'VMX' in F:      # VM8 quarters as independent x roots fed from their local REPL slice: no cross-quarter buses
        for lg in list(G):
            if lg.startswith('hb_vm_x_'): drop.add(lg)
    if 'VMC' in F:      # VM8 union (closed quarters, cross buses kept) into the spine void at the die centre
        dy_ = 12490.0 - m0['insts']['hb_vm_sw'][3]
        for q_ in ('sw', 'se', 'nw', 'ne'):
            v_ = m0['insts'][f'hb_vm_{q_}']; mv(f'hb_vm_{q_}', v_[2], v_[3] + dy_)
        v_ = m0['insts']['hb_cmdproc']; mv('hb_cmdproc', v_[2], 14510.0)
    if 'VM' in F:
        mv('hb_vm_sw', 13300.0, 7300.0); mv('hb_vm_se', 17760.0, 8000.0, 1000.0, 700.0)
        mv('hb_vm_nw', 13450.0, 16950.0); mv('hb_vm_ne', 17800.0, 16950.0)
    if 'COLL' in F:
        C = dict(SW=(10600.0, 6950.0), SE=(19000.0, 6950.0), NW=(12700.0, 18050.0), NE=(17400.0, 18050.0))
        T = dict(SW=(9600.0, 7950.0), SE=(19000.0, 5900.0), NW=(11600.0, 18050.0), NE=(18450.0, 18050.0))
        for q in C:
            new(f'coll_{q}', 'hfd_coll_q', *C[q], 1000.0, 1000.0)
            new(f'tkm_{q}', 'hfd_coll_tkm_q', *T[q], 1000.0, 1000.0)
        LQ = dict(S0='SW', S1='SW', S2='SW', S3='SE', S4='SE', N0='NW', N1='NW', N2='NE', N3='NE')
        for l, q in LQ.items(): rew(f'lk_lk_{l}', f'coll_{q}', f'ep_{l}')
        for q in C:
            rew(f'hb_su_{q}_coll', f'hb_su_{q}', f'coll_{q}'); rew(f'hb_coll_su_{q}', f'coll_{q}', f'hb_su_{q}')
            add.append((f'vcb_coll_{q}', 'hub', 1088, f'coll_{q}', f'hb_vms_{q}'))
            add.append((f'tkm_del_{q}', 'hub', 545, f'coll_{q}', f'tkm_{q}'))
            add.append((f'tkm_w_{q}', 'hub', 137, f'tkm_{q}', f'coll_{q}'))
        for lg in ('vcb_coll_SW', 'vcb_coll_SE', 'vcb_SE_NE', 'vcb_SW_NW', 'vcb_SE_NE_c', 'vcb_SW_NW_c', 'vcb_coll_SW_c',
                   'vcb_coll_SE_c', 'tkm_del', 'tkm_w', 'tkm_cfg', 'tkm_st'):
            drop.add(lg)
        # COLL peer ring (small data: control, sequence, top-k / argmax merge streams): 256 b each way
        for a, b in (('SW', 'SE'), ('SW', 'NW'), ('SE', 'NE'), ('NW', 'NE')):
            add += [(f'cring_{a}_{b}', 'hub', 256, f'coll_{a}', f'coll_{b}'), (f'cring_{b}_{a}', 'hub', 256, f'coll_{b}', f'coll_{a}')]
        # any other bus that touched hb_coll -> NW quadrant COLL (control / mtp / host paths)
        for lg, g in G.items():
            if lg in drop: continue
            if any('hb_coll' in (a, b) for a, b in g['edges']):
                S_, T_ = ends(lg, m0['insts'])
                for s_ in S_:
                    for t_ in T_:
                        add.append((lg, g['cls'], g['bits'], 'coll_NW' if s_ == 'hb_coll' else s_, 'coll_NW' if t_ == 'hb_coll' else t_))
                drop.add(lg)
        del I['hb_coll']; del I['hb_tkm']
    if 'CP' in F:
        D = dict(SW=(13400.0, 10750.0), SE=(17770.0, 10750.0), NW=(13400.0, 14450.0), NE=(17770.0, 14450.0))
        for q in D:
            new(f'cp_{q}', 'hfd_cmdproc_q', *D[q], 950.0, 400.0)
            add.append((f'cp_rec_{q}', 'control', 256, 'hb_cmdproc', f'cp_{q}'))
        for lg, g in list(G.items()):
            if lg in drop: continue
            if not re.match(r'^(hgi_su_cmd|hgi_hc_cmd|ct_|vrc_cp_|vrc_att_)', lg): continue
            S_, T_ = ends(lg, m0['insts'])
            qq = re.search(r'_(SW|SE|NW|NE)$', lg)
            if lg.startswith('hgi_su_cmd') or lg.startswith('hgi_hc_cmd'): q = 'SW'
            elif lg.startswith('vrc_cp'): q = 'NW'
            elif lg.startswith('vrc_att'): q = 'NE'
            else: q = qq.group(1) if qq else 'SW'
            for s_ in S_:
                for t_ in T_:
                    add.append((lg, g['cls'], g['bits'], f'cp_{q}' if s_ == 'hb_cmdproc' else s_, f'cp_{q}' if t_ == 'hb_cmdproc' else t_))
            drop.add(lg)
    # buses touching a moved (relocated) instance: direct re-hop
    for lg, g in G.items():
        if lg in drop: continue
        if any(a in moved or b in moved for a, b in g['edges']):
            S_, T_ = ends(lg, m0['insts'])
            for s_ in S_:
                for t_ in T_:
                    if s_ in I and t_ in I: add.append((lg, g['cls'], g['bits'], s_, t_))
            drop.add(lg)
    segs = [s for s in segs if logical(s[0]) not in drop]
    for bid, cls, bits, a, b in add:
        if a not in I or b not in I: continue
        p, q = near(box(I, a), box(I, b)); segs.append((bid, cls, bits, p[0], p[1], q[0], q[1]))
    # overlap check of the new / moved boxes against every block > 4e4 um2
    ov = []
    for n in moved:
        a = box(I, n)
        for k, v in I.items():
            if k == n or v[1] == 'waypoint' or v[4] * v[5] <= 4e4: continue
            b = (v[2], v[3], v[2] + v[4], v[3] + v[5])
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]: ov.append((n, k))
    return I, segs, ov, add

out = {}
for sc in sys.argv[1:]:
    I, segs, ov, add = scenario(sc)
    I2, segs = W.light(dict(insts=I, segs=segs))
    res, (dH, dV, cH, cV, opn) = W.run(I2, segs)
    hub = W.by_family(segs, (11000, 7000, 21500, 20000), *dH.shape)
    hot = W.by_family(segs, (12000, 14000, 15000, 17000), *dH.shape)
    # bits crossing the two centre lines inside the hub band (cross-quadrant traffic), counted on hop segments
    xc = sum(s[2] for s in segs if (min(s[3], s[5]) < 16492 < max(s[3], s[5])) and 7000 < (s[4] + s[6]) / 2 < 20000)
    yc = sum(s[2] for s in segs if (min(s[4], s[6]) < 12990 < max(s[4], s[6])) and 11000 < (s[3] + s[5]) / 2 < 21500)
    blocks = [b for b in I2.values() if b[4] != 'waypoint' and (b[2] - b[0]) * (b[3] - b[1]) > 4e4]
    capx, _ = CU.capacity('x', 7000, 20000, 16492, blocks); capy, _ = CU.capacity('y', 11000, 21500, 12990, blocks)
    capxf, _ = CU.capacity('x', 0, 25979, 16492, blocks); capyf, _ = CU.capacity('y', 0, 32984, 12990, blocks)
    xf = sum(s[2] for s in segs if (min(s[3], s[5]) < 16492 < max(s[3], s[5])))
    yf = sum(s[2] for s in segs if (min(s[4], s[6]) < 12990 < max(s[4], s[6])))
    HUBR = (11000, 7000, 21500, 20000)
    hubwin = {}
    for sz in W.SIZES:
        ww = W.windows(dH, dV, cH, cV, sz)
        ov_ = [x for x in ww if x[0] > W.LIMIT[sz]]
        inh = [x for x in ov_ if HUBR[0] <= x[2] + sz / 2 <= HUBR[2] and HUBR[1] <= x[3] + sz / 2 <= HUBR[3]]
        wh = max((x[0] for x in ww if HUBR[0] <= x[2] + sz / 2 <= HUBR[2] and HUBR[1] <= x[3] + sz / 2 <= HUBR[3]), default=0)
        hubwin[int(sz)] = dict(over_all=len(ov_), over_hub=len(inh), worst_hub=round(wh, 3))
    cutsum = dict(x_centre_hub=dict(bits=xc, tracks=round(capx), util=round(xc / capx, 3)), y_centre_hub=dict(bits=yc, tracks=round(capy), util=round(yc / capy, 3)),
                  x_centre_full=dict(bits=xf, util=round(xf / capxf, 3)), y_centre_full=dict(bits=yf, util=round(yf / capyf, 3)))
    print(sc, 'HUBWIN', json.dumps(hubwin), 'CUTS', json.dumps(cutsum))
    out[sc] = dict(hubwin=hubwin, cuts=cutsum, verdict=res['verdict'], **{k: dict(over=v['over'], worst=v['worst'], top=v['top'][0]) for k, v in res['sizes'].items()},
                   hub_bit_mm=round(sum(hub.values()) / 1000), hot_bit_mm=round(sum(hot.values()) / 1000), x_centre_hub_bits=xc,
                   y_centre_hub_bits=yc, overlaps=ov, added=len(add))
    print(sc, json.dumps({k: (v if k not in ('500', '1000', '2000') else dict(over=v['over'], worst=v['worst'], at=(v['top']['x_um'], v['top']['y_um'], v['top']['dir']), fam=v['top']['top'][:3])) for k, v in out[sc].items()}))
json.dump(out, open(os.path.join(OUT, 'scen_' + '_'.join(sys.argv[1:]) + '.json'), 'w'), indent=1, default=str)
