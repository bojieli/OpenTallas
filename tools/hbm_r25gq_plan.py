#!/usr/bin/env python3
"""hbm-phys-1010 [fp] 2026-10-10: R25GQ (owner Option A) re-floorplan record -- density, channel track use, relay-stage
lint, projected peak power and the floorplan / congestion pictures.

R25GQ is a PLACEMENT plan (tools/hbm_accel_die_fp.py build_r25gq): its die nets are not rebuilt until the dependent
blocks are re-routed.  The wiring model therefore carries the R25GPH logical nets over:

  * logical nets: the R25GPH network-probe buses (tools/hbm_accel_die_fp.py, same commit), relay chains collapsed
    through their waypoints into terminal sets (clock / reset / strap trees excluded); each set is spanned by a
    rectilinear MST, an MST edge carries the larger of its two terminals' widest bus (broadcast trunks and gather
    trunks keep their width; leaves keep theirs);
  * R25GQ terminal map: every instance keeps its name; the 64 -> 32 attention tiles map base row r onto row r // 2
    (the pair's nets land on the surviving tile, so the bits are kept -- conservative); SU / SFU / index nets keep their
    R25GPH widths (the quarter faces are unchanged, conservative for 512 lanes / 36 score lanes);
  * Option A additions: the VM lane groups (hgi-1010/b ot_hgi_vm_lanearb: read ~8.8 kb + write ~9 kb a group): the W
    group through SU -> SFU -> HC (SW quarter), the E group through the abutted VM | CP | quant; ATT record broadcast
    1,250 b CP -> each quadrant's root tile; CP <-> MTP ports (120 b) + f_mtp 517 / t_mtp 197; the loader host port
    widening (HOST_H_HGI); the IKS issuer nets hgi_iks_<st> (IDX -> svc e, 128 b + fclk);
  * router: a congestion-negotiated grid router (100 um cells, 5 rounds, use reported on 300-um box sums; a bus wider
    than 2,100 b is routed as <= 2,100-b bundles, which spread over its face as the real pins do) over the placed blocks; a cell's track capacity
    is its free (unblocked) area x the GRT-derated tracks per um of the R25GP die run (M4-M9, GRT-0053), the same
    capacity basis as the R25GP budget model; a block cell costs 20 x a free cell (routes over blocks are counted and
    reported, a relay cannot sit there);
  * the SAME model on R25GPH is the calibration row (the budget's centre-to-centre strip model is in
    results/arch/r25gp_area_wiring_budget_20261010).

Grades: geometry = generator plan (measured outlines); channels = ESTIMATE (model, no die GRT); power = PROJECTION.

    python3 tools/hbm_r25gq_plan.py --out results/arch/r25gq_refloorplan_20261010
"""
import argparse, json, math, subprocess, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra, minimum_spanning_tree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_accel_die_fp as F  # noqa: E402

CELL = 100.0
V_DER = 0.7033 / 0.048 + 0.8531 / 0.064 + 0.85 / 0.080      # derated vertical tracks / um (M5, M7, M9; R25GP die GRT)
H_DER = 0.7065 / 0.048 + 0.8525 / 0.064 + 0.8499 / 0.080    # derated horizontal tracks / um (M4, M6, M8)
SKIP = ('clock', 'reset', 'strap', 'phy_dfi')      # phy_dfi: PHY <-> svc by abutment
BLOCK_COST = 20.0
TARGET = 0.55
BUNDLE = 2100       # bits per routed bundle (a 2,068-b x trunk stays one bundle)
VMW = 8800 + 9000  # one lane group: read ~8.8 kb + write ~9 kb (hgi-1010/b, ot_hgi_vm_lanearb ace618cd8)
OPTION_A = [('vm_lgW_0', 'hub_vm_lanes', VMW, ['hb_hgi_vm', 'hb_su_SW']),      # W group through SU -> SFU -> HC
            ('vm_lgW_1', 'hub_vm_lanes', VMW, ['hb_su_SW', 'hb_sfu_SW']),
            ('vm_lgW_2', 'hub_vm_lanes', VMW, ['hb_sfu_SW', 'hb_hc_SW']),
            ('vm_lgE_0', 'hub_vm_lanes', VMW, ['hb_hgi_vm', 'hb_cmdproc']),     # E group: VM | CP | quant abut
            ('vm_lgE_1', 'hub_vm_lanes', VMW, ['hb_cmdproc', 'hb_quant']),
            ('cp_mtp_ports', 'control', 120, ['hb_cmdproc', 'hb_mtp']),
            ('cp_mtp_f_mtp', 'control', 517, ['hb_mtp', 'hb_cmdproc']),
            ('cp_mtp_t_mtp', 'control', 197, ['hb_cmdproc', 'hb_mtp']),
            # loader host port h: exact HOST_H_HGI 406 / 381 (ot_hfd_loader_hgi host-facing ports) = R25GPH 256 / 256
            # + 150 / + 125, to the host interface, pipelined
            ('loader_h_widen', 'host', 150 + 125, ['hb_loader', 'lk_host'])] + \
           [(f'att_rec_{q}', 'att_record', 1250, ['hb_cmdproc', f'at_{q}_00_lo']) for q in ('SW', 'SE', 'NW', 'NE')] + \
           [(f'hgi_iks_{q}', 'expert_req', 129, ['hb_hgi_idx', f'svc_{q}_s3']) for q in ('SW', 'SE', 'NW', 'NE')]


def logical_nets(base):
    """R25GPH buses -> [(name, cls, {terminal: widest incident bits})] with waypoint chains collapsed."""
    kind = {i.name: i.kind for i in base['insts']}
    par = {}

    def f(a):
        while par.setdefault(a, a) != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for bid, cls, bits, eps in base['buses']:
        if cls.startswith(SKIP):
            continue
        ws = [e[0] for e in eps if kind.get(e[0]) == 'waypoint']
        for w in ws[1:]:
            par[f(w)] = f(ws[0])
    comp = defaultdict(lambda: dict(t=defaultdict(int), cls=defaultdict(int), name=None))
    for bid, cls, bits, eps in base['buses']:
        if cls.startswith(SKIP):
            continue
        ws = [e[0] for e in eps if kind.get(e[0]) == 'waypoint']
        key = f(ws[0]) if ws else ('bus', bid)
        c = comp[key]
        c['name'] = c['name'] or bid
        c['cls'][cls] += bits
        for e in eps:
            if kind.get(e[0]) != 'waypoint' and e[0] in kind:
                c['t'][e[0]] = max(c['t'][e[0]], bits)
    out = []
    for c in comp.values():
        if len(c['t']) >= 2:
            out.append((c['name'], max(c['cls'], key=c['cls'].get), dict(c['t'])))
    return out


class Grid:
    def __init__(self, m):
        g = m['geo']
        self.W, self.H = g['W'], g['H']
        self.nx, self.ny = math.ceil(self.W / CELL), math.ceil(self.H / CELL)
        f = 10      # 10-um raster for the free fraction
        occ = np.zeros((self.ny * f, self.nx * f), bool)
        self.inst = {}
        for it in m['insts']:
            if it.kind == 'waypoint':
                continue
            x0, y0, x1, y1 = it.box()
            occ[int(y0 / CELL * f):int(math.ceil(y1 / CELL * f)), int(x0 / CELL * f):int(math.ceil(x1 / CELL * f))] = True
            self.inst[it.name] = it
        self.free = 1.0 - occ.reshape(self.ny, f, self.nx, f).mean(axis=(1, 3))
        self.blocked = self.free < 0.2
        self.hcap = np.maximum(self.free, 0.0) * CELL * H_DER
        self.vcap = np.maximum(self.free, 0.0) * CELL * V_DER
        self.N = self.nx * self.ny

    def idx(self, i, j):
        return j * self.nx + i

    def ring(self, name):
        it = self.inst[name]
        x0, y0, x1, y1 = it.box()
        i0, i1 = max(int(x0 // CELL) - 1, 0), min(int(math.ceil(x1 / CELL)), self.nx - 1)
        j0, j1 = max(int(y0 // CELL) - 1, 0), min(int(math.ceil(y1 / CELL)), self.ny - 1)
        cells = []
        for i in range(i0, i1 + 1):
            for j in (j0, j1):
                if not self.blocked[j, i]:
                    cells.append(self.idx(i, j))
        for j in range(j0, j1 + 1):
            for i in (i0, i1):
                if not self.blocked[j, i]:
                    cells.append(self.idx(i, j))
        if not cells:       # fully enclosed (abutted spine stacks): the block's own centre cell
            cells = [self.idx(min(int((x0 + x1) / 2 // CELL), self.nx - 1), min(int((y0 + y1) / 2 // CELL), self.ny - 1))]
        return sorted(set(cells))

    def graph(self, cost):
        c = cost.ravel()
        ii, jj = np.meshgrid(np.arange(self.nx), np.arange(self.ny))
        a = (jj * self.nx + ii)
        r = [a[:, :-1].ravel(), a[:-1, :].ravel()]
        s = [a[:, 1:].ravel(), a[1:, :].ravel()]
        rows = np.concatenate(r + s)
        cols = np.concatenate(s + r)
        w = (c[rows] + c[cols]) / 2 * CELL
        return coo_matrix((w, (rows, cols)), shape=(self.N, self.N)).tocsr()


def route(m, nets, rounds=3):
    G = Grid(m)
    rings = {}

    def ring(n):
        if n not in rings:
            rings[n] = G.ring(n)
        return rings[n]
    edges = []
    for name, cls, t in nets:
        ts = [n for n in t if n in G.inst]
        if len(ts) < 2:
            continue
        cs = [((G.inst[n].x + G.inst[n].w / 2), (G.inst[n].y + G.inst[n].h / 2)) for n in ts]
        D = np.array([[abs(a[0] - b[0]) + abs(a[1] - b[1]) + 1e-3 for b in cs] for a in cs])
        T = minimum_spanning_tree(D).tocoo()
        for a, b in zip(T.row, T.col):
            A_, B_ = G.inst[ts[a]].box(), G.inst[ts[b]].box()
            if max(A_[0] - B_[2], B_[0] - A_[2], A_[1] - B_[3], B_[1] - A_[3]) <= 2.0:
                continue        # abutted blocks connect pin-to-pin (no channel)
            bits = max(t[ts[a]], t[ts[b]])
            nb = math.ceil(bits / BUNDLE)       # a wide bus spreads over its face: routed as <= BUNDLE-bit bundles
            for k in range(nb):
                edges.append((name if nb == 1 else f'{name}#{k}', cls, bits / nb, ts[a], ts[b]))
    hist = np.zeros((G.ny, G.nx))
    paths = None
    for rnd in range(rounds):
        hu = np.zeros((G.ny, G.nx))
        vu = np.zeros((G.ny, G.nx))
        paths = []

        def present():     # present congestion (PathFinder): rebuilt every 25 edges and between the bundles of one bus
            u = np.maximum(np.divide(hu / 2, G.hcap, out=np.zeros_like(hu), where=G.hcap > 0),
                           np.divide(vu / 2, G.vcap, out=np.zeros_like(vu), where=G.vcap > 0))
            return G.graph(1.0 + BLOCK_COST * G.blocked + hist + 3.0 * np.clip(u - TARGET, 0, 4.0))
        A = present()
        for e_, (name, cls, bits, a, b) in enumerate(edges):
            if e_ % 25 == 0 or '#' in name:
                A = present()
            src, dst = ring(a), ring(b)
            d, pred, srcs = dijkstra(A, indices=src, min_only=True, return_predecessors=True)
            k = min(dst, key=lambda x: d[x])
            p = [k]
            while pred[p[-1]] >= 0:
                p.append(pred[p[-1]])
            p = p[::-1]
            paths.append((name, cls, bits, a, b, p))
            for u, v in zip(p, p[1:]):
                ju, iu = divmod(u, G.nx)
                jv, iv = divmod(v, G.nx)
                arr = hu if ju == jv else vu
                arr[ju, iu] += bits
                arr[jv, iv] += bits
        util = np.maximum(np.divide(hu / 2, G.hcap, out=np.zeros_like(hu), where=G.hcap > 0),
                          np.divide(vu / 2, G.vcap, out=np.zeros_like(vu), where=G.vcap > 0))
        util[G.blocked] = 0.0
        hist += 4.0 * np.clip(util - TARGET, 0, None)
    # reported use: 3 x 3-cell (300 um) box sums of use over capacity -- a 100-um cell straddling a block edge keeps only
    # its free fraction of tracks, so single cells overstate (raster artifact); the channel rows use band sums
    from scipy.ndimage import uniform_filter
    bs = lambda a: uniform_filter(a, size=3, mode='constant')
    h2, v2 = hu / 2, vu / 2
    util_s = np.maximum(np.divide(bs(h2), bs(G.hcap), out=np.zeros_like(h2), where=bs(G.hcap) > 0.2 * CELL * H_DER),
                        np.divide(bs(v2), bs(G.vcap), out=np.zeros_like(v2), where=bs(G.vcap) > 0.2 * CELL * V_DER))
    util_s[G.blocked] = 0.0
    return G, paths, h2, v2, util_s


def path_stats(G, paths):
    """per edge: routed length, relay stages at 504 um, longest run over block cells (a relay cannot sit there)."""
    rows = []
    for name, cls, bits, a, b, p in paths:
        L = (len(p) - 1) * CELL
        run = best = 0
        for u in p[1:-1]:
            ju, iu = divmod(u, G.nx)
            if G.blocked[ju, iu] and not any(G.inst[n].box()[0] <= (iu + .5) * CELL <= G.inst[n].box()[2] and
                                             G.inst[n].box()[1] <= (ju + .5) * CELL <= G.inst[n].box()[3] for n in (a, b)):
                run += CELL
                best = max(best, run)
            else:
                run = 0
        rows.append(dict(net=name, cls=cls, bits=round(bits, 1), a=a, b=b, length_um=L, stages=max(1, math.ceil(L / F.SS_REACH_UM)),
                         over_block_um=best))
    return rows


def channels(G, hu, vu, rects):
    """per named channel rect: worst cross-section use (horizontal channel: sum of horizontal use over the band's rows
    at each column / the band's horizontal capacity; vertical analogous)."""
    out = {}
    for name, (kind, x0, y0, x1, y1) in rects.items():
        i0, i1 = int(x0 // CELL), int(math.ceil(x1 / CELL))
        j0, j1 = int(y0 // CELL), int(math.ceil(y1 / CELL))
        if kind == 'h':
            u = hu[j0:j1, i0:i1].sum(axis=0)
            c = G.hcap[j0:j1, i0:i1].sum(axis=0)
        else:
            u = vu[j0:j1, i0:i1].sum(axis=1)
            c = G.vcap[j0:j1, i0:i1].sum(axis=1)
        r = np.divide(u, c, out=np.zeros_like(u), where=c > 1)
        k = int(np.argmax(r))
        out[name] = dict(kind='horizontal' if kind == 'h' else 'vertical', rect_um=[round(v, 1) for v in (x0, y0, x1, y1)],
                         width_um=round((y1 - y0) if kind == 'h' else (x1 - x0), 1), max_use=round(float(r[k]), 3),
                         p90_use=round(float(np.percentile(r[c > 1], 90)) if (c > 1).any() else 0.0, 3),
                         max_bits=int(u[k]), at_um=round(((i0 + k) if kind == 'h' else (j0 + k)) * CELL + CELL / 2, 1))
    return out


def channel_rects(m, q):
    """named channels: q = True for R25GQ, False for the R25GPH calibration row."""
    I = {i.name: i for i in m['insts']}
    sm = lambda n: I[n]
    r = {}
    for st, s0 in (('SW', 0), ('SE', 8)):
        a, b, c = sm(f'sm{s0}'), sm(f'sm{s0 + 3}'), sm(f'sm{s0 + 6}')
        xs = sorted([sm(f'sm{s0 + k}').x for k in range(8)])
        x0, x1 = xs[0], xs[-1] + a.w
        r[f'{st}_SM_row_ch01'] = ('h', x0, a.y + a.h, x1, b.y)
        r[f'{st}_SM_row_ch12'] = ('h', x0, b.y + b.h, x1, c.y)
        hub0 = min(i.y for i in m['insts'] if i.kind in ('hub', 'attn_tile') and i.y > c.y and (i.x < 15000) == (st == 'SW'))
        r[f'{st}_SM_hub_edge_ch'] = ('h', x0, c.y + c.h, x1, hub0)
    a = sm('sm2')
    idx = I['idx_score_SW']
    sv = I['svc_SW_s0']
    r['SW_svc_gap'] = ('h', I['sm0'].x, sv.y + sv.h, I['sm2'].x + I['sm2'].w, I['sm0'].y)
    r['SW_grp_E_strip'] = ('v', a.x + a.w, a.y, idx.x, sm('sm6').y + sm('sm6').h)
    for k, (l_, r_) in enumerate(((sm('sm0'), sm('sm1')), (sm('sm1'), sm('sm2'))), 1):
        r[f'SW_col_ch{k}'] = ('v', l_.x + l_.w, l_.y, r_.x, sm('sm6').y + sm('sm6').h)
    sp = I['hb_cmdproc']
    vm = I['hb_hgi_vm']
    su = I['hb_su_SW']
    sp_lo = min(i.y for i in m['insts'] if i.kind == 'spine')
    sp_hi = max(i.y + i.h for i in m['insts'] if i.kind == 'spine')
    r['W_spine_ch'] = ('v', su.x + su.w, sp_lo, sp.x, sp_hi)
    r['E_spine_ch'] = ('v', sp.x + sp.w, sp_lo, I['hb_su_SE'].x, sp_hi)
    r['W_spine_ch_at_VM_face'] = ('h', su.x + su.w, vm.y, sp.x, vm.y + vm.h)
    hub = [i for i in m['insts'] if i.kind in ('hub', 'attn_tile') and 6000 < i.y < 19500]
    ylo_n = min(i.y for i in hub if i.y > 12641)
    yhi_s = max(i.y + i.h for i in hub if i.y < 12641)
    r['hub_equator'] = ('h', m['geo']['x0'], yhi_s, m['geo']['W'] - m['geo']['x0'], ylo_n)
    return r


BUDGET = ROOT / 'results/arch/r25gp_area_wiring_budget_20261010'


def strip_model(mq, rects):
    """The R25GP budget's strip model (results/arch/r25gp_area_wiring_budget_20261010: max L-route cross-section bits per
    channel on the R25GPH netlist WITH its relay waypoints, i.e. where the generator puts the chains) carried to R25GQ:
    the same channel loads over the R25GQ channel widths, + the Option A lane groups where they cross a channel.  This is
    the conservative row (the chains are re-placed in the same channels when the blocks are re-routed)."""
    x = json.loads((BUDGET / 'xsec_r25gph.json').read_text())['channels']
    I = {i.name: i for i in mq['insts']}
    w = lambda k: (rects[k][4] - rects[k][2]) if rects[k][0] == 'h' else (rects[k][3] - rects[k][1])
    vm = I['hb_hgi_vm']
    sfu, hc = I['hb_sfu_SW'], I['hb_hc_SW']
    rows = dict(
        SM_row_ch01=(x['SM_row_ch_520']['max_bits'], w('SW_SM_row_ch01'), H_DER, 'SM_row_ch_520', 0),
        SM_row_ch12=(x['SM_row_ch_259']['max_bits'], w('SW_SM_row_ch12'), H_DER, 'SM_row_ch_259', 0),
        SM_hub_edge_ch=(x['hub_S_edge_ch(SM N row->hub)']['max_bits'], w('SW_SM_hub_edge_ch'), H_DER,
                        'hub_S_edge_ch(SM N row->hub)', 0),
        SW_grp_E_strip=(x['SW_grp_E']['max_bits'], w('SW_grp_E_strip'), V_DER, 'SW_grp_E', 0),
        SW_col_ch1=(x['SW_col_ch1']['max_bits'], x['SW_col_ch1']['width_um'], V_DER, 'SW_col_ch1', 0),
        SW_col_ch2=(x['SW_col_ch2']['max_bits'], x['SW_col_ch2']['width_um'], V_DER, 'SW_col_ch2', 0),
        W_spine_ch=(x['W_spine_ch']['max_bits'], w('W_spine_ch'), V_DER, 'W_spine_ch', 0),
        E_spine_ch=(x['E_spine_ch']['max_bits'], w('E_spine_ch'), V_DER, 'E_spine_ch', 0),
        # group A lanes leave the HGI VM's W face across the W spine channel: the VM face window carries them
        W_spine_ch_at_VM_face=(1836, vm.h, H_DER, 'budget item 1 (existing 1,836 b at the VM face)', VMW),
        # group A hop SFU -> HC across the hub column gap: over the SFU's height window
        SFU_HC_column_gap=(0, sfu.h, H_DER, 'new', VMW))
    out = {}
    for k, (bits, width, der, src, add) in rows.items():
        out[k] = dict(base_bits=bits, added_bits=add, width_um=round(width, 1), use=round((bits + add) / (width * der), 3),
                      r25gp_use=x[src]['use'] if src in x else None, source=src)
    vm_per = 2 * (vm.w + vm.h)
    out['HGI_VM_pins'] = dict(base_bits=13907, added_bits=2 * VMW, perimeter_um=round(vm_per, 1),
                              use=round((13907 + 2 * VMW) / (vm_per / 0.048), 3), r25gp_use=0.135,
                              source='budget item 1 pin rule (2 tracks a bit on 2 pin layers: perimeter / 0.048 bits)')
    return out


def ds_att_check():
    """Attention 64 -> 32 tiles against DeepSeek AR + MTP (owner condition), from committed model records only."""
    cal = json.loads((ROOT / 'tools/hgi_sim/calibration.json').read_text())
    tim = json.loads((ROOT / 'results/arch/hgi_sim_20261009/ds_native_timing_1M.json').read_text())['result']['S0']
    ar = json.loads((ROOT / 'results/arch/token_path_20261009/hbm_ds.json').read_text())['totals']
    mtp = json.loads((ROOT / 'results/arch/token_path_20261009/hbm_ds_mtp.json').read_text())['totals']
    att = lambda t: next(c['cycles'] for c in t['by_class'] if c['cls'] == 'attn')
    bw = cal['hbm']['bytes_per_cycle']['value']
    ingest = 32 * 1024 / 8          # 32 tiles x the ld_w 1,024-b KV line a cycle (ATTN_LD)
    worst = lambda t: dict(attn_cycles=att(t), step_cycles=t['cycles'], tok_s=t['tok_s'],
                           tok_s_if_attn_doubles=round(t['tok_s'] * t['cycles'] / (t['cycles'] + att(t)), 1),
                           delta_pct=round(-100 * att(t) / (t['cycles'] + att(t)), 2))
    return dict(
        hgi_sim=dict(source='results/arch/hgi_sim_20261009/ds_native_timing_1M.json (S0) + tools/hgi_sim/timing.py ATT',
                     rule='ATT priced HBM-stream-bound: first access + bytes / %.1f B/cycle + 225 fixed; the tile count is '
                          'not a model parameter' % bw,
                     att_busy_cycles=tim['per_unit']['ATT']['busy'], token_cycles=tim['total_cycles'], tok_s=tim['tok_s'],
                     tile_ingest_32_B_per_cycle=ingest, hbm_B_per_cycle=bw, stream_bound_at_32=ingest >= bw),
        token_path_ar=dict(source='results/arch/token_path_20261009/hbm_ds.json', **worst(ar)),
        token_path_mtp=dict(source='results/arch/token_path_20261009/hbm_ds_mtp.json (P = 6 verify, tau %.3f)' % mtp['tau'],
                            **worst(mtp)),
        verdict='AR: meets (stream-bound: 32 x 128 B/cycle = 4,096 >= 3,166.7 B/cycle HBM, unchanged). MTP (P = 6): the '
                'token-path record runs a 16-row tile job per position (1,350 cycles a layer at 64 tiles); if 32 tiles '
                'double the rows a tile walks, the attention class doubles: bound shown in tok_s_if_attn_doubles '
                '(no change if the 8 KV stripes a stack map 1:1 onto its 8 tiles and the pairs split heads). '
                'Not re-simulated: hgi-sim has no tile-count or MTP-attention term.')


def density(m):
    W, H = m['geo']['W'], m['geo']['H']
    area = lambda it: it.w * it.h
    ins = [i for i in m['insts'] if i.kind != 'waypoint']
    out = dict(die_mm2=round(W * H / 1e6, 2), placed_mm2=round(sum(map(area, ins)) / 1e6, 2))
    out['placed_density'] = round(out['placed_mm2'] / out['die_mm2'], 4)
    core = [i for i in ins if i.kind not in ('phy', 'link', 'serdes_slab', 'host_slab')]
    out['placed_mm2_excl_phy_serdes_host'] = round(sum(map(area, core)) / 1e6, 2)
    regs = {}
    for rg in m['regions']:
        x0, y0, x1, y1 = rg['rect']
        A = (x1 - x0) * (y1 - y0)
        s = 0.0
        for it in ins:
            a0, b0, a1, b1 = it.box()
            s += max(0, min(a1, x1) - max(a0, x0)) * max(0, min(b1, y1) - max(b0, y0))
        regs[rg['name']] = dict(rect_um=[round(v, 1) for v in rg['rect']], area_mm2=round(A / 1e6, 2),
                                density=round(s / A, 4) if A else None)
    out['regions'] = regs
    by = defaultdict(float)
    for it in ins:
        by[it.kind] += area(it) / 1e6
    out['by_kind_mm2'] = {k: round(v, 2) for k, v in sorted(by.items())}
    return out


def power(out_dir):
    ev = json.loads((ROOT / 'results/physical/die_evidence_20261009/hbm_r25gp_power.json').read_text())
    scale = {'hfd_attn_half_lo': 0.5, 'hfd_attn_half_hi': 0.5, 'hfd_su': 0.5, 'hfd_sfu': 0.5,
             'hfd_idx_score_native_grid': 36 / 64}
    for mst, s in scale.items():
        v = ev['masters'][mst]
        for k in list((v.get('w') or {})):
            v['w'][k] = v['w'][k] * s
        if v['kind'] == 'attn_tile':
            v['n'] = int(round(v['n'] * s))          # w_each unchanged: half the tiles
        else:
            for k in list((v.get('w_each') or {})):
                v['w_each'][k] = v['w_each'][k] * s
        if v.get('leak_w'):
            v['leak_w'] *= s
        v['assumed_w'] = v.get('assumed_w', 0.0) * s
        v['r25gq_scale'] = s
    a20 = sum((v.get('w') or {}).get('a20', v.get('assumed_w', 0.0)) or 0.0 for v in ev['masters'].values())
    wires_cls = ev['die_wires']['by_class']
    att_w = sum(c.get('w_at_activity_1', 0) for k, c in wires_cls.items() if k.startswith('attn'))
    wires = ev['total']['a20_split']['die_wires_w']
    relay = ev['relay_stations']['w']['a20']
    ev['note_r25gq'] = ('R25GQ right-sized: attention halves n 64 -> 32, SU / SFU x 0.5, index score grids x 36/64 on the '
                        'measured R25GP per-master a20 / a00; die wires and relays kept at R25GP (conservative)')
    evp = Path(out_dir) / 'power_evidence_r25gq.json'
    evp.write_text(json.dumps(ev, indent=1) + '\n')
    pp = Path(out_dir) / 'power_projection.json'
    r = subprocess.run([sys.executable, str(ROOT / 'tools/hbm_cg_power_projection.py'), '--evidence', str(evp),
                        '--measured', str(ROOT / 'results/arch/redesign_hbm_cg_20261009/measured_gated_floors.json'),
                        '--out', str(pp)], capture_output=True, text=True)
    proj = json.loads(pp.read_text()) if pp.exists() else {}
    peak = a20 + relay + wires
    return dict(grade='PROJECTION (measured R25GP per-master power, right-sized counts; no R25GQ power run)',
                peak_in_phase_a20_w=round(peak, 1), r25gp_peak_in_phase_a20_w=ev['total']['peak_in_phase_a20_w'],
                masters_a20_w=round(a20, 1), relay_w=relay, die_wires_w=wires,
                die_wires_attn_classes_w_at_activity_1=round(att_w, 2), cooling_limit_w=ev['cooling_limit_w'],
                peak_passes_cooling=peak <= ev['cooling_limit_w'],
                duty_mix_projection=dict(rc=r.returncode, verdict=proj.get('verdict'),
                                         workloads={k: v['projection_w'] for k, v in proj.get('workloads', {}).items()}))


def pictures(m, G, util, out, tag, rects):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    W, H = m['geo']['W'], m['geo']['H']
    col = dict(sm='#9ecae1', svc='#fdd0a2', phy='#756bb1', hub='#74c476', spine='#31a354', attn_tile='#fd8d3c',
               link='#fee391', serdes_slab='#fff7bc', host_slab='#fec44f')
    for kind in ('floorplan', 'congestion'):
        fig, ax = plt.subplots(figsize=(15, 15 * H / W))
        if kind == 'congestion':
            u = np.ma.masked_where(G.blocked, util)
            im = ax.imshow(u, origin='lower', extent=[0, G.nx * CELL, 0, G.ny * CELL], cmap='inferno_r', vmin=0, vmax=1.2,
                           interpolation='nearest')
            fig.colorbar(im, ax=ax, fraction=0.025, label='track use (model, derated tracks); target <= 0.55')
        for it in m['insts']:
            if it.kind == 'waypoint':
                continue
            ax.add_patch(Rectangle((it.x, it.y), it.w, it.h, fill=(kind == 'floorplan'), lw=0.3,
                                   fc=col.get(it.kind, '#ccc'), ec='#333'))
            if kind == 'floorplan' and (it.kind in ('hub', 'spine', 'sm') or it.name.endswith('_00_lo')) and it.w > 150:
                ax.text(it.x + it.w / 2, it.y + it.h / 2, it.name.replace('hb_', ''), fontsize=3.2 if it.kind != 'sm' else 5,
                        ha='center', va='center')
        if kind == 'congestion':
            for nm, (k, x0, y0, x1, y1) in rects.items():
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.6, ec='#1f78b4', ls='--'))
        ax.set_xlim(0, W)
        ax.set_ylim(0, H)
        ax.set_aspect('equal')
        ax.set_title(f'{tag} {kind} ({W:,.0f} x {H:,.0f} um)' + (' -- ESTIMATE, carried-over nets' if kind == 'congestion' else ''))
        fig.savefig(out / f'{tag.lower()}_{kind}.png', dpi=130, bbox_inches='tight')
        if kind == 'floorplan':
            fig.savefig(out / f'{tag.lower()}_{kind}.svg', bbox_inches='tight')
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--rounds', type=int, default=5)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mq = F.build(F.variant_arg('r25gq'))
    base = mq['base']
    nets0 = logical_nets(base)
    rmap = mq['r25gq_map']
    names = {i.name for i in mq['insts']}
    netsq = []
    for name, cls, t in nets0:
        t2 = {}
        for n, b in t.items():
            n2 = rmap.get(n, n)
            if n2 in names:
                t2[n2] = max(t2.get(n2, 0), b)
        if len(t2) >= 2:
            netsq.append((name, cls, t2))
    for name, cls, bits, ts in OPTION_A:
        netsq.append((name, cls, {t: bits for t in ts}))
    res = {}
    for tag, m, nets in (('R25GPH', base, nets0), ('R25GQ', mq, netsq)):
        G, paths, hu, vu, util = route(m, nets, a.rounds)
        rects = channel_rects(m, tag == 'R25GQ')
        ch = channels(G, hu, vu, rects)
        ps = path_stats(G, paths)
        free = ~G.blocked
        u = util[free]
        cls_st = defaultdict(lambda: dict(max_stages=0, max_length_um=0.0, relay_bit_stages=0))
        for p in ps:
            c = cls_st[p['cls']]
            c['max_stages'] = max(c['max_stages'], p['stages'])
            c['max_length_um'] = max(c['max_length_um'], p['length_um'])
            c['relay_bit_stages'] += p['bits'] * (p['stages'] - 1)
        res[tag] = dict(nets=len(nets), routed_edges=len(paths), channels=ch,
                        free_cells_over=dict(p55=round(float((u > 0.55).mean()), 4), p80=round(float((u > 0.8).mean()), 4),
                                             p100=round(float((u > 1.0).mean()), 4)),
                        worst_cells=[dict(x_um=round((k % G.nx + .5) * CELL), y_um=round((k // G.nx + .5) * CELL),
                                          use=round(float(util.ravel()[k]), 3))
                                     for k in np.argsort(util.ravel())[::-1][:12]],
                        over_block=dict(edges=sum(1 for p in ps if p['over_block_um'] > 0),
                                        max_run_um=max(p['over_block_um'] for p in ps),
                                        runs_over_504um=[dict(net=p['net'], a=p['a'], b=p['b'], run_um=p['over_block_um'])
                                                         for p in ps if p['over_block_um'] > F.SS_REACH_UM][:20]),
                        stages_by_class={k: dict(v) for k, v in sorted(cls_st.items())},
                        relay_bit_stages=sum(p['bits'] * (p['stages'] - 1) for p in ps))
        pictures(m, G, util, out, tag, rects)
        res[tag]['density'] = density(m)
        if tag == 'R25GQ':
            res[tag]['strip_model'] = strip_model(m, rects)
    pw = power(out)
    plan = dict(schema='opentallas.r25gq-refloorplan.v1', date='2026-10-10', preset='r25gq',
                generator='tools/hbm_accel_die_fp.py build_r25gq (opt-in; other variants byte-identical)',
                base='r25gph (network probe, same commit)', die=dict(W=mq['geo']['W'], H=mq['geo']['H']),
                geo={k: v for k, v in mq['geo'].items()}, legality=F._legality(mq), notes=mq['notes'],
                variant={k: v for k, v in mq['variant'].items()},
                instances=[i.d() for i in mq['insts']], regions=mq['regions'],
                attention_map={k: v for k, v in rmap.items() if k.startswith('at_')})
    (out / 'floorplan.json').write_text(F.plan_json(plan) + '\n')
    F.write_def_floorplan(mq, out / 'floorplan.def')
    summary = dict(schema='opentallas.r25gq-refloorplan-summary.v1', grade=dict(
        geometry='generator plan (measured block outlines), legality checked', channels='ESTIMATE (grid-router model on '
        'carried-over R25GPH logical nets + Option A nets; no die GRT)', power='PROJECTION'),
        model=dict(cell_um=CELL, v_tracks_per_um=round(V_DER, 2), h_tracks_per_um=round(H_DER, 2), block_cost=BLOCK_COST,
                   rounds=a.rounds, option_a_nets=OPTION_A), wiring=res, power=pw, ds_attention_32=ds_att_check())
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, default=str) + '\n')
    for tag in res:
        print(tag, json.dumps(dict(density=res[tag]['density']['placed_density'],
                                   channels={k: v['max_use'] for k, v in res[tag]['channels'].items()},
                                   over=res[tag]['free_cells_over'], over_block=res[tag]['over_block']['max_run_um'],
                                   strip={k: v['use'] for k, v in res[tag].get('strip_model', {}).items()})))
    print('ds_att', json.dumps(summary['ds_attention_32']['token_path_ar']), json.dumps(summary['ds_attention_32']['token_path_mtp']))
    print('power', json.dumps({k: pw[k] for k in ('peak_in_phase_a20_w', 'r25gp_peak_in_phase_a20_w', 'cooling_limit_w')}),
          json.dumps(pw['duty_mix_projection']['workloads'])[:400])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
