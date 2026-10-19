#!/usr/bin/env python3
"""H-PLANSTUDY (owner 0dn, 10-17): plan-level comparison of three HBM die organisations, NO RTL.

  (a) d4f as is (16 SM / 2 stacks / 4 cores, cores stacked at the E end, E column IDX + hc_eng + SerDes),
      run9 lane model (claude/hrelay-lanes-1017 dry run on run8 pins) -- the baseline;
  (b) d4f with PER-QUADRANT services: each 4-SM quadrant owns one full core (VM slice 8 banks + hub, SU slices + SU
      core + programme slice, SFU groups + SFU core/store, HC client + its own HC engine, IDX scorer quarter + local
      IDX ctl/query, COLL engine with its own SerDes endpoint) laid out directly above its 4 SMs; only collectives
      (COLL ring / VM ring as a COLL tree), the IDX top-k merge, argmax and host cross quadrants, on fixed-pitch fat lanes
      through a centre strip that also holds the tree roots;
  (c) an 8-SM / 1-stack / 2-quadrant die = the S half of (b) + the strip, more dies in the array.

Two models, the same for all three plans:
  1. PLAN GRAPH (tools/hbm_die_v15/v6_eval.py, the d4f plan tool): compact.P.json + compact.graph.json per plan ->
     sliding-window pin cut, bit-weighted relay stages per link class (pin-to-pin lane route, 480 um), bit-mm.
     (b)/(c) graphs are the d4f graph re-wired: every SM-side class (SM_X, SM_OUT, KV_DESC, HBM_VM, VM_HBM) goes to the
     SM's own quadrant core; HC_ENG goes to the quadrant's own engine.
  2. BUS MODEL (this file): every relayed bus of the run9 dry run (driver instance, sink instances, bits, clock
     domain) at block-instance level.  (a) uses the run9 rows as measured (pins, stations, depths).  (b)/(c) move every
     instance with its plan block (relative position kept) or to an explicit home, and RE-WIRE each bus:
       R1 quadrant service (a driver named *_SW/_SE/_NW/_NE): a sink in another quadrant is served by that quadrant's
          replica (the same master in the sink's quadrant); duplicate (driver, sink) pairs merge;
       R2 die-wide drivers (host, su_prog, col_*, tkm, argmax, idx merge, ckgen/status): a TREE -- one fat lane per
          sink quadrant from the root to the quadrant core, then the local fan-out (the cross-quadrant part is counted
          as class XQ);
       R3 cross-quadrant by function (COLL ring, VM ring, IDX scorer -> merge, HC partials): kept, as class XQ.
     Per bus: route length = Manhattan pin distance x the detour factor measured on (a) (run9 station hops /
     Manhattan); stages = ceil(L / 380) (the run9 plan spacing, every hop <= 405 um); a broadcast is a rectilinear
     MST from the driver (stations = MST / 380, depth = the farthest sink).  Relay tiles = sum over buses of
     ceil(bits / lane) x stations (lane 136 for forks, 624 / 48 for point-to-point, as run9) -- calibrated on (a).
     Equal-age broadcast depth per domain = the deepest fork bus (every sink padded to it).

    python3 tools/hbm_die_v15/plan_study_1017.py --out results/arch/hbm_plan_study_1017
"""
import argparse, collections, copy, json, math, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v15'))
import reticle  # noqa: E402

A_DIR = ROOT / 'results/arch/hbm_die_v15/d4f_a2p_fullcore'
RUN9 = Path('/home/ubuntu/artifacts/hdie-d4/d4f_run9/dry_stations_r9_lanes_run8pins.json')
RUN9_LAYER = Path('/home/ubuntu/artifacts/hdie-d4/d4f_run9/dry_layer_report.json')
RUN8_MANIFEST = Path('/home/ubuntu/artifacts/hdie-d4/d4f_run8b/run8_manifest.json')
KAPPA_FORK, KAPPA_P2P = 1.204, 1.038   # run9 measured / model depth on plan (a): median over fork / p2p buses (depth >= 10)
SPACING = 380.0            # run9 plan spacing (every hop <= 405)
REACH = 405.0
QS = ('SW', 'SE', 'NW', 'NE')
W_DIE = 20200.0          # plans (b)/(c): quadrant pairs + a 2.2 mm spine (d4f (a) is 22,762.24)
W_A = 22762.24
EDGE = 42.4
BAND_Y = 8934.72
SU_H = 2825.28
ROWGAP = 200.0
STRIP_H = 1450.0

# ----------------------------------------------------------------------------------------------- plan geometry
def mirror_x(r, W):
    r = dict(r); r['x'] = round(W - r['x'] - r['w'], 3); return r


def mirror_y(r, H):
    r = dict(r); r['y'] = round(H - r['y'] - r['h'], 3); return r


def rect(x, y, w, h, orient='R0'):
    return dict(x=round(x, 3), y=round(y, 3), w=round(w, 3), h=round(h, 3), orient=orient)


def quadrant_core_template(PA, q, side='inner'):
    """block rects of one quadrant (SW frame: S half, W side) in plan (b): 4 bank-pair groups above the SMs, the
    quadrant core column (VM hub, SU core, SFU core/store, COLL, HC client + its HC engine, local IDX ctl/query) at
    the INNER (die-centre) or OUTER (SerDes edge) end, the IDX scorer quarter at the other end."""
    out = {}
    src = q
    gw = max(max(PA[n]['x'] + PA[n]['w'] for n in PA if re.match(rf'^(vmb|hc|sfu|su|quant)_{src}\d$', n) and
                 PA[n]['x'] < PA[f'vmb_{src}{2 * g}']['x'] + 3000 and PA[n]['x'] >= PA[f'vmb_{src}{2 * g}']['x'] - 1)
             - PA[f'vmb_{src}{2 * g}']['x'] for g in range(4))
    pitch = gw + 50.0
    if side == 'outer':
        core_x = EDGE; grp_x = EDGE + 3100 + 50
    else:
        grp_x = EDGE; core_x = grp_x + 2 * pitch
    for g in range(4):
        names = [f'vmb_{src}{2 * g}', f'vmb_{src}{2 * g + 1}', f'hc_{src}{g}', f'sfu_{src}{g}', f'su_{src}{g}']
        if f'quant_{src}{g}' in PA:
            names.append(f'quant_{src}{g}')
        x0 = PA[f'vmb_{src}{2 * g}']['x']
        y0 = min(PA[n]['y'] for n in names); y1 = max(PA[n]['y'] + PA[n]['h'] for n in names)
        gx = grp_x + (g % 2) * pitch
        gy = BAND_Y + (g // 2) * (SU_H + ROWGAP)
        flip = q in ('NW', 'NE')              # (a) N groups are y-mirrored: un-mirror into the S frame
        for n in names:
            r = PA[n]
            ry = (y1 - (r['y'] + r['h'])) if flip else (r['y'] - y0)
            out[n] = rect(gx + (r['x'] - x0), gy + ry, r['w'], r['h'])
    s = lambda n: (PA[f'{n}_{src}']['w'], PA[f'{n}_{src}']['h'])
    top = BAND_Y + 2 * SU_H + ROWGAP
    w, h = s('sfucore'); out[f'sfucore_{q}'] = rect(core_x, BAND_Y, w, h)
    w2, h2 = s('sfus'); out[f'sfus_{q}'] = rect(core_x, BAND_Y + h + 100, w2, h2)
    w3, h3 = s('coll'); out[f'coll_{q}'] = rect(core_x, top - h3, w3, h3)
    out[f'hce_{q}'] = rect(core_x, BAND_Y + h + 100 + h2 + 50, 1598.4, 1598.4)   # quadrant HC engine
    bx = core_x + 1698.4
    y = BAND_Y
    for n in ('sucore', 'sucx', 'dbk', 'hc', 'cij'):
        w5, h5 = s(n)
        out[f'{n}_{q}'] = rect(bx, y, w5, h5); y += h5 + 60
    out[f'idxq_{q}'] = rect(bx, y, 560.0, 300.0)                   # local IDX ctl + query (idx_ctl + idx_q replica)
    w4, h4 = s('vmh')
    out[f'vmh_{q}'] = rect(core_x + 3100 - w4, BAND_Y, w4, h4) if side == 'inner' else rect(core_x + 1698.4 + 920, BAND_Y + 2400, w4, h4)
    # IDX scorer quarter (2 x 3050^2 / 4) in the spine between the two SM groups, right above its PCs (keys from HBM)
    # (the spine is 2.24 mm wide: the two scorer quarters of one stack are stacked in y)
    out[f'idxs_{q}'] = rect(W_DIE / 2 - 897.5, 2156.0 + (2690.0 if q in ('SE', 'NE') else 0.0), 1795.0, 2590.0)
    out[f'pleaf_{q}'] = rect(W_DIE / 2 - 450.0, 2156.0 + 2 * 2690.0, 400.0, 400.0)   # PHY-side host / config leaf
    return out


def plan_b(PA, halves=('S', 'N'), side='inner'):
    P = {}
    H = 2 * (BAND_Y + 2 * SU_H + ROWGAP + 100) + STRIP_H if halves == ('S', 'N') else BAND_Y + 2 * SU_H + ROWGAP + 100 + STRIP_H + 21.6
    smx = [PA[f'sm_SW{i}']['x'] for i in range(4)]       # W quadrant SM columns as (a) (pair gaps keep the XQL stores)
    for half in halves:
        st = 'SW' if half == 'S' else 'NW'
        loc = {}
        phy = dict(PA['phy_SW']); phy['x'] = round(W_DIE / 2 - phy['w'] / 2, 3); loc[f'phy_{st}'] = rect(phy['x'], 21.6, phy['w'], phy['h'])
        for i in range(8):
            r = PA[f'pc_SW{i}']; loc[f'pc_{st}{i}'] = rect(phy['x'] + 2 + i * 1136.8, r['y'], r['w'], r['h'])
        for i in range(8):
            r = PA[f'sm_SW{i}']
            x = smx[i] if i < 4 else W_DIE - smx[7 - i] - r['w']
            loc[f'sm_{st}{i}'] = rect(x, r['y'], r['w'], r['h'])
        for p in range(4):                     # XQL pair stores: pair p sits in the gap of SM pair (2p, 2p+1)
            for n in ('eg', 'bd', 'bfq0', 'bfq1', 'bfq2', 'bfq3'):
                r = PA[f'xq_SW_p{p}_{n}']
                dx = loc[f'sm_{st}{2 * p}']['x'] - PA[f'sm_SW{2 * p}']['x']
                loc[f'xq_{st}_p{p}_{n}'] = rect(r['x'] + dx, r['y'], r['w'], r['h'])
        qW, qE = ('SW', 'SE') if half == 'S' else ('NW', 'NE')
        for q, east in ((qW, False), (qE, True)):
            t = quadrant_core_template(PA, q, side)
            for n, r in t.items():
                loc[n] = mirror_x(r, W_DIE) if east else r
        if half == 'N':
            loc = {n: mirror_y(r, H) for n, r in loc.items()}
            for n in loc:
                if n.startswith('xq_'):
                    loc[n]['orient'] = 'MX'
        P.update(loc)
    # ---- centre strip (b) / top strip (c): SerDes pairs at the W and E edges, tree roots in the middle
    ys = BAND_Y + 2 * SU_H + ROWGAP + 100
    pairs_w = [('S0', 'SW'), ('S1', 'host')] + ([('N0', 'NW')] if 'N' in halves else [])
    pairs_e = [('S3', 'SE')] + ([('N2', 'NE')] if 'N' in halves else [])
    for i, (k, _) in enumerate(pairs_w):
        P[f'lk_{k}'] = rect(EDGE + i * 1135, ys + 50, 600, 600); P[f'ep_{k}'] = rect(EDGE + i * 1135 + 650, ys + 50, 434.72, 515.2)
    for i, (k, _) in enumerate(pairs_e):
        x = W_DIE - EDGE - (i + 1) * 1135
        P[f'lk_{k}'] = rect(x + 485, ys + 50, 600, 600); P[f'ep_{k}'] = rect(x, ys + 50, 434.72, 515.2)
    cx = W_DIE / 2
    P['tkm_SW'] = rect(cx - 1500, ys + 25, 3000, 1400)            # top-k merge (2000 x 2120 re-shaped, same area)
    P['idx_sel'] = rect(cx - 1500 - 700, ys + 50, 600, 450)
    P['idx_link'] = rect(cx - 1500 - 700, ys + 550, 650, 500)
    P['idx_ctl'] = rect(cx + 1600, ys + 50, 300, 260)            # die-level IDX coordinator (launch, merge control)
    P['idx_op'] = rect(cx + 1600, ys + 360, 216, 108)
    P['idx_q'] = rect(cx + 1600, ys + 520, 260, 260)
    P['host_cp'] = rect(cx + 2000, ys + 50, 1300, 700)            # host CP ingress + status (carried grant)
    return P, H


def plan_names(P):
    return sorted(P)


# ----------------------------------------------------------------------------------------------- plan graphs
def quad_of_sm(n):
    """(b) quadrant of an SM-side plan block / instance with an SM (or PC) index"""
    m = re.match(r'^(sm|pc|svg|cp_svg|xc|vmks|wbc)_(SW|NW)(\d+)$', n)
    if m:
        k = int(m.group(3))
        if m.group(1) == 'wbc':
            k = 4 * k              # wbc_<st>0 / 1 serve PC halves 0-3 / 4-7
        return {'SW': ('SW', 'SE'), 'NW': ('NW', 'NE')}[m.group(2)][k >= 4]
    m = re.match(r'^ctl_(SW|NW)_p(\d+)$', n)
    if m:
        return {'SW': ('SW', 'SE'), 'NW': ('NW', 'NE')}[m.group(1)][int(m.group(2)) // 4 >= 4]
    m = re.match(r'^xq_(SW|NW)_p(\d)', n)
    if m:
        return {'SW': ('SW', 'SE'), 'NW': ('NW', 'NE')}[m.group(1)][int(m.group(2)) >= 2]
    return None


def graph_b(GA, keep_q=QS):
    G = copy.deepcopy(GA)
    nodes = G['nodes']
    for q in QS:
        if 'hc_eng' in nodes:
            e = dict(nodes['hc_eng']); e['id'] = f'hce_{q}'; e['quadrant'] = q; e['w'] = e['h'] = 1598.4
            e['area_mm2'] = round(1598.4 ** 2 / 1e6, 4); e['provenance'] = 'H-PLANSTUDY: quadrant HC engine (hc_eng slot / 4, replicated)'
            nodes[f'hce_{q}'] = e
    nodes.pop('hc_eng', None)
    out = []
    seen = set()
    for l in G['links']:
        l = dict(l)
        c = l['cls']
        s, d = l['src'], l['dst']
        if c in ('SM_X', 'SM_OUT', 'KV_DESC', 'HBM_VM', 'VM_HBM'):
            smside = d if (d.startswith('sm_') or d.startswith('pc_')) else s
            q = quad_of_sm(smside)
            core = s if smside == d else d
            core2 = re.sub(r'_(SW|SE|NW|NE)(\d*)$', lambda m: f'_{q}{m.group(2)}', core)
            if smside == d:
                s = core2
            else:
                d = core2
        if c == 'HC_ENG':
            q = (s if s != 'hc_eng' else d).split('_')[1]
            s, d = (f'hce_{q}', d) if s == 'hc_eng' else (s, f'hce_{q}')
        if c == 'COLL_EP' and d == 'ep_S1':
            pass
        l['src'], l['dst'] = s, d
        l['id'] = f'{s}>{d}:{c}'
        key = l['id']
        if key in seen:
            continue
        seen.add(key)
        out.append(l)
    G['links'] = out
    # keep only the quadrants of this die
    dropq = [q for q in QS if q not in keep_q]
    if dropq:
        def dead(n):
            m = re.search(r'_(SW|SE|NW|NE)(\d*|_p\d.*)$', n)
            if n in ('lk_N0', 'lk_N2', 'ep_N0', 'ep_N2'):
                return True
            return bool(m) and m.group(1) in dropq
        G['nodes'] = {k: v for k, v in G['nodes'].items() if not dead(k)}
        G['links'] = [l for l in G['links'] if l['src'] in G['nodes'] and l['dst'] in G['nodes']]
    G['structural'] = list(G.get('structural', [])) + ['H-PLANSTUDY: per-quadrant services; SM-side classes re-wired to the SM quadrant core']
    return G


def write_plan(d, P, G, H, tag, W=W_DIE):
    d.mkdir(parents=True, exist_ok=True)
    Pg = {k: v for k, v in P.items()}
    (d / 'compact.P.json').write_text(json.dumps(Pg, indent=1))
    (d / 'compact.graph.json').write_text(json.dumps(G, indent=1))
    placed = sum(r['w'] * r['h'] for r in P.values()) / 1e6
    met = dict(die_um=[W, round(H, 2)], die_mm2=round(W * H / 1e6, 2), placed_mm2=round(placed, 2), density=round(placed / (W * H / 1e6), 3))
    (d / 'compact.metrics.json').write_text(json.dumps(met, indent=1))
    r = subprocess.run([sys.executable, str(ROOT / 'tools/hbm_die_v15/v6_eval.py'), str(d), '--tag', tag], capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise SystemExit(r.stderr[-3000:])
    ev = json.loads((d / 'eval.json').read_text())
    sys.path.insert(0, str(ROOT / 'tools'))
    import hbm_globalfp as F
    F.W_DIE, F.H_DIE = W, H
    m = F.score(G, {k: v for k, v in P.items() if k in G['nodes']}, json.loads((ROOT / 'results/arch/hbm_globalfp_1015/noatt/ref_sm.json').read_text()))
    import pin_cut
    pins = json.loads((d / 'pins' / f'{tag}.pins.json').read_text()); lanes = json.loads((d / 'lanes.json').read_text())
    cut_np, _ = pin_cut.run(pins, {k: v for k, v in P.items() if not k.startswith('phy_')}, lanes, full=True)
    over = cut_np.pop('over_060')
    ev['cut_phy_unmasked'] = dict(cut_np, rule='pin_cut with full supply over the PHY rows (the cut_window_who.py measure; '
                                  'removes the PHY-row supply-mask artefact noted in d4f_a2p_fullcore/README pc637)', over_060=over[:20])
    ev['sum_bits_mm'] = round(m['sum_bits_mm'], 1)
    ev['graph_relay_flops'] = m['relay_flops']
    ev['overlaps'] = m['overlaps']; ev['outside'] = m['outside']
    ev['by_class_longest_um'] = {k: v['longest_um'] for k, v in m['by_class'].items()}
    (d / 'eval.json').write_text(json.dumps(ev, indent=1))
    return ev


# ----------------------------------------------------------------------------------------------- bus model
def gapxy(r, p):
    """closest point of rect r to point p"""
    return (min(max(p[0], r['x']), r['x'] + r['w']), min(max(p[1], r['y']), r['y'] + r['h']))


def manh(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def mst_len(root, pts):
    """rectilinear Prim MST length from root over pts"""
    done = [root]; todo = list(pts); L = 0.0
    while todo:
        best = None
        for i, p in enumerate(todo):
            d = min(manh(p, q) for q in done)
            if best is None or d < best[0]:
                best = (d, i)
        L += best[0]; done.append(todo.pop(best[1]))
    return L


def inst_quadrant(n):
    if DIEWIDE.match(n) or n in ('hc_eng', 'hcx_root'):
        return None
    if n.startswith(('leaf_', 'pleaf_', 'idxs_', 'idxq_', 'hce_')):
        return n.split('_')[1]
    q = quad_of_sm(n)
    if q:
        return q
    m = re.match(r'^xl_(SW|SE|NW|NE)_', n)
    if m:
        return m.group(1)
    m = re.search(r'_(SW|SE|NW|NE)(\d*|_b\d+)$', n) or re.match(r'^(?:lg|fl|fr|fs|hc|su|sfu|vmb)_(SW|SE|NW|NE)', n)
    if m:
        return m.group(1)
    return None


# die-wide drivers / sinks (R2: tree from the root, one fat lane per quadrant)
DIEWIDE = re.compile(r'^(host_|su_prog$|col_su$|col_idx$|hb_argmax$|hb_ckgen$|vm_status|hb_idx__(selector|link)$|tkm|epcal_|smw_)')
# functions that cross quadrants by design (R3), kept as cross-quadrant lanes (class XQ)
def cross_by_function(drv, sink):
    if drv.startswith('hb_coll_') and sink.startswith('hb_coll_'):
        return True
    if drv.startswith('hb_vms_') and sink.startswith('hb_vms_'):
        return True
    if drv.startswith('hb_idx__scorer') and sink.startswith(('hb_idx__selector', 'hb_idx__ctl')):
        return True
    if drv.startswith('hc_') and sink == 'hc_eng':
        return False
    return False


PHYSIDE = re.compile(r'^(sm_|svg_|cp_svg_|xc_|ctl_|vmks_|vmdel_|wbc_|wbk_|refcfg_|sfault_|pc_|phy_|xq_|xl_|smw_|vmm_|fs_)')


def stack_level(n):
    """stack (PHY side) services shared by the two quadrants of one stack: they keep both quadrants' sinks"""
    return bool(re.match(r'^(phy_|wbk_|refcfg_|sfault_|ctl_|vmks_|wbc_|fs_)', n))


KNOWN = set()          # instance names of the (a) die (filled by main)
NEW_REPLICAS = set()   # replicas plan (b)/(c) must add (not in (a)): placed at the quadrant core
CREATABLE = re.compile(r'^(hb_quant_|xl_|vmdel_|vmm_)')


def replica(n, q):
    """the same master's instance in quadrant q (None when the function has no replica there)"""
    if quad_of_sm(n):
        return None
    m = re.match(r'^xl_(SW|SE|NW|NE)_(.*)$', n)
    if m:
        r = f'xl_{q}_{m.group(2)}'
        if r not in KNOWN:
            NEW_REPLICAS.add(r)
        return r
    m = re.match(r'^(.*)_(SW|SE|NW|NE)(\d*)$', n)
    if m:
        r = f'{m.group(1)}_{q}{m.group(3)}'
        if r in KNOWN:
            return r
        if CREATABLE.match(n):
            NEW_REPLICAS.add(r); return r
    return None


def a_hosts(PA, inst):
    """(a) host plan block of every instance: the smallest compact.P rect containing its centre, else the nearest;
    an instance of quadrant q is hosted only by a block of q (or a quadrant-less block)"""
    host = {}
    for n, v in inst.items():
        cx, cy = v['x'] + v['w'] / 2, v['y'] + v['h'] / 2
        q = inst_quadrant(n)
        PQ = {b: r for b, r in PA.items() if inst_quadrant(b) == q} if q else PA
        PQ = PQ or PA
        hs = [b for b, r in PQ.items() if r['x'] <= cx <= r['x'] + r['w'] and r['y'] <= cy <= r['y'] + r['h']]
        if hs:
            host[n] = min(hs, key=lambda b: PA[b]['w'] * PA[b]['h'])
        else:
            dd = lambda r: max(r['x'] - cx, 0, cx - r['x'] - r['w']) + max(r['y'] - cy, 0, cy - r['y'] - r['h'])
            host[n] = min(PQ, key=lambda b: dd(PQ[b]))
    return host


def centre(r):
    return (r['x'] + r['w'] / 2, r['y'] + r['h'] / 2)


def positions(plan, P, PA, inst, host, keep_q):
    """instance -> (rect) in plan (a) / (b) / (c).  Instances move with their (a) host block (relative position kept);
    die-level instances get an explicit home in the strip; replicas/leaves are added."""
    pos = {}
    if plan == 'a':
        for n, v in inst.items():
            pos[n] = dict(x=v['x'], y=v['y'], w=v['w'], h=v['h'])
        pos['host_cp_landing'] = pos['host_cp_packet'] = dict(pos['host_cp_ingress'])
        return pos
    home = {'host_': 'host_cp', 'hb_ckgen': 'idx_op', 'su_prog': 'idx_op', 'col_su': 'idx_op', 'vm_status': 'idx_op',
            'col_idx': 'idx_ctl', 'hb_argmax': 'idx_op', 'hb_idx__ctl': 'idx_ctl', 'hb_idx__selector': 'idx_sel',
            'hb_idx__link': 'idx_link', 'hb_idx__query': 'idx_q', 'hb_idx__operands': 'idx_q', 'tkm_SW': 'tkm_SW',
            'smw_': 'host_cp'}
    epq = dict(SW='ep_S0', SE='ep_S3', NW='ep_N0', NE='ep_N2')
    for n, v in inst.items():
        q = inst_quadrant(n)
        if q is not None and q not in keep_q:
            continue
        h = next((b for k, b in home.items() if n.startswith(k)), None)
        if n.startswith('epcal_'):
            h = epq.get(n.split('_')[1])
        if h is not None and h in P:
            r = P[h]; pos[n] = dict(x=r['x'] + r['w'] / 2 - v['w'] / 2, y=r['y'] + r['h'] / 2 - v['h'] / 2, w=v['w'], h=v['h']); continue
        hb = host.get(n)
        if hb not in P:
            hb2 = f'sucore_{q}' if q else 'idx_op'
            r = P[hb2]; pos[n] = dict(x=r['x'] + r['w'] / 2 - v['w'] / 2, y=r['y'] + r['h'] / 2 - v['h'] / 2, w=v['w'], h=v['h'])
            continue
        ra, rb = PA[hb], P[hb]
        cx, cy = v['x'] + v['w'] / 2, v['y'] + v['h'] / 2
        fx = (cx - ra['x']) / ra['w']; fy = (cy - ra['y']) / ra['h']
        # relative position kept (clamped into the block); mirror flips inside one block are below plan resolution
        fx, fy = min(max(fx, 0.0), 1.0), min(max(fy, 0.0), 1.0)
        pos[n] = dict(x=rb['x'] + fx * rb['w'] - v['w'] / 2, y=rb['y'] + fy * rb['h'] - v['h'] / 2, w=v['w'], h=v['h'])
    for q in keep_q:                    # replicas / leaves of plan (b)/(c)
        for k, blk in ((f'idxs_{q}', f'idxs_{q}'), (f'idxq_{q}', f'idxq_{q}'), (f'hce_{q}', f'hce_{q}'), (f'leaf_{q}', f'sucore_{q}'),
                       (f'pleaf_{q}', f'pleaf_{q}')):
            r = P[blk]; pos[k] = dict(r)
    pos['hcx_root'] = dict(P['idx_op']); pos['hc_eng'] = dict(P['idx_op'])
    for n in ('host_cp_landing', 'host_cp_packet'):
        pos[n] = dict(P['host_cp'])
    for n in NEW_REPLICAS:
        q = n.split('_')[1] if n.startswith('xl_') else re.sub(r'\d+$', '', n.split('_')[-1])
        r = P[f'pleaf_{q}'] if n.startswith('xl_') else (P[f'vmh_{q}'] if n.startswith(('vmdel_', 'vmm_')) else P[f'sucore_{q}'])
        pos[n] = dict(x=r['x'], y=r['y'], w=min(r['w'], 300), h=min(r['h'], 300))
    return pos


def rewire(rows, keep_q):
    """bus list of plan (b) / (c) from the run9 rows (module doc R1-R3, plus the IDX / HC per-quadrant rules)."""
    out = collections.OrderedDict()

    cur = {}

    def add(drv, port, sinks, bits, dom, xq, cls):
        key = (drv, port, xq)
        e = out.setdefault(key, dict(driver=drv, port=port, sinks=[], bits=bits, domain=dom, xq=xq, cls=cls, cfg=cur.get('cfg', False)))
        e['bits'] = max(e['bits'], bits)
        for x in sinks:
            if x not in e['sinks']:
                e['sinks'].append(x)

    def tree(drv, port, sinks, bits, dom):
        byq = collections.defaultdict(list)
        for x in sinks:
            byq[inst_quadrant(x)].append(x)
        for q, ss in byq.items():
            if q is None:
                add(drv, port, ss, bits, dom, False, 'die')
            else:          # root -> quadrant leaf on a fat cross-quadrant lane, then the local fan-out
                ph = [x for x in ss if PHYSIDE.match(x)]; co = [x for x in ss if not PHYSIDE.match(x)]
                for lf, grp in ((f'pleaf_{q}', ph), (f'leaf_{q}', co)):
                    if grp:
                        add(drv, port + f'@{lf}', [lf], bits, dom, True, 'tree')
                        add(lf, f'{drv}.{port}', grp, bits, dom, False, 'tree_local')
    sc = lambda x: x.startswith('hb_idx__scorer')
    for r in rows:
        drv, port = r['driver'].split('.', 1)
        if drv.startswith(('rfr_', 'sfr_')) or any(x.startswith(('rfr_', 'sfr_')) for x in r['sinks']):
            continue           # SU RF_RELAY chains between quarter cores: replaced by the per-quadrant RF + the scalar tree
        dq = inst_quadrant(drv)
        if dq is not None and dq not in keep_q:
            continue
        cur['cfg'] = r['cls'] == 'cfg_no_pad'
        bits, dom = r['bits'], r['domain']
        sinks = [x for x in r['sinks'] if inst_quadrant(x) in keep_q or inst_quadrant(x) is None]
        if not sinks:
            continue
        # ---- IDX: scorer quarter + local ctl/query per quadrant; merge (selector / link / tkm) central
        if sc(drv):
            for q in keep_q:
                add(f'idxs_{q}', port, [x for x in sinks], bits, dom, True, 'xq_idx_merge')
            continue
        if drv in ('hb_idx__ctl', 'hb_idx__query', 'col_idx'):
            rest = [x for x in sinks if not sc(x) and not x.startswith('vmb_')]
            for x in sinks:
                if x.startswith('vmb_'):
                    add(f'idxq_{inst_quadrant(x)}', port, [x], bits, dom, False, 'local')
            if any(sc(x) for x in sinks):
                if drv == 'col_idx':
                    tree(drv, port, [f'idxs_{q}' for q in keep_q], bits, dom)
                else:
                    for q in keep_q:
                        add(f'idxq_{q}', port, [f'idxs_{q}'], bits, dom, False, 'local')
            if rest:
                add(drv, port, rest, bits, dom, False, 'die')
            continue
        if any(sc(x) for x in sinks):        # svg -> scorer: the quadrant's own scorer quarter
            for x in sinks:
                add(drv, port, [f'idxs_{dq}' if sc(x) else x], bits, dom, False, 'local')
            continue
        # ---- HC: quadrant engine; the cross-quadrant part is a partial-sum tree (hce_q <-> hcx_root)
        if drv == 'hc_eng' or 'hc_eng' in sinks:
            if drv == 'hc_eng':
                for x in sinks:
                    q = inst_quadrant(x)
                    add(f'hce_{q}' if q else drv, port, [x], bits, dom, False, 'local')
            else:
                add(drv, port, [(f'hce_{dq}' if dq else 'hcx_root') if x == 'hc_eng' else x for x in sinks], bits, dom, False, 'local')
            continue
        if DIEWIDE.match(drv) or dq is None:
            tree(drv, port, sinks, bits, dom)
            continue
        for x in sinks:
            sq = inst_quadrant(x)
            if sq is None and not stack_level(x):      # quadrant -> die-level sink: up the tree through the leaf
                lf = f'pleaf_{dq}' if PHYSIDE.match(drv) else f'leaf_{dq}'
                add(drv, port, [lf], bits, dom, False, 'tree_local')
                e = out.setdefault((lf, f'up:{x}', True), dict(driver=lf, port=f'up:{x}', sinks=[x], bits=0,
                                                               domain=dom, xq=True, cls='tree_up', cfg=cur.get('cfg', False)))
                e['bits'] += bits
                continue
            if sq is not None and sq != dq and quad_of_sm(drv) and not stack_level(x) and replica(x, dq):
                add(drv, port, [replica(x, dq)], bits, dom, False, 'local')    # SM/PC side -> its own quadrant core
                continue
            if sq is None or sq == dq or stack_level(drv) or stack_level(x):
                add(drv, port, [x], bits, dom, False, 'local')
            elif cross_by_function(drv, x):
                add(drv, port, [x], bits, dom, True, 'xq')
            else:
                rep = replica(drv, sq)
                if rep:
                    add(rep, port, [x], bits, dom, False, 'local')
                else:
                    add(drv, port, [x], bits, dom, True, 'xq_norep')
    for q in keep_q:                         # SU scalar tree (RMS / softmax scalars) replacing the RF relays: 64 b each way
        add(f'leaf_{q}', 'sux_part', ['hcx_root'], 64, 'serial', True, 'xq_su')
        add('hcx_root', f'sux_bcast@{q}', [f'leaf_{q}'], 64, 'serial', True, 'xq_su')
    for q in keep_q:                         # HC cross-quadrant partial sums (estimate: 1,024 b each way)
        add(f'hce_{q}', 'hcx_part', ['hcx_root'], 1024, 'stream', True, 'xq_hc')
        add('hcx_root', f'hcx_bcast@{q}', [f'hce_{q}'], 1024, 'stream', True, 'xq_hc')
    return list(out.values())


def rows_as_buses(rows):
    return [dict(driver=r['driver'].split('.', 1)[0], port=r['driver'].split('.', 1)[1], sinks=list(r['sinks']),
                 bits=r['bits'], domain=r['domain'], xq=False, cls=r['cls'], cfg=r['cls'] == 'cfg_no_pad') for r in rows
            if not r['driver'].startswith(('rfr_', 'sfr_'))]


def lane_of(b, fork):
    return 136 if fork else (624 if b['bits'] >= 200 else 48)


def bus_metrics(buses, pos, grid=None):
    """route every bus on the plan: driver point = the driver rect point closest to its sinks' centroid; sink point =
    the sink rect point closest to the driver point; L = Manhattan; stages = ceil(L / 380); fork = rectilinear MST."""
    dom_fork = collections.defaultdict(int); dom_all = collections.defaultdict(int)
    T = dict(bit_mm=0.0, station_bits=0.0, tiles=0, buses=0, fork_buses=0, xq_bits=0, xq_buses=0, missing=set(),
             longest=[0.0, None, 0], over_reach_bits=0, per_cls=collections.Counter(), deep=[])
    for b in buses:
        if b['driver'] not in pos:
            T['missing'].add(b['driver']); continue
        rs = [pos[x] for x in b['sinks'] if x in pos]
        T['missing'].update(x for x in b['sinks'] if x not in pos)
        if not rs:
            continue
        cen = (sum(centre(r)[0] for r in rs) / len(rs), sum(centre(r)[1] for r in rs) / len(rs))
        d = gapxy(pos[b['driver']], cen)
        pts = [gapxy(r, d) for r in rs]
        Ls = [manh(d, p) for p in pts]
        fork = len(pts) > 1
        tree = mst_len(d, pts) if fork else Ls[0]
        depth = max(math.ceil(L / SPACING) for L in Ls) if max(Ls) > REACH else 0
        depth = math.ceil(depth * (KAPPA_FORK if len(pts) > 1 else KAPPA_P2P))
        stn = math.ceil(tree / SPACING) if tree > REACH else 0
        lanes = math.ceil(b['bits'] / lane_of(b, fork))
        T['buses'] += 1; T['fork_buses'] += fork
        if grid:
            W_, H_, nx, ny = grid
            reg = lambda pt: (min(nx - 1, int(pt[0] / (W_ / nx))), min(ny - 1, int(pt[1] / (H_ / ny))))
            rd = reg(d)
            for pt in pts:
                rs_ = reg(pt)
                if rs_ != rd:
                    T.setdefault('_pairs', {})[tuple(sorted((rd, rs_)))] = max(abs(rd[0] - rs_[0]), abs(rd[1] - rs_[1]))
        T['bit_mm'] += b['bits'] * tree / 1000
        T['station_bits'] += b['bits'] * stn
        T['tiles'] += lanes * stn
        T['per_cls'][b['cls']] += lanes * stn
        if b.get('cfg'):
            dom_fork['cfg'] = max(dom_fork['cfg'], depth)
        elif fork or b['xq']:
            dom_fork[b['domain']] = max(dom_fork[b['domain']], depth)
        dom_all[b['domain']] = max(dom_all[b['domain']], depth)
        T['deep'].append((depth, b['domain'], f"{b['driver']}.{b['port'][:40]}", len(pts), b['bits'], bool(b['xq'])))
        if max(Ls) > T['longest'][0]:
            T['longest'] = [round(max(Ls)), f"{b['driver']}.{b['port'][:60]}", depth]
        if b['xq']:
            T['xq_bits'] += b['bits']; T['xq_buses'] += 1
    T['missing'] = sorted(T['missing'])
    if grid:
        pr = T.pop('_pairs', {})
        T['clock_regions'] = dict(grid=f'{grid[2]} x {grid[3]} (box {grid[0] / grid[2] / 1000:.2f} x {grid[1] / grid[3] / 1000:.2f} mm)',
                                  regions=grid[2] * grid[3], communicating_pairs=len(pr),
                                  neighbour_pairs=sum(1 for v in pr.values() if v == 1),
                                  pairs_over_1_region=sum(1 for v in pr.values() if v > 1),
                                  max_pair_distance_regions=max(pr.values()) if pr else 0)
    T['equal_age_depth'] = dict(dom_fork)
    T['max_depth'] = dict(dom_all)
    T['deep'] = sorted(T['deep'], reverse=True)[:12]
    T['per_cls'] = dict(T['per_cls'])
    T['bit_mm'] = round(T['bit_mm']); T['station_bits'] = int(T['station_bits'])
    return T


def run9_measured(rows, layer):
    tiles = sum(layer['tile_categories'].values())
    lng = max(((sum((s.get('hop_um') or 0) for s in r['stations']), r['driver'], r['depth']) for r in rows), key=lambda z: z[2])
    return dict(relay_tiles=tiles, buses=layer['buses'], equal_age_depth=layer['equal_age_max_depth_by_domain'],
                hops_over_405=len(layer['hops_over_reach']), deepest_bus=dict(driver=lng[1], depth=lng[2]),
                station_bits=int(sum(r['bits'] * len(r['stations']) for r in rows)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    PA = json.loads((A_DIR / 'compact.P.json').read_text())
    GA = json.loads((A_DIR / 'compact.graph.json').read_text())
    res = {}
    # ---------------- plan graphs
    import shutil
    da = out / 'plan_a'; da.mkdir(exist_ok=True)
    for f in ('compact.P.json', 'compact.graph.json', 'compact.metrics.json'):
        shutil.copy(A_DIR / f, da / f)
    HA = json.loads((A_DIR / 'compact.metrics.json').read_text())['die_um'][1]
    res['a'] = dict(plan=write_plan(da, PA, GA, HA, 'a', W_A), H=HA)
    for side in ('inner', 'outer'):
        PB, HB = plan_b(PA, side=side)
        res[f'b_{side}'] = dict(plan=write_plan(out / f'plan_b_{side}', PB, graph_b(GA), HB, f'b_{side}'), H=HB)
        PC, HC = plan_b(PA, halves=('S',), side=side)
        res[f'c_{side}'] = dict(plan=write_plan(out / f'plan_c_{side}', PC, graph_b(GA, keep_q=('SW', 'SE')), HC, f'c_{side}'), H=HC)
    # ---------------- bus model
    rows = json.loads(RUN9.read_text())['rows']
    layer = json.loads(RUN9_LAYER.read_text())
    inst = {k: v for k, v in json.loads(RUN8_MANIFEST.read_text())['placement'].items() if not v['m'].startswith(('hbfd_rly', 'hfd_stn'))}
    host = a_hosts(PA, inst)
    KNOWN.update(inst)
    buses = dict(a=rows_as_buses(rows))
    plans = dict(a=PA)
    for side in ('inner', 'outer'):
        plans[f'b_{side}'] = plan_b(PA, side=side)[0]; plans[f'c_{side}'] = plan_b(PA, halves=('S',), side=side)[0]
    bus = {}
    for t, P in plans.items():
        kq = ('SW', 'SE') if t.startswith('c') else QS
        NEW_REPLICAS.clear()
        bl = buses['a'] if t == 'a' else rewire(rows, kq)
        pos = positions('a' if t == 'a' else 'b', P, PA, inst, host, kq)
        Wd, Hd = (W_A, json.loads((A_DIR / 'compact.metrics.json').read_text())['die_um'][1]) if t == 'a' else (W_DIE, plan_b(PA, halves=('S',) if t.startswith('c') else ('S', 'N'))[1])
        bus[t] = bus_metrics(bl, pos, (Wd, Hd, math.ceil(Wd / 4000), math.ceil(Hd / 4000)))
        bus[t]['n_bus_rows'] = len(bl)
        bus[t]['new_replicas'] = sorted(NEW_REPLICAS)
        bus[t]['xq_list'] = sorted({(b['cls'], b['driver'], b['port'][:50], b['bits']) for b in bl if b['xq']})
    bus['a_measured_run9'] = run9_measured(rows, layer)
    k = bus['a_measured_run9']['relay_tiles'] / bus['a']['tiles']
    for t in plans:
        bus[t]['relay_tiles_calibrated'] = int(round(bus[t]['tiles'] * k))
    bus['_calibration'] = dict(tiles_factor=round(k, 4), rule='model tiles x (run9 measured tiles / model tiles on plan a)')
    for t in res:
        res[t]['bus'] = bus.get(t)
    res['a']['bus_measured_run9'] = bus['a_measured_run9']
    res['_bus_calibration'] = bus['_calibration']
    (out / 'plans.json').write_text(json.dumps({k: v for k, v in res.items()}, indent=1))
    for t, v in res.items():
        if t.startswith('_'):
            continue
        b = v['bus']
        print(t, v['plan']['die_mm2'], 'cut', v['plan']['cut_phy_unmasked']['worst_v']['ratio'], v['plan']['cut_phy_unmasked']['worst_h']['ratio'],
              '| bus tiles', b['tiles'], b['relay_tiles_calibrated'], 'bitmm', b['bit_mm'], 'stbits', b['station_bits'], 'depth', b['equal_age_depth'],
              'longest', b['longest'], 'xq', b['xq_buses'], b['xq_bits'], 'missing', b['missing'][:8])


if __name__ == '__main__':
    main()
