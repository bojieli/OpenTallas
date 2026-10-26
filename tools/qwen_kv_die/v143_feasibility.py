"""v1.4.3 feasibility: matched-bit worst Manhattan pin distances for the band + near-head feed-through layout (one group,
lower pair = heads 0 (far) / 1 (near), MX under an R0 ECTL).  Coordinates: ECTL-local (ECTL at x 0..648, y 0..129.6),
head column x -216..864.  Uses actual closed LEFs."""
import re, sys, json, itertools
from pathlib import Path
R = Path(__file__).resolve().parents[2]
RT = R/'physical/ref_tile'
def lefpins(p):
    s = Path(p).read_text(); sz = tuple(map(float, re.search(r'SIZE (\S+) BY (\S+)', s).groups())); pins = {}
    for m in re.finditer(r'^\s*PIN (\S+)\s*$(.*?)^\s*END \1', s, re.M | re.S):
        pts = []
        for x0, y0, x1, y1 in re.findall(r'RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', m[2]):
            pts.append(((float(x0)+float(x1))/2, (float(y0)+float(y1))/2))
        pins[m[1]] = pts
    return sz, pins
def xf(pt, org, size, orient):
    x, y = pt; w, h = size
    if orient in ('MY', 'R180'): x = w - x
    if orient in ('MX', 'R180'): y = h - y
    return (org[0]+x, org[1]+y)
def P(view, name):
    return lefpins(RT/view/'views'/name/(name+'.lef'))
ECTL = {r: P(f'qkd_ectl_{r}_tp8_direct' if r != 'a' else 'qkd_ectl_a_tp8_direct', n) for r, n in
        [('a', 'qkd_ectl_a_tp8_epoch_direct'), ('b', 'qkd_ectl_b_tp8_direct'), ('c', 'qkd_ectl_c_tp8_direct')]}
EX = dict(a=0.0, b=254.88, c=509.76)
GATH = P('qkh_head_gather_stage', 'qkh_head_gather_stage'); SST = P('qkh_head_sstage', 'qkh_head_sstage')
FRONT = P('qkh_r4_frontq_1014', 'ot_qkh_head_frontq_native'); SCORE = P('qkh_r4_score4_1014', 'ot_qkh_head_score4_native')
plan = json.loads((R/'results/arch/qwen_split_1014/head_native_r4_codex_1014/plan.json').read_text())
CH = plan['children']; HH = 492.456
def epin(role, name):          # ECTL leaf pin in ECTL-local coords (R0 ECTL)
    sz, pins = ECTL[role]; return [xf(p, (EX[role], 0.0), sz, 'R0') for p in pins[name]]
def stage_pins(view, org, orient, port, bit=None):
    sz, pins = view; nm = f'{port}[{bit}]' if bit is not None else port
    return [xf(p, org, sz, orient) for p in pins[nm]]
def dist(a, b): return max(abs(p[0]-q[0])+abs(p[1]-q[1]) for p in a for q in b)
# t word bit -> ECTL producer pin (Codex signal(): pair-level names t{pr}_row/_cl/_q, e{h})
def producer(bit, h):
    pr = h // 2
    if bit < 519:                       # q_data 512 + beat 6 + valid  (ti[518:0]) -> c t{pr}_q[?]
        q = {**{i: i+7 for i in range(512)}, **{512+j: j+1 for j in range(6)}, 518: 0}[bit]
        return 'c', f't{pr}_q[{q}]'
    if bit < 531: return 'b', f't{pr}_cl[{bit-519+4}]'            # lt 12
    if bit < 1043: return 'a', f't{pr}_row[{bit-531}]'            # row lower 512
    if bit < 1555: return 'b', f't{pr}_row[{bit-1043}]'           # row upper 512 (b t_row)
    return 'b', f't{pr}_cl[{bit-1555}]'                           # c 4
def run(Hft=503.256, chan=(189.0, 210.6), gx_far=416.016, gx_near=86.4, band_rows=5, nf_band=32.4):
    out = {}
    row = lambda k: -28.08*k - .048          # k-th 21.6 row below the ECTL (y of its bottom edge)
    gy = row(3)
    t1n = (gx_near, row(4)); t2n = (gx_near, row(5))
    top1 = row(band_rows) - 5.4                # near head h1 (MX) top
    chy = top1 - chan[1]                       # channel stage bottom (MX: local y measured from top)
    bot1 = top1 - Hft
    t2f = (gx_far, bot1 - 5.4 - 21.6)
    top0 = bot1 - nf_band
    # data flows DOWN: stages MX (input = N face at top). gather view: ti_a S face (y=0) -> in MX at top
    def g(org, port, bit): return stage_pins(GATH, org, 'MX', port, bit)
    res = {}
    for name, a_org, b_org in [('gather_f->T1f(channel)', (gx_far, gy), (gx_far, chy)),
                               ('T1f->T2f(nf band)', (gx_far, chy), t2f),
                               ('gather_n->T1n', (gx_near, gy), t1n), ('T1n->T2n', t1n, t2n)]:
        w = max(dist(g(a_org, 'ti_b', b), g(b_org, 'ti_a', b)) for b in range(0, 1559, 7))
        res[name] = round(w, 1)
    # final hop T2 -> 4 fronts of the head (MX head: local (x,y) -> (x+216 col offset .., top - y))
    names = ['q_data_in']*512 + ['q_beat_in']*6 + ['q_valid_in'] + ['lt_in']*12 + ['row_in']*1024 + ['c_in']*4
    idx = list(range(512)) + list(range(6)) + [None] + list(range(12)) + list(range(1024)) + list(range(4))
    def front_pts(top, f, port, i):
        x0, y0, w, h = CH[f'front{f}']
        sz, pins = FRONT
        nm = port if i is None else f'{port}[{i}]'
        pts = [xf(p, (0, 0), sz, 'R0') for p in pins[nm]]
        return [(-216 + x0 + px, top - (y0 + py)) for px, py in pts]
    for hn, top, t2 in [('near h1', top1, t2n), ('far h0', top0, t2f)]:
        worst = (0, None)
        for b in range(0, 1559, 3):
            port, i = names[b], idx[b]
            fr = [0, 1, 2, 3]
            if port == 'row_in':
                fr = [i // 256]; i = i % 256
            d = max(dist(g(t2, 'ti_b', b), front_pts(top, f, port, i)) for f in fr)
            if d > worst[0]: worst = (round(d, 1), f'{port}[{i}]')
        res[f'T2->{hn} fronts'] = worst
    # producer -> chunk is Codex's (<=152 um); ECTL producer -> gather (if no ABC) for reference
    w = 0
    for b in range(0, 1559, 5):
        role, pn = producer(b, 1)
        try: w = max(w, dist(epin(role, pn), g((gx_near, gy), 'ti_a', b)))
        except KeyError: pass
    res['ECTL producer->gather_n (no ABC, reference)'] = round(w, 1)
    res['geometry'] = dict(gather_y=gy, top_near=round(top1, 3), channel_y=round(chy, 3), bottom_near=round(bot1, 3),
                           t2f_y=round(t2f[1], 3), top_far=round(top0, 3), group_half_growth=round(-(top0 - HH) - (2*HH + 5.4 + 21.6), 1))
    return res
if __name__ == '__main__':
    print(json.dumps(run(), indent=1))

def chunk_of(bit):           # gather/T1 input bit -> (role, chunk bit) per qkh_head_ingress_abc
    if bit < 519: return 'c', bit
    if bit < 531: return 'b', bit-519
    if bit < 1043: return 'a', bit-531
    if bit < 1555: return 'b', bit-1043+12
    return 'b', bit-1555+524
CHX = dict(a=129.6, b=264.816, c=480.6)
def scan(tier=1, Hft=503.256):
    best = []
    row = lambda k: -28.08*k - .048
    names = ['q_data_in']*512 + ['q_beat_in']*6 + ['q_valid_in'] + ['lt_in']*12 + ['row_in']*1024 + ['c_in']*4
    idx = list(range(512)) + list(range(6)) + [None] + list(range(12)) + list(range(1024)) + list(range(4))
    top1 = row(5) - 5.4
    for gx in [x*5.4 for x in range(-40, 101)]:
        gy = row(3)
        def g(org, port, b): return stage_pins(GATH, org, 'MX', port, b)
        # chunk (tier, MX) -> gather
        w1 = 0
        for b in range(0, 1559, 4):
            role, cb = chunk_of(b)
            cp = [((CHX[role] + 13.5 + .192*cb), row(tier) + 21.6*0)]
            w1 = max(w1, dist(cp, g((gx, gy), 'ti_a', b)))
        # T2 directly above the near head's fronts (near: t2 at row(5)); far: t2 above far head
        t2 = (gx, row(5)) if tier == 1 else (gx, top1 - Hft - 5.4 - 21.6)
        top = top1 if tier == 1 else top1 - Hft - 32.4
        w2 = 0
        for b in range(0, 1559, 3):
            port, i = names[b], idx[b]; fr = [0, 1, 2, 3]
            if port == 'row_in': fr = [i // 256]; i = i % 256
            for f in fr:
                x0, y0, ww, hh = CH[f'front{f}']; sz, pins = FRONT
                nm = port if i is None else f'{port}[{i}]'
                pts = [(-216 + x0 + px, top - (y0 + py)) for px, py in pins[nm]]
                w2 = max(w2, dist(g(t2, 'ti_b', b), pts))
        best.append((max(w1, w2), round(w1, 1), round(w2, 1), gx))
    best.sort()
    return best[:3]

def chunk_opt(gx=108.0, h=1, tier=1):
    """Choose each role's chunk x to minimise max(producer->chunk, chunk->gather) (chunk MX rows below the ECTL)."""
    row = lambda k: -28.08*k - .048
    gy = row(3); out = {}
    def g(org, port, b): return stage_pins(GATH, org, 'MX', port, b)
    bits = {r: [b for b in range(1559) if chunk_of(b)[0] == r] for r in 'abc'}
    for role in 'abc':
        best = None
        for cx in [x*5.4 for x in range(-30, 120)]:
            cy = row(tier)
            w_in = w_out = 0
            for b in bits[role][::3]:
                _, cb = chunk_of(b)
                pin_in = [(cx + 13.5 + .192*cb, cy + 21.6)]; pin_out = [(cx + 13.5 + .192*cb, cy)]
                r_, pn = producer(b, h)
                try: w_in = max(w_in, dist(epin(r_, pn), pin_in))
                except KeyError: pass
                w_out = max(w_out, dist(pin_out, g((gx, gy), 'ti_a', b)))
            cand = (max(w_in, w_out), round(w_in, 1), round(w_out, 1), cx)
            if best is None or cand < best: best = cand
        out[role] = best
    return out

def direct_gather(h=1, rows=(3,)):
    row = lambda k: -28.08*k - .048
    res = []
    for gx in [x*5.4 for x in range(-40, 101)]:
        w = 0; wb = None
        for k in rows:
            org = (gx, row(k))
            for b in range(0, 1559, 2):
                role, pn = producer(b, h)
                try: d = dist(epin(role, pn), stage_pins(GATH, org, 'MX', 'ti_a', b))
                except KeyError: continue
                if d > w: w, wb = d, pn
            for j in range(16):
                d = dist(epin('c', f'e{h}[{j}]'), stage_pins(GATH, org, 'MX', 'e_a', j))
                if d > w: w, wb = d, f'e{h}[{j}]'
        res.append((round(w, 1), gx, wb))
    res.sort(); return res[:3]

NAMES = ['q_data_in']*512 + ['q_beat_in']*6 + ['q_valid_in'] + ['lt_in']*12 + ['row_in']*1024 + ['c_in']*4
IDX = list(range(512)) + list(range(6)) + [None] + list(range(12)) + list(range(1024)) + list(range(4))
def chain(xg=226.8, xt1n=226.8, xt2n=108.0, xt1f=226.8, xt2f=108.0, Hft=508.656, nf=32.4, chan_local=189.0):
    row = lambda k: -28.08*k - .048
    g = lambda org, port, b: stage_pins(GATH, org, 'MX', port, b)
    G_n, G_f, T1n, T2n = (xg, row(1)), (xg, row(2)), (xt1n, row(3)), (xt2n, row(4))
    top1 = row(4) - 5.4; chy = top1 - chan_local - 21.6; T1f = (xt1f, chy)
    bot1 = top1 - Hft; T2f = (xt2f, bot1 - 5.4 - 21.6); top0 = bot1 - nf
    out = {}
    def hop(name, a, b, pa='ti_b', pb='ti_a'):
        w = max(dist(g(a, pa, i), g(b, pb, i)) for i in range(0, 1559, 3))
        w = max(w, max(dist(g(a, 'e_b', j), g(b, 'e_a', j)) for j in range(16)))
        out[name] = round(w, 1)
    def prod(name, org, h):
        w = 0
        for b in range(0, 1559, 2):
            role, pn = producer(b, h)
            try: w = max(w, dist(epin(role, pn), g(org, 'ti_a', b)))
            except KeyError: pass
        w = max(w, max(dist(epin('c', f'e{h}[{j}]'), g(org, 'e_a', j)) for j in range(16)))
        out[name] = round(w, 1)
    def fronts(name, org, top):
        w = (0, None)
        for b in range(0, 1559, 3):
            port, i = NAMES[b], IDX[b]; fr = [0, 1, 2, 3]
            if port == 'row_in': fr = [i // 256]; i = i % 256
            for f in fr:
                x0, y0, ww, hh = CH[f'front{f}']; sz, pins = FRONT
                nm = port if i is None else f'{port}[{i}]'
                pts = [(-216 + x0 + px, top - (y0 + py)) for px, py in pins[nm]]
                d = dist(g(org, 'ti_b', b), pts)
                if d > w[0]: w = (round(d, 1), nm, f)
        for j in range(16):
            for f in range(4):
                x0, y0, ww, hh = CH[f'front{f}']; sz, pins = FRONT
                pts = [(-216 + x0 + px, top - (y0 + py)) for px, py in pins[f'e_in[{j}]']]
                d = dist(g(org, 'e_b', j), pts)
                if d > w[0]: w = (round(d, 1), f'e_in[{j}]', f)
        out[name] = w
    prod('ECTL->G_near (pair word, 2 loads)', G_n, 1); prod('ECTL->G_far', G_f, 0)
    hop('G_n->T1n', G_n, T1n); hop('T1n->T2n', T1n, T2n); fronts('T2n->near fronts', T2n, top1)
    hop('G_f->T1f (near-head channel)', G_f, T1f); hop('T1f->T2f (nf band)', T1f, T2f); fronts('T2f->far fronts', T2f, top0)
    out['geometry'] = dict(top_near=round(top1, 2), chan_y=round(chy, 2), bot_near=round(bot1, 2), top_far=round(top0, 2),
                           half_group_growth=round((-top0 + 492.456) - (2*492.456 + 5.4 + 2.16), 1))
    return out

def score_chain(top1=-117.77, Hft=508.656, nf=32.4, chan_local=189.0):
    row = lambda k: -28.08*k - .048
    bot1 = top1 - Hft; top0 = bot1 - nf; chy = top1 - chan_local - 21.6
    s_ = lambda org, port, j: stage_pins(SST, org, 'R0', port, j)
    sz, pins = SCORE
    def score_pins(top, j):                     # MX head: score child at head-local (550.8, 54)
        x0, y0, w, h = CH['score']
        nm = f'sc_o[{j}]' if j < 32 else ('sf_o' if j == 32 else 'gf_o')
        return [(-216 + x0 + px, top - (y0 + py)) for px, py in pins[nm]]
    S1n, S2n = (437.4, row(4)), (556.2, row(3))
    S1f, S2f = (437.4, bot1 - 5.4 - 21.6), (479.4, chy)
    out = {}
    def ectl_s(h, j):   # s{h} bit j: RTL s = {sc_d, sc_f, g_f}?  die s = [sc_d, sc_f, g_f] LSB first
        return epin('c', f's{h}[{j}]')
    # die bus order for s: sc_d (32) bits 0..31, sc_f 32, g_f 33
    for nm, top, S1, S2, h in [('near', top1, S1n, S2n, 1), ('far', top0, S1f, S2f, 0)]:
        a = max(dist(score_pins(top, j), s_(S1, 's_a', j)) for j in range(34))
        b = max(dist(s_(S1, 's_b', j), s_(S2, 's_a', j)) for j in range(34))
        c = max(dist(s_(S2, 's_b', j), ectl_s(h, j)) for j in range(34))
        out[nm] = dict(score_to_S1=round(a, 1), S1_to_S2=round(b, 1), S2_to_ECTL=round(c, 1))
    return out
