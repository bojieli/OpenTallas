#!/usr/bin/env python3
"""HBM-MU-QUAD: unified SU/MU hub plan = Codex 3c3dae6bb native MU buddy candidate (H4320, bound 3957.12) with the
GEOM-REVIEW-15 quad fixes, repacked around 2 FIXED replicated quad tiles per hub (q0 = E end of segment 0, q1 = W end of
segment 1, n4 between them), NE = die mirror of NW (same local layout; NE_hub is MY at die level, local E faces the root).
Plan arithmetic only (no P&R). UNCHECKED unless CHECKED.

Structural SU fix (root cause of the +19-register SU bank legs in U0): Codex's MU grouping moved banks Q0-Q3 to segment 0
AFTER plan_quadrants had bound each bank<->service station to the service copy of the bank's OLD segment (__q1), so
Q0/Q1/Q2 talked to hb_vms/xl_ctl/smw/dbk/calendar __q1 across the hub (6.7 mm, serialised k3).  Here every replicated
service end is rebound to the copy of its partner's segment, so each quad's 4 banks are served by its own service column.

Usage: hbm_mu_quad_pack.py ROOT HUB(q_hub_nw|q_hub_ne) OUTDIR [--bound 3957.12] [--kmin 1]
"""
import sys, json, copy, re, math, pathlib, collections
root = pathlib.Path(sys.argv[1]); tn = sys.argv[2]; out = pathlib.Path(sys.argv[3])
argv = sys.argv[:]
bound = float(argv[argv.index('--bound') + 1]) if '--bound' in argv else 3957.12
kmin = int(argv[argv.index('--kmin') + 1]) if '--kmin' in argv else 1
H = 4320.0
def opt(n, d): return argv[argv.index(n) + 1] if n in argv else d
QY = opt('--qy', 'mid'); Q1POS = opt('--q1pos', 'W'); DES = opt('--desired', 'aff')
CODEX = {}
if DES != 'aff':
    for h in json.load(open(DES))['hard_cores']:
        CODEX[h['inst']] = (h['origin_um'][0] + h['outline_um'][0] / 2, h['origin_um'][1] + h['outline_um'][1] / 2)
    # HBM-MU-QUAD-2 --alias NEW=OLD[,..]: desired centre of NEW (e.g. NE-only coll body_n2) = centre of OLD in the desired file
    for x in opt('--alias', '').split(','):
        if x:
            nn, oo = x.split('=')
            for q in ('__q0', '__q1'):
                if oo + q in CODEX: CODEX[nn + q] = CODEX[oo + q]
out.mkdir(parents=True, exist_ok=True)
wrapper = (root / 'mu_r13_probe.py').read_text()
setup = wrapper[:wrapper.index("src=(root/")]
ns = {'__name__': 'mu_setup'}; sys.argv = [argv[0], str(root), str(H), tn]
exec(compile(setup, 'probe_setup', 'exec'), ns)
R11, R9, M, P = ns['R11'], ns['R9'], ns['M'], ns['P']
HR = R9.HR
original = ns['original']
claude = (root / 'mu_probe_claude.py').read_text()
cn = {'__name__': 'mu_patch'}
sys.argv = ['claude_probe', str(root / 'tools'), str(root / 'plan'), 'all', str(H), str(bound)]
exec(compile(claude[:claude.index('_orig = R11.prepare')], 'claude_unit_patch', 'exec'), cn)
G = 8.64
def r3(v): return round(v + 0.0, 3)
def sn(v, q=G): return round(round(v / q) * q, 3)

# ------------------------------------------------------------------ quad tile (GEOM-REVIEW-15 fixes applied)
VM = (270.0, 403.92); FU = (345.6, 518.4); TN = (172.8, 172.8)
OS = 43.2      # (e) outer column street beside each FUSED column: vertical n1->n2 tree legs + their stations
S_ = 43.2      # inner streets between the bank columns and the service column
bw = FU[0] + G + VM[0]; bh = max(VM[1], FU[1]); st1 = TN[1] + 2 * G
cellh = 2 * bh + st1; mid = TN[1] + 2 * G
colw = 881.28
xW = OS; xC = xW + bw + S_; xE = xC + colw + S_; QW = r3(xE + bw + OS)
QH = r3(2 * cellh + mid)                               # 2643.84 (hb_vms no longer needs an upper half)
rows = [0.0, cellh + mid]
def quad_members(dims):
    Mm = {}
    def put(n, x, y, wh, o='R0', k=''): Mm[n] = (r3(x), r3(y), wh[0], wh[1], o, k)
    for k, (side, ri) in enumerate([('W', 0), ('W', 1), ('E', 0), ('E', 1)]):
        y0 = rows[ri]
        for j in (0, 1):
            yb = y0 + (0 if j == 0 else bh + st1)
            if side == 'W':
                put(f'fu{k}_{j}', xW, yb, FU, 'MY', 'fused'); put(f'vm{k}_{j}', xW + FU[0] + G, yb, VM, 'MY', 'vm')
            else:
                put(f'vm{k}_{j}', xE, yb, VM, 'R0', 'vm'); put(f'fu{k}_{j}', xE + VM[0] + G, yb, FU, 'R0', 'fused')
        fx = (xW if side == 'W' else xE + VM[0] + G) + (FU[0] - TN[0]) / 2
        put(f'n1_{k}', fx, y0 + bh + G, TN, 'R0', 'tnode')
    n2y = cellh + G
    put('n2L', xW + (FU[0] - TN[0]) / 2, n2y, TN, 'R0', 'tnode')
    put('n2R', xE + VM[0] + G + (FU[0] - TN[0]) / 2, n2y, TN, 'R0', 'tnode')
    # (c) hb_vms on the middle street, centred on the n2 row; services split below (xl_ctl/smw/dbk/cal) and above (vmdel x4)
    hv = dims['hb_vms']; yc = n2y + TN[1] / 2
    put('hb_vms', xC + (colw - hv[0]) / 2, sn(yc - hv[1] / 2), hv, 'R0', 'svc')
    put('xl_ctl', xC, G, dims['xl_ctl'], 'R0', 'svc'); put('smw', xC + 388.8 + G, G, dims['smw'], 'R0', 'svc')
    put('dbk', xC + 388.8 + G + 142.56 + G, G, dims['dbk'], 'R0', 'svc')
    put('cal', xC + 388.8 + G + 142.56 + G, G + 240.84 + G, dims['cal'], 'R0', 'svc')
    hv_top = Mm['hb_vms'][1] + hv[1]
    for k in range(4):
        # HBM-MU-QUAD-2: S_ street (not the 8.64 abut gap) between hb_vms N face and the vmdel block, so hb_vms N-face
        # pins escape (b3_xq -> vmb_Q3 was the one failed station route, enclosed under vmdel)
        put(f'vmdel{k}', xC + (colw - 2 * 257.04 - G) / 2 + (k % 2) * (257.04 + G), sn(hv_top + S_ + (k // 2) * (108 + G), G),
            dims['vmdel'], 'R0', 'svc')
    # n3 at the top of the service column (equal legs n2L/n2R -> n3 by symmetry); root leg leaves on the N street
    put('n3', xC + (colw - TN[0]) / 2, QH - TN[1], TN, 'R0', 'tnode')
    assert Mm['vmdel3'][1] + Mm['vmdel3'][3] + S_ <= Mm['n3'][1] + 1e-6, 'vmdel block hits n3'
    return Mm

C0 = json.load(open(root / 'plan' / 'die_plan.json'))
# ------------------------------------------------------------------ unit patch + n4 (GEOM-15 (b)/(d))
_orig_prep = R11.prepare
ADD = {}
def prepare(Pp, part, tn_, cap, spread):
    t, W, H0, t1, lrep = _orig_prep(Pp, part, tn_, cap, spread)
    t1 = copy.deepcopy(t1); t1['_mu_hub_type'] = tn_
    ADD[tn_] = cn['patch'](t1)
    hc = t1['hard_cores']; st = t1['internal_stations']
    by = {h['inst']: h for h in hc}
    # replace the two per-quadrant root legs by n3_q0/n3_q1 -> n4 (one node between the quads) -> root (hub local E face)
    st[:] = [s for s in st if not str(s.get('conn', '')).startswith('mu_tree_root:')]
    n4 = dict(inst='u_mu_fused_n4', module='ot_hnx_fused_tnode', origin_um=[bound, H / 2], outline_um=list(TN),
              track_offset_um=[0, 0], pins_file=None, note='HBM-MU-QUAD n4: q0/q1 pair node in the hub (GEOM-REVIEW-15 (b))')
    hc.append(n4); by[n4['inst']] = n4
    def Np(h, fx):   # N-face pin, fx = fraction of width
        return [r3(h['origin_um'][0] + fx * h['outline_um'][0]), r3(h['origin_um'][1] + h['outline_um'][1])]
    def Sp(h, fx):   # S-face pin (HBM-MU-QUAD-2: n4 pins face the N street the legs run in)
        return [r3(h['origin_um'][0] + fx * h['outline_um'][0]), r3(h['origin_um'][1])]
    for q in (0, 1):
        n3 = by[f'u_mu_fused_n3_q{q}']; slot = 'ua' if q == 0 else 'ub'; da = 'da' if q == 0 else 'db'
        st.append(dict(conn=f'mu_tree:{n3["inst"]}.uo|u_mu_fused_n4', launch=f'{n3["inst"]}.uo', capture=f'u_mu_fused_n4.{slot}',
                       bits=271, from_um=Np(n3, .5), to_um=Sp(n4, .25 if q == 0 else .75), regs_um=[]))
        st.append(dict(conn=f'mu_tree:u_mu_fused_n4.{da}|{n3["inst"]}', launch=f'u_mu_fused_n4.{da}', capture=f'{n3["inst"]}.dn',
                       bits=173, from_um=Sp(n4, .375 if q == 0 else .625), to_um=Np(n3, .5), regs_um=[]))
    # local E face for BOTH hubs (NE_hub orient MY, 3c3dae6bb).  HBM-MU-QUAD-2 (COORD 23:50): face pin on the N street
    # row above the quads (y = quad top + half street), so the n4 -> root leg runs straight in the street and never
    # bends over the mfused_15 corner.  Valid for --qy mid (both hubs).
    assert QY == 'mid'
    # realise() rescales face-pin y from the input hub height to H (y * H / H_in), so the pin is given in input units
    # (the predecessor's H/2 became y 2647 after rescaling = the corner bend over mfused_15)
    fy = r3(sn((H - QH) / 2) + QH + QSTREET / 2); H_in = t1['outline_um'][1]
    face = [t1['outline_um'][0], fy * H_in / H]
    REPORT['root_face_pin_um'] = [t1['outline_um'][0], fy]; REPORT['root_face_pin_input_frame'] = dict(H_in=H_in, y_in=face[1])
    st.append(dict(conn='mu_tree_root:n4:up', launch='u_mu_fused_n4.uo', capture='face root.up', bits=271,
                   from_um=Sp(n4, .5), to_um=face, regs_um=[]))
    st.append(dict(conn='mu_tree_root:n4:down', launch='face root.dn', capture='u_mu_fused_n4.dn', bits=173,
                   from_um=face, to_um=Sp(n4, .5), regs_um=[]))
    return t, W, H0, t1, lrep
R11.prepare = prepare

# ------------------------------------------------------------------ segment assignment + service rebinding (SU fix)
QUADMAP = {}
INMY0 = {}
CONN = []
PINS = collections.defaultdict(list)   # (a, b) -> [(pin offset on a, pin offset on b, bits)]
# HBM-MU-QUAD-2 pin-facing pairs: follower:leader -- follower legalised so its pins face the leader's pins (atomic pair)
PAIRS = [tuple(x.split(':')) for x in opt('--pair', '').split(',') if x]
PAIRLOG = []
SWEEPS = int(opt('--sweeps', '0'))
SEGX0 = {0: 0.0, 1: None}   # seg -> {quad member name -> inst}
def quadrant(t, S, *a, **kw):
    for n, s in enumerate(t['internal_stations']):
        s['_r13_bits'], s['_r13_id'] = s['bits'], n
    kw['named_ends'] = True
    Q = original(t, S, *a, **kw)
    banks = sorted(h['inst'] for h in t['hard_cores'] if h['inst'].startswith('u_vmb_'))
    assert len(banks) == 16, len(banks)
    asg = {n: i // 8 for i, n in enumerate(banks)}
    for h in Q['cores']:
        n = h['inst']
        m1 = re.fullmatch(r'u_mu_fused_(\d+)', n); m2 = re.fullmatch(r'u_mu_fused_n[123].*_q([01])(?:_\d+)?', n)
        m3 = re.fullmatch(r'u_vmdel_Q(\d)', n)
        if m1: asg[n] = int(m1.group(1)) // 8
        elif m2: asg[n] = int(m2.group(1))
        elif m3: asg[n] = int(m3.group(1)) // 4
        elif n == 'u_mu_fused_n4': asg[n] = 1
    for n, k in asg.items():
        assert n in Q['segof'], n
        Q['segof'][n] = k
    copies = {n for n in Q['segof'] if re.search(r'__q\d+$', n) and n.rsplit('__q', 1)[0] in {h['inst'] for h in t['hard_cores']}}
    rebound = collections.Counter(); newst = []
    for st, ea, eb, ka, kb in Q['stations']:
        ends = [ea, eb]
        for i in (0, 1):
            me, ot = ends[i], ends[1 - i]
            if me[0] == 'C' and me[1] in copies and ot[0] == 'C' and ot[1] not in copies and ot[1] in Q['segof']:
                k = Q['segof'][ot[1]]; nm = me[1].rsplit('__q', 1)[0] + f'__q{k}'
                if nm != me[1]:
                    rebound[me[1].rsplit('__q', 1)[0]] += 1
                    ends[i] = ('C', nm, me[2])
        ea, eb = ends
        ka = Q['segof'][ea[1]] if ea[0] == 'C' else ka
        kb = Q['segof'][eb[1]] if eb[0] == 'C' else kb
        newst.append((st, ea, eb, ka, kb))
    Q['stations'] = newst
    CONN.clear(); PINS.clear()
    for st_, ea_, eb_, ka_, kb_ in newst:
        if ea_[0] == 'C' and eb_[0] == 'C' and ea_[1] != eb_[1]:
            CONN.append((ea_[1], eb_[1], st_.get('bits_parallel', st_['bits'])))
            PINS[(ea_[1], eb_[1])].append((ea_[2], eb_[2], st_.get('bits_parallel', st_['bits'])))
            PINS[(eb_[1], ea_[1])].append((eb_[2], ea_[2], st_.get('bits_parallel', st_['bits'])))
    Q['su_service_rebound'] = dict(rebound)
    REPORT['su_service_rebound'] = dict(rebound)
    # MY mirror of the W-column cells (pin offsets x -> w - x)
    my = set()
    for seg in (0, 1):
        for k in (0, 1):
            b = 4 * seg + k
            my |= {f'u_vmb_Q{b}', f'u_vmb_Q{b}_mu1', f'u_mu_fused_{2 * b}', f'u_mu_fused_{2 * b + 1}'}
    W_ = {h['inst']: h['outline_um'][0] for h in Q['cores']}
    # HBM-MU-QUAD-2: orientation is set by the quad slot, not inherited.  Codex 3c3dae6bb had u_vmb_Q3/_mu1 MY with
    # mirrored pin offsets; in the R0 E-column slot that put its W-face service pins (b3_xq) on the E face inside the
    # 8.64 um VM|FUSED buddy gap (the one failed station route).  Flip = cells whose input orient differs from the slot.
    quadcells = set()
    for b in range(8):
        quadcells |= {f'u_vmb_Q{b}', f'u_vmb_Q{b}_mu1', f'u_mu_fused_{2 * b}', f'u_mu_fused_{2 * b + 1}'}
    # input orientation captured ONCE: quadrant() runs once per k and the core dicts keep the orient written below,
    # while the station pin offsets are regenerated from the input each call
    if 'inmy' not in INMY0: INMY0['inmy'] = {h['inst'] for h in Q['cores'] if h.get('orient', 'R0') == 'MY'}
    inmy = INMY0['inmy']
    flip = (inmy ^ my) & quadcells
    REPORT['orient_flips'] = sorted(flip)
    def mir(e): return ('C', e[1], (r3(W_[e[1]] - e[2][0]), e[2][1])) if e[0] == 'C' and e[1] in flip else e
    Q['stations'] = [(s, mir(ea), mir(eb), ka, kb) for s, ea, eb, ka, kb in Q['stations']]
    for h in Q['cores']:
        if h['inst'] in quadcells: h['orient'] = 'MY' if h['inst'] in my else 'R0'
    for s in t['internal_stations']:
        s.pop('_r13_bits', None); s.pop('_r13_id', None)
    M.face_affine(Q, t['outline_um'][0])
    M.affinity(Q, t, 1)
    for x in Q['stations']:
        x[0].pop('_r13_bits', None); x[0].pop('_r13_id', None)
    return Q
R9.plan_quadrants = quadrant

# ------------------------------------------------------------------ packer: fixed quad + legalised rest
CLR = 25.92   # core-core street
QSTREET = 43.2  # N/S street around the quad (n3 -> n4 -> root leg on the N street)
GAPN4 = TN[0] + 2 * 17.28   # gap between quads holding n4
def quad_pack(W, Hh, cores, **kw):
    import numpy as np
    names = {c['inst'] for c in cores}
    seg = 0 if 'u_mu_fused_n3_q0' in names else 1
    by = {c['inst']: c for c in cores}
    dims = dict(hb_vms=(by[f'u_hb_vms_Q__q{seg}']['w'], by[f'u_hb_vms_Q__q{seg}']['h']),
                xl_ctl=(by[f'u_xl_Q_ctl__q{seg}']['w'], by[f'u_xl_Q_ctl__q{seg}']['h']),
                smw=(by[f'u_smw_Q__q{seg}']['w'], by[f'u_smw_Q__q{seg}']['h']),
                dbk=(by[f'u_hb_dbk_Q__q{seg}']['w'], by[f'u_hb_dbk_Q__q{seg}']['h']),
                cal=(by[f'u_calendar_Q__q{seg}']['w'], by[f'u_calendar_Q__q{seg}']['h']),
                vmdel=(by[f'u_vmdel_Q{4 * seg}']['w'], by[f'u_vmdel_Q{4 * seg}']['h']))
    Mm = quad_members(dims)
    mp = {}
    for k in range(4):
        b = 4 * seg + k
        mp.update({f'vm{k}_0': f'u_vmb_Q{b}', f'vm{k}_1': f'u_vmb_Q{b}_mu1', f'fu{k}_0': f'u_mu_fused_{2 * b}',
                   f'fu{k}_1': f'u_mu_fused_{2 * b + 1}', f'n1_{k}': f'u_mu_fused_n1_q{seg}_{k}', f'vmdel{k}': f'u_vmdel_Q{b}'})
    mp.update({'n2L': f'u_mu_fused_n2L_q{seg}', 'n2R': f'u_mu_fused_n2R_q{seg}', 'n3': f'u_mu_fused_n3_q{seg}',
               'hb_vms': f'u_hb_vms_Q__q{seg}', 'xl_ctl': f'u_xl_Q_ctl__q{seg}', 'smw': f'u_smw_Q__q{seg}',
               'dbk': f'u_hb_dbk_Q__q{seg}', 'cal': f'u_calendar_Q__q{seg}'})
    for m, i in mp.items():
        assert i in by, (i, seg)
        assert abs(by[i]['w'] - Mm[m][2]) < 1e-6 and abs(by[i]['h'] - Mm[m][3]) < 1e-6, (i, by[i], Mm[m])
    # quad origin: q0 flush to the segment-0 E edge, q1 at GAPN4 from the segment-1 W edge -> n4 midway
    qy = sn((Hh - QH) / 2) if QY == 'mid' else (r3(Hh - QH - QSTREET - TN[1]) if QY == 'N' else r3(QSTREET + G))
    qx = sn(W - QW) if seg == 0 else sn(GAPN4)
    if seg == 0:
        qx = r3(W - QW)
    if seg == 1 and Q1POS == 'E':
        qx = r3(W - QW - G)
    place = {mp[m]: (r3(qx + v[0]), r3(qy + v[1])) for m, v in Mm.items()}
    n4b = None
    if seg == 1 and 'u_mu_fused_n4' in by:
        if Q1POS == 'W':
            place['u_mu_fused_n4'] = (r3(GAPN4 / 2 - TN[0] / 2), r3(qy + QH - TN[1]))
        else:   # midpoint of the two n3 centres (q0 n3 at seg-1-local x = -QW/2), on the N street row above the quads
            xm = ((-QW / 2) + (qx + QW / 2)) / 2
            place['u_mu_fused_n4'] = (r3(xm - TN[0] / 2), r3(qy + QH + QSTREET))
            n4b = (xm - TN[0] / 2 - CLR, qy + QH, xm + TN[0] / 2 + CLR, qy + QH + QSTREET + TN[1] + CLR)
    QUADMAP[seg] = dict(origin_seg_local=[qx, qy], members=mp)
    # legalise every other core near its affinity centre (largest first), streets CLR, quad block + N/S street
    g = G; nx = int(W / g); ny = int(Hh / g)
    occ = np.zeros((nx + 1, ny + 1), dtype=np.int32)
    def block(x0, y0, x1, y1):
        i0, i1 = max(0, int(math.floor(x0 / g + 1e-9))), min(nx + 1, int(math.ceil(x1 / g - 1e-9)))
        j0, j1 = max(0, int(math.floor(y0 / g + 1e-9))), min(ny + 1, int(math.ceil(y1 / g - 1e-9)))
        occ[i0:i1, j0:j1] = 1
    block(qx - (0 if seg == 0 or Q1POS == 'E' else GAPN4), qy - QSTREET, qx + QW, qy + QH + QSTREET)
    if n4b: block(*n4b)
    rest = sorted([c for c in cores if c['inst'] not in place], key=lambda c: -c['w'] * c['h'])
    pad = int(round(CLR / g))
    for c in rest:
        fw, fh = int(math.ceil(c['w'] / g - 1e-9)), int(math.ceil(c['h'] / g - 1e-9))
        P_ = np.pad(occ, pad); S = P_.cumsum(0).cumsum(1); S = np.pad(S, ((1, 0), (1, 0)))
        wi, wj = fw + 2 * pad, fh + 2 * pad
        ni, nj = S.shape[0] - wi, S.shape[1] - wj
        win = S[wi:wi + ni, wj:wj + nj] - S[:ni, wj:wj + nj] - S[wi:wi + ni, :nj] + S[:ni, :nj]
        ii = np.arange(ni)[:, None]; jj = np.arange(nj)[None, :]
        x0 = ii * g; y0 = jj * g
        ok = (win == 0) & (x0 >= G) & (x0 + c['w'] <= W - G) & (y0 >= G) & (y0 + c['h'] <= Hh - G)
        if not ok.any():
            raise ValueError(f'quad_pack: no legal site for {c["inst"]} in segment {seg}')
        ox, oy = c['ocx'], c['ocy']
        if c['inst'] in CODEX:
            ox, oy = CODEX[c['inst']][0] - SEGX0[seg], CODEX[c['inst']][1]
        lead = [L for F_, L in PAIRS if c['inst'].startswith(F_ + '__q') and any(n.startswith(L + '__q') and n in place for n in names)]
        if lead:
            ln = [n for n in names if n.startswith(lead[0] + '__q') and n in place][0]
            pp = PINS.get((c['inst'], ln), [])
            if pp:
                bw_ = sum(b for _, _, b in pp)
                tx = sum(b * (place[ln][0] + ob[0] - oa[0]) for oa, ob, b in pp) / bw_
                ty = sum(b * (place[ln][1] + ob[1] - oa[1]) for oa, ob, b in pp) / bw_
                ox, oy = tx + c['w'] / 2, ty + c['h'] / 2
                PAIRLOG.append(dict(seg=seg, follower=c['inst'], leader=ln, bits=bw_, target_centre=[r3(ox), r3(oy)]))
        cost = np.abs(x0 + c['w'] / 2 - ox) + np.abs(y0 + c['h'] / 2 - oy)
        _unused = np.abs(x0 + c['w'] / 2 - c['ocx']) + np.abs(y0 + c['h'] / 2 - c['ocy'])
        cost = np.where(ok, cost, np.inf)
        i, j = np.unravel_index(np.argmin(cost), cost.shape)
        place[c['inst']] = (r3(i * g), r3(j * g))
        occ[i:i + fw, j:j + fh] = 1
    # cluster refinement: re-legalise each core toward 0.5 x (its desired site) + 0.5 x (bit-weighted partner centroid)
    nb = collections.defaultdict(list)
    for a_, b_, bits_ in CONN:
        if a_ in by and b_ in by:
            nb[a_].append((b_, bits_)); nb[b_].append((a_, bits_))
    restn = [c for c in rest]
    restn.sort(key=lambda c: -sum(b for _, b in nb[c['inst']]))
    for sw in range(SWEEPS):
        for c in restn:
            L = nb[c['inst']]
            if not L: continue
            fw, fh = int(math.ceil(c['w'] / g - 1e-9)), int(math.ceil(c['h'] / g - 1e-9))
            i0, j0 = int(round(place[c['inst']][0] / g)), int(round(place[c['inst']][1] / g))
            occ[i0:i0 + fw, j0:j0 + fh] = 0
            sx = sum(b * (place[o][0] + by[o]['w'] / 2) for o, b in L); sy = sum(b * (place[o][1] + by[o]['h'] / 2) for o, b in L)
            sw_ = sum(b for o, b in L)
            ox, oy = c['ocx'], c['ocy']
            if c['inst'] in CODEX: ox, oy = CODEX[c['inst']][0] - SEGX0[seg], CODEX[c['inst']][1]
            tx, ty = 0.5 * ox + 0.5 * sx / sw_, 0.5 * oy + 0.5 * sy / sw_
            P_ = np.pad(occ, pad); S = P_.cumsum(0).cumsum(1); S = np.pad(S, ((1, 0), (1, 0)))
            wi, wj = fw + 2 * pad, fh + 2 * pad
            ni, nj = S.shape[0] - wi, S.shape[1] - wj
            win = S[wi:wi + ni, wj:wj + nj] - S[:ni, wj:wj + nj] - S[wi:wi + ni, :nj] + S[:ni, :nj]
            ii = np.arange(ni)[:, None]; jj = np.arange(nj)[None, :]
            x0 = ii * g; y0 = jj * g
            ok = (win == 0) & (x0 >= G) & (x0 + c['w'] <= W - G) & (y0 >= G) & (y0 + c['h'] <= Hh - G)
            cost = np.where(ok, np.abs(x0 + c['w'] / 2 - tx) + np.abs(y0 + c['h'] / 2 - ty), np.inf)
            i, j = np.unravel_index(np.argmin(cost), cost.shape)
            place[c['inst']] = (r3(i * g), r3(j * g)); occ[i:i + fw, j:j + fh] = 1
    hs = [[r3(qy - QSTREET), r3(qy)], [r3(qy + QH), r3(qy + QH + QSTREET)], [r3(qy + rows[1] - mid), r3(qy + rows[1])]]
    vs = [[r3(qx), r3(qy), r3(qx + OS), r3(qy + QH)], [r3(qx + QW - OS), r3(qy), r3(qx + QW), r3(qy + QH)]]
    area = sum(c['w'] * c['h'] for c in cores)
    return place, dict(lane_um=CLR, shelves=0, packing_search='HBM-MU-QUAD fixed quad + greedy legaliser', quad_seg=seg,
                       streets=dict(horizontal_y_um=hs, vertical_rects_um=vs), displacement_um_total=0.0)
R9.HR.pack_hub = quad_pack

# ------------------------------------------------------------------ evaluate: smallest k with whole + both segment axes <= 0.6
REPORT = {}
part = 'NW_hub' if tn == 'q_hub_nw' else 'NE_hub'
t, W, H0, t1, lrep = R11.prepare(P, part, tn, 6, 3)
rows_k = []; sel = None
SEGX0[1] = sn(bound)
for k in range(kmin, 9):
    r = R11.eval_hub(t1, H0, W, H, bound, k, 6, 3, 2, 1000, route=False)
    vals = [r['cut'][a]['max_use'] for a in 'xy'] + [s['cut_' + a] or 0 for s in r['segs'] for a in 'xy']
    row = dict(k=k, whole={a: r['cut'][a]['max_use'] for a in 'xy'}, segs=[(s['cut_x'], s['cut_y']) for s in r['segs']],
               max=max(vals), ok=max(vals) <= .6 + 1e-9)
    rows_k.append(row); print(json.dumps(dict(stage='cut', hub=tn, **row)), flush=True)
    if row['ok']: sel = k; break
if '--cutonly' in argv:
    print(json.dumps(dict(stage='cutonly', rows=[(x['k'], x['max']) for x in rows_k]))); raise SystemExit(0)
FK = int(argv[argv.index('--force-k') + 1]) if '--force-k' in argv else None
if FK: sel = FK
if sel is None:
    (out / 'FAIL.json').write_text(json.dumps(dict(hub=tn, rows=rows_k), indent=1)); raise SystemExit(1)
r = R11.eval_hub(t1, H0, W, H, bound, sel, 6, 3, 2, 1000, route='--noroute' not in argv)
st = r['stations']; cores = r['cores']
# finalize (as Codex finalize_buddy): native VM<->FUSED buddy links direct (no relays, <=405); MU tree period <= 4, q0 == q1
fin = []
BUDDY_BAD = []
def isf(x): return re.match(r'^u_mu_fused_\d+(?:\.|$)', x) is not None
for s in st:
    a, c = s.get('launch', ''), s.get('capture', '')
    if (a.startswith('u_vmb_') and isf(c)) or (isf(a) and c.startswith('u_vmb_')):
        L = sum(abs(x - y) for x, y in zip(s['from_um'], s['to_um']))
        if s.get('serial_k', 1) != 1: raise ValueError('native buddy serialised ' + s['conn'])
        if L > 405: BUDDY_BAD.append((s['conn'], r3(L)))
        if s.get('regs_um'): fin.append(dict(conn=s['conn'], kind='direct_native_gap', removed=len(s['regs_um']), L=r3(L)))
        s['regs_um'] = []
    if str(s.get('conn', '')).startswith('mu_tree') and s.get('serial_k', 1) > 1:
        par = s.get('bits_parallel', s['bits'])
        k4 = min(s['serial_k'], 4)
        if k4 != s['serial_k']:
            fin.append(dict(conn=s['conn'], kind='tree_period4', old_k=s['serial_k'], new_k=k4)); s['serial_k'] = k4; s['bits'] = math.ceil(par / k4)
# equal MU tree period for q0/q1 legs to n4 (GEOM-15 (b): level above the quads equal, no schedule delay-matching)
leg = [s for s in st if str(s.get('conn', '')).startswith('mu_tree:') and 'n4' in s['conn']]
for d in ('up', 'down'):
    L_ = [s for s in leg if (s['conn'].endswith('|u_mu_fused_n4') if d == 'up' else s['conn'].startswith('mu_tree:u_mu_fused_n4'))]
    kk = max(s.get('serial_k', 1) for s in L_)
    for s in L_:
        par = s.get('bits_parallel', s['bits'])
        if s.get('serial_k', 1) != kk:
            fin.append(dict(conn=s['conn'], kind='equal_q0q1_period', old_k=s.get('serial_k', 1), new_k=kk))
        if kk > 1: s['serial_k'] = kk; s['bits_parallel'] = par; s['bits'] = math.ceil(par / kk)
u = R9.cut(dict(outline_um=[W, H], hard_cores=cores, internal_stations=st))['blocked']
segs = [R10p for R10p in [ns['R10'].profile(W, H, dict(hard_cores=cores, internal_stations=st), a_, b_) for a_, b_ in ((0, bound), (bound, W))]]
mx = max([u[a]['max_use'] for a in 'xy'] + [x[a]['max_use'] or 0 for x in segs for a in 'xy'])
ct = copy.deepcopy(t); ct['outline_um'] = [W, H]; ct['hard_cores'] = cores; ct['internal_stations'] = st
for h in ct['hard_cores']:
    h.setdefault('obs_max', 'M5')
ct['note'] = ct.get('note', '') + ' | HBM-MU-QUAD unified SU/MU hub: 2 fixed replicated quad tiles + n4, services rebound per quad (SU fix); model only'
(out / 'candidate_type.json').write_text(json.dumps(ct, indent=1) + '\n')
# overlap check
ov = []
rects = [(h['inst'],) + tuple(HR._core_rect(h)) for h in cores]
for i in range(len(rects)):
    a = rects[i]
    assert a[1] >= -1e-6 and a[2] >= -1e-6 and a[3] <= W + 1e-6 and a[4] <= H + 1e-6, a
    for b in rects[i + 1:]:
        if a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6 and a[2] < b[4] - 1e-6 and b[2] < a[4] - 1e-6: ov.append((a[0], b[0]))
REPORT.update(hub=tn, H=H, bound=bound, k=sel, k_rows=rows_k, cut=u, segments=segs, max_axis=mx,
              verdict='PASS_MODEL_CUT' if mx <= .6 + 1e-9 else 'FAIL_MODEL_CUT', stats=r['stats'], cc=len(r['cc']),
              finalize=fin, overlaps=ov, pairs=PAIRLOG, buddy_bad=BUDDY_BAD, quad=dict(QW=QW, QH=QH, map=QUADMAP), add=ADD.get(tn), cores=len(cores),
              core_area_mm2=r3(sum(h['outline_um'][0] * h['outline_um'][1] for h in cores) / 1e6))
(out / 'report.json').write_text(json.dumps(REPORT, indent=1, default=str) + '\n')
if BUDDY_BAD: raise ValueError(f'native buddy links > 405 um: {BUDDY_BAD[:6]} ({len(BUDDY_BAD)})')
print(json.dumps({k: REPORT[k] for k in ('hub', 'k', 'max_axis', 'verdict', 'stats', 'cc', 'overlaps', 'su_service_rebound', 'cores', 'core_area_mm2')}, default=str))
