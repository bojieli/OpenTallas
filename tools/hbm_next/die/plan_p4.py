#!/usr/bin/env python3
"""HBM-NEXT-DIE 10-19: P = 4 next-release HBM die floorplan, forked from the d4g GEN2 frame (COPIED, no GEN2 edits).

Frame input: physical/hbm_next/die/frame_d4g_copy/d4g_phy.compact.{P,graph}.json (verbatim copy of
results/arch/hbm_die_d4g/plan/d4g_phy at claude/hbm-next-1019 4f894f572).  Evaluator: the d4g plan tool chain
(tools/hbm_die_v15/plan_study_1017.write_plan -> v6_eval pins / lanes / sliding-window pin cut, hbm_globalfp bit-mm,
per-class stages at the 480-um lane rule), used read-only, so every number is on the d4g basis (reproduces 641.83 mm2,
cut 0.397/0.431, 0.797 M bit-mm, 7.035 stages_bw).

SM column at P = 4 (stand-in until SM4 publishes results/arch/hbm_next_1019/sm4/geometry.json):
  MTP-AREA measured +99.83 mm2 for 16 SMs = +6.24 mm2 per SM column (13.49 -> 19.73 mm2); the column stays a 4 x 4 grid
  of rp4 tiles (2 leaves each), every tile edge on the 43.2-um lattice: tile 457.92 x 1598.4 -> --tile-w x --tile-h
  (default 673.92 x 1684.8 = 1.135 mm2 >= 1.122 needed; aspect 2.5:1 vs 3.5:1 today); column = 4 tw + 108, 4 th + 561.6.
  x-only growth (717.12 x 1598.4) makes the SM row 26.66 mm > the 25.5-mm reticle short side: rejected by construction.

Plans:
  d4g     the frame as is (check of the evaluator)
  f4w     the frame GROWN: SM row widened to the P=4 columns, every band/strip block keeps its distance to the die centre
          line and its distance to the SM row (white space at the band edges, nothing re-packed)
  f4c     the frame RE-PACKED for the wider quadrant (proposed): per quadrant ONE band row of the 4 SU groups over the
          4 SMs, the 8 VM banks in a row directly on the SM row's inner face (SM_X / LG short), VM hub + quadrant core
          (SFU core/store, SU core, DMA back, HC client, IDX query) at the inner end beside the centre lane channel; COLL
          engines and HC engines move into the centre strip next to the SerDes endpoints / ring neighbours.
  --vmh inner|mid  VM hub at the quadrant core (inner) or between groups 2|3 (mid).
  --coll-x K  multiplies COLL_VM / COLL_RING / COLL_EP bits by K (COLL widened for xN payload; reserve until
              UNITS/CMTP publish the P = 4 collective BW).

    plan_p4.py --out results/arch/hbm_next_1019/die/plan [--plans d4g,f4w,f4c] [--vmh inner] [--coll-x 1]
"""
import argparse, copy, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v15'))
import plan_study_1017 as S  # noqa: E402

FRAME = ROOT / 'physical/hbm_next/die/frame_d4g_copy'
W0, H0 = 20200.0, 31773.52
LAT = 43.2
SM_W0, SM_H0 = 1939.68, 6955.2
# UNITS-IDXN (claude/hbm-next-1019@5bf6d2d50, units/idxn/README.md Area): 2 key replay buffers 0.486 + 3 selectors 0.331
# + issuer 0.007 mm2 cell+macro per die; plan outlines at fill 0.7
IDXN_KEY_MM2 = 0.486 / 0.7
IDXN_SEL_MM2 = (0.331 + 0.007) / 0.7
TW0, TH0 = 457.92, 1598.4
EDGE = 42.4
GAPS = (540.0, 100.0, 540.0)       # SW0|SW1, SW1|SW2, SW2|SW3 (xq pair stores sit in the 540 gaps)
CH = 400.0                         # centre lane channel (PC3|PC4 line)
RETICLE = (26000.0, 33000.0)
MARGIN = 500.0


def R(x, y, w, h, o='R0'):
    return dict(x=round(x, 3), y=round(y, 3), w=round(w, 3), h=round(h, 3), orient=o)


def sm_dims(tw, th):
    return round(4 * tw + (SM_W0 - 4 * TW0), 3), round(4 * th + (SM_H0 - 4 * TH0), 3)


def sm_row(P0, W, smw, smh, north, H):
    """SM row + xq pair stores + PHY/PC + IDX scorer quarters + config leaf of one half (S frame, then mirrored)."""
    st = 'NW' if north else 'SW'
    CX = W / 2
    out = {}
    xs = [0.0] * 8
    xs[3] = CX - CH / 2 - smw
    xs[2] = xs[3] - GAPS[2] - smw
    xs[1] = xs[2] - GAPS[1] - smw
    xs[0] = xs[1] - GAPS[0] - smw
    for i in range(4, 8):
        xs[i] = W - xs[7 - i] - smw
    y0 = 2056.0
    for i in range(8):
        out[f'sm_{st}{i}'] = R(xs[i], y0, smw, smh)
    top = y0 + smh
    top0 = y0 + SM_H0                  # d4g S SM top (inner edge) = 9011.2
    for p in range(4):
        L0 = P0[f'sm_SW{2 * p}']       # d4g left SM of the pair
        for k in ('eg', 'bd', 'bfq0', 'bfq1', 'bfq2', 'bfq3'):
            r = P0[f'xq_SW_p{p}_{k}']
            dx = r['x'] - (L0['x'] + L0['w'])
            out[f'xq_{st}_p{p}_{k}'] = R(xs[2 * p] + smw + dx, top - (top0 - r['y']), r['w'], r['h'])
    ph = P0['phy_SW']
    px = CX - 4499.2
    out[f'phy_{st}'] = R(px, ph['y'], ph['w'], ph['h'])
    for i in range(8):
        r = P0[f'pc_SW{i}']
        out[f'pc_{st}{i}'] = R(px + 2 + i * 1136.8, r['y'], r['w'], r['h'])
    qW, qE = ('NW', 'NE') if north else ('SW', 'SE')
    iw, ih = P0['idxs_SW']['w'], P0['idxs_SW']['h']
    out[f'idxs_{qW}'] = R(px - 60.0 - iw, 21.6, iw, ih)
    pcr = max(out[f'pc_{st}{i}']['x'] + out[f'pc_{st}{i}']['w'] for i in range(8))
    out[f'idxs_{qE}'] = R(max(px + ph['w'], pcr) + 60.0, 21.6, iw, ih)
    ly = top - (top0 - P0['pleaf_SW']['y'])
    out[f'pleaf_{qW}'] = R(CX - 200.0, ly, 400.0, 400.0)          # both config leaves INSIDE the 400-um centre channel
    out[f'pleaf_{qE}'] = R(CX - 200.0, ly - 460.0, 400.0, 400.0)  # (d4g overlapped the SM columns by 200 um)
    if north:
        out = {n: S.mirror_y(r, H) for n, r in out.items()}
        for n in out:
            if n.startswith('xq_'):
                out[n]['orient'] = 'MX'
    return out, top


def quadrant_core_c(P0, q, BY, W, vmh='inner', side=None, hc='quad', vm_dw=0.0, vm_dh=0.0, fused=0.0, idxn=False, fused_h=None):
    """F4-C quadrant band (W-quadrant S frame, x from the die W edge): row A = 8 VM banks on the SM row inner face,
    row B = 4 SU groups (SU slot + HC client + SFU group (+ quant)) over the 4 SMs, quadrant core at the inner end."""
    out = {}
    dims = lambda n: (P0[n]['w'], P0[n]['h'])
    CX = W / 2
    vw, vh = dims(f'vmb_{q}0')
    vw = round(vw + vm_dw, 3)               # VM growth (PROG 10-19 01:35): bank SRAM part widened by vm_dw
    vh = round(vh + vm_dh, 3)               # ... or made taller by vm_dh (one-column macro stack, 47-um pin ring kept)
    ga = 40.0
    order = (1, 0, 2, 3)               # su_0 (SU_CORE / SFU_CORE hub of the quadrant) second from the outer edge
    x = EDGE
    vmh_w, vmh_h = dims(f'vmh_{q}')
    rowB = BY + vh + 50.0
    for pos, g in enumerate(order):
        if vmh == 'mid' and pos == 2:
            out[f'vmh_{q}'] = R(x, BY, vmh_w, vmh_h); x += vmh_w + ga
        suw, suh = dims(f'su_{q}{g}')
        out[f'vmb_{q}{2 * g}'] = R(x, BY, vw, vh)
        out[f'vmb_{q}{2 * g + 1}'] = R(x + vw + 20.0, BY, vw, vh)
        out[f'su_{q}{g}'] = R(x, rowB, suw, suh)
        cx = x + suw + 40.0
        fy = rowB
        fh_ = fused_h or fused                 # lane outline fused (W) x fused_h (H); square when fused_h is not given
        if fused:                              # UNITS-FUSED hnx_fused_lane_1019 (x32 = one per VM bank, S face = its bank): the group's
            for k in range(2):                 # 2 lanes at the foot of the SFU/HC client column, next to the bank pair's inner corner
                out[f'fus_{q}{2 * g + k}'] = R(cx, rowB + k * (fh_ + 20.0), fused, fh_)
            fy = rowB + 2 * (fh_ + 20.0) + 40.0
        fw, fh = (side, side) if side else dims(f'sfu_{q}{g}'); out[f'sfu_{q}{g}'] = R(cx, fy, fw, fh)
        hw, hh = (side, side) if side else dims(f'hc_{q}{g}'); out[f'hc_{q}{g}'] = R(cx, fy + fh + 60.0, hw, hh)
        hw = max(hw, fused)                    # the column is as wide as its widest block (FUSED lanes may be wider than 259.2)
        if f'quant_{q}{g}' in P0:              # quantiser in the bank row, beside its bank pair (QUANT_VM)
            qw, qh = dims(f'quant_{q}{g}'); out[f'quant_{q}{g}'] = R(x + 2 * vw + 60.0, BY, qw, qh)
        x = cx + max(hw, fw) + ga
        x = max(x, out[f'vmb_{q}{2 * g + 1}']['x'] + vw + ga)
    if vmh == 'inner':
        out[f'vmh_{q}'] = R(x, BY, vmh_w, vmh_h); x += vmh_w + ga
    sw_, sh_ = dims(f'sfucore_{q}'); out[f'sfucore_{q}'] = R(x, BY, sw_, sh_)
    if hc == 'quad':
        out[f'hce_{q}'] = R(x, BY + sh_ + 60.0, 1598.4, 1598.4)   # quadrant HC engine over the SFU core (HC_ENG to hc_q)
        x += max(sw_, 1598.4) + ga
    else:                                                          # ONE HC engine (PROG 10-19 01:35): slot released
        x += sw_ + ga
    y = BY
    for n in ('dbk', 'sucore', 'sucx', 'hc', 'cij', 'idxq'):
        w_, h_ = dims(f'{n}_{q}')
        if n == 'idxq' and idxn:             # UNITS-IDXN: half a key replay buffer per quadrant scorer quarter beside the
            h_ = round(h_ + IDXN_KEY_MM2 / 4 * 1e6 / w_, 2)   # quadrant scorer (2 buffers / 4 quadrants, outline at fill 0.7)
        out[f'{n}_{q}'] = R(x, y, w_, h_); y += h_ + 60.0
    right = max(r['x'] + r['w'] for r in out.values())
    top = max(r['y'] + r['h'] for r in out.values())
    return out, right, top


def strip_c(P0, ys, W, sh, coll_d, idxn=False, fused_hub=0.0):
    """centre strip: SerDes pairs at the die edges; per side, from the centre line outward (greedy, no overlap, each
    item as close as possible to its preferred centre x): the SFU programme stores (over their SFU cores at the
    quadrant core), the COLL engine pair (S over N, stacked; preferred centre CX -/+ coll_d, swept: COLL_VM from the
    8 banks of the quadrant against COLL_RING / COLL_EP), IDX selector/link (W), top-k merge, IDX die control,
    host CP (E)."""
    out = {}
    CX = W / 2
    x = EDGE
    cy = lambda h: ys + (sh - h) / 2
    for k in ('S0', 'S1', 'N0'):
        out[f'lk_{k}'] = R(x, cy(600), 600, 600); out[f'ep_{k}'] = R(x + 650, cy(515.2), 434.72, 515.2); x += 1135
    wleft = x
    x = W - EDGE
    for k in ('S3', 'N2'):
        x -= 1085
        out[f'ep_{k}'] = R(x, cy(515.2), 434.72, 515.2); out[f'lk_{k}'] = R(x + 485, cy(600), 600, 600); x -= 50
    eright = x

    def coll_pair(qs, qn):
        a, b = P0[f'coll_{qs}'], P0[f'coll_{qn}']
        w = max(a['w'], b['w'])
        return w, lambda x0: {f'coll_{qs}': R(x0, ys + 25.0, a['w'], a['h']), f'coll_{qn}': R(x0, ys + sh - 25.0 - b['h'], b['w'], b['h'])}

    def one(name, w, h, dy=0.0):
        return w, lambda x0: {name: R(x0, cy(h) + dy, w, h)}

    def sfus(q):
        r = P0[f'sfus_{q}']; return one(f'sfus_{q}', r['w'], r['h'])
    idxw = (650, lambda x0: {'idx_sel': R(x0, cy(1000), 600, 450), 'idx_link': R(x0, cy(1000) + 500, 650, 500)})
    if idxn:                                      # UNITS-IDXN: the 3 added selectors + issuer beside idx_sel
        nh = 600.0; nw = round(IDXN_SEL_MM2 * 1e6 / nh, 2)
        idxw = (650 + 40 + nw, lambda x0: {'idx_sel': R(x0 + nw + 40, cy(1000), 600, 450), 'idx_link': R(x0 + nw + 40, cy(1000) + 500, 650, 500),
                                           'idx_nsel': R(x0, cy(1000), nw, nh)})
    idxc = (300, lambda x0: {'idx_ctl': R(x0, cy(708), 300, 260), 'idx_op': R(x0, cy(708) + 300, 216, 108), 'idx_q': R(x0, cy(708) + 448, 260, 260)})
    sides = {
        -1: [(0.6e3, sfus('SW')), (1.7e3, sfus('NW')), (coll_d, coll_pair('SW', 'NW')), (3.0e3, idxw)]
            + ([(0.0, one('fus_hub', fused_hub, fused_hub))] if fused_hub else []),
        +1: [(0.6e3, sfus('SE')), (1.7e3, sfus('NE')), (coll_d, coll_pair('SE', 'NE')), (3.5e3, one('tkm_SW', 3000, 1400)),
             (5.5e3, idxc), (6.5e3, one('host_cp', 1300, 700))]}
    for sg, items in sides.items():
        edge = 25.0                                  # distance from the centre line already used
        for pref, (w, mk) in sorted(items, key=lambda t: t[0]):
            d0 = max(edge + 50.0, pref - w / 2)
            x0 = CX - d0 - w if sg < 0 else CX + d0
            out.update(mk(x0)); edge = d0 + w
        lim = CX - wleft if sg < 0 else eright - CX
        assert edge + 50 < lim, ('strip overfull', sg, edge, lim)
    return out


def plan_f4c(P0, tw, th, vmh, coll_d=500.0, side=None, hc='quad', vm_dw=0.0, vm_dh=0.0, fused=0.0, idxn=False, fused_h=None, fused_hub=0.0):
    smw, smh = sm_dims(tw, th)
    W = round(2 * (EDGE + 4 * smw + sum(GAPS) + CH / 2), 2)
    BY = 2056.0 + smh + 200.0
    tops = []
    cores = {}
    for q in ('SW', 'NW'):
        c, right, top = quadrant_core_c(P0, q, BY, W, vmh, side, hc, vm_dw, vm_dh, fused, idxn, fused_h)
        assert right <= W / 2 - CH / 2 + 1e-6, (q, 'core overruns centre channel', right, W / 2 - CH / 2)
        cores[q] = c; tops.append(top)
    for q, src in (('SE', 'SW'), ('NE', 'NW')):
        c, right, top = quadrant_core_c(P0, q, BY, W, vmh, side, hc, vm_dw, vm_dh, fused, idxn, fused_h)
        cores[q] = {n: S.mirror_x(r, W) for n, r in c.items()}; tops.append(top)
    ys = max(tops) + 100.0
    SH = 1800.0
    H = round(2 * ys + SH, 2)
    P = {}
    s, _ = sm_row(P0, W, smw, smh, False, H); P.update(s)
    n, _ = sm_row(P0, W, smw, smh, True, H); P.update(n)
    for q in ('SW', 'SE'):
        P.update(cores[q])
    for q in ('NW', 'NE'):
        P.update({k: S.mirror_y(r, H) for k, r in cores[q].items()})
    P.update(strip_c(P0, ys, W, SH, coll_d, idxn, fused_hub))
    if hc == 'one':
        # the ONE split HC engine (GEN2 binds ot_hbm_hc_root_static + 4 qhub + 32 bank tiles, 5,223 x 1,953 um at the S-E PHY
        # corner): the S-E corner between idxs_SE and the die E edge, up to 40 um under the SM row
        x0 = P['idxs_SE']['x'] + P['idxs_SE']['w'] + 60.0
        P['hce_SE'] = R(x0, 21.6, W - EDGE - x0, 2056.0 - 40.0 - 21.6)
    return P, W, H


def plan_f4w(P0, tw, th):
    """frame grown, nothing re-packed"""
    smw, smh = sm_dims(tw, th)
    W = round(2 * (EDGE + 4 * smw + sum(GAPS) + CH / 2), 2)
    W = max(W, W0)
    dH = smh - SM_H0
    H = round(H0 + 2 * dH, 2)
    P = {}
    s, _ = sm_row(P0, W, smw, smh, False, H); P.update(s)
    n, _ = sm_row(P0, W, smw, smh, True, H); P.update(n)
    dx = (W - W0) / 2
    for k, r in P0.items():
        if k in P:
            continue
        r = dict(r)
        r['x'] = round(r['x'] + dx, 3)
        r['y'] = round(r['y'] + dH, 3)          # band + strip between the two grown SM rows
        P[k] = r
    return P, W, H


def graph_for(P, coll_x, hc='quad', coll_l5=False):
    G = _graph_for(P, coll_x, hc, coll_l5)
    if 'fus_hub' in P:
        fused_graph(G, P)
    return G


def _graph_for(P, coll_x, hc='quad', coll_l5=False):
    G = json.loads((FRAME / 'd4g_phy.compact.graph.json').read_text())
    for n, v in G['nodes'].items():
        if n in P:
            if abs(v['w'] - P[n]['w']) > 1e-6 or abs(v['h'] - P[n]['h']) > 1e-6:
                v['provenance'] = v.get('provenance', '') + f" | HBM-NEXT-DIE P=4: {P[n]['w']} x {P[n]['h']}"
            v['w'], v['h'] = P[n]['w'], P[n]['h']; v['area_mm2'] = round(v['w'] * v['h'] / 1e6, 4)
    if hc == 'one':                    # one engine: the 4 hc_q clients all link to hce_SE (bits per client unchanged)
        for q in ('SW', 'NW', 'NE'):
            G['nodes'].pop(f'hce_{q}', None)
        for l in G['links']:
            for e in ('src', 'dst'):
                if re.fullmatch(r'hce_(SW|NW|NE)', l[e]):
                    l[e] = 'hce_SE'; l['provenance'] = l.get('provenance', '') + ' | HBM-NEXT-DIE: ONE HC engine (hce_SE corner)'
            l['id'] = f"{l['src']}>{l['dst']}:{l['cls']}"
        G['nodes']['hce_SE']['provenance'] = 'HBM-NEXT-DIE 10-19: ONE split HC engine (GEN2 hc_eng, 250 cyc/row measured by UNITS) at the S-E PHY corner'
    if coll_l5:   # UNITS-COLL 10-19 (units/coll/README.md): L = 5 = per quadrant hb_coll -> cxdl_<q>4 586 b + cxdl -> SU 1,044 b
        for q in ('SW', 'NW', 'SE', 'NE'):    # quadrant-local, ring / EP unchanged; lane 4 lands on su_<q>0 (SU landing decision open)
            G['links'].append(dict(id=f'coll_{q}>su_{q}0:COLL_VM_L5', src=f'coll_{q}', dst=f'su_{q}0', cls='COLL_VM', bits=1630,
                                   bytes_per_token={'qwen': 0.0, 'ds': 0.0}, criticality=0.05, rule=None, fixed_return=False,
                                   provenance='HBM-NEXT-UNITS-COLL L=5 5th delivery lane: 586 + 1,044 b (cxdl_<q>4 on the path)'))
    if coll_x != 1:
        for l in G['links']:
            if l['cls'] in ('COLL_VM', 'COLL_RING', 'COLL_EP'):
                l['bits'] = int(round(l['bits'] * coll_x))
                l['provenance'] = l.get('provenance', '') + f' | HBM-NEXT-DIE: x{coll_x:g} COLL payload reserve (P=4)'
    G['structural'] = list(G.get('structural', [])) + ['HBM-NEXT-DIE 10-19: P=4 SM column stand-in; COLL x%g' % coll_x]
    return G


# UNITS-FUSED ot_hnx_fused_lane ports (rtl/hbm_next/fused/ot_hnx_fused_eng.sv): VM bank rq 17 + rr 257 + wq 273 = 547 b (S face);
# top side dn 140 + r 33 (down) + up 268 = 441 b (N face).  COORD 10-19 0kl: lane beside its bank, the csum is a TREE over
# neighbour hops (no star into the hub), the top's own logic (job decode, scalar prologue, heap, divc, rsqrt) in a small hub tile.
FUSED_VM_BITS, FUSED_TREE_BITS = 547, 441


def fused_graph(G, P):
    """FUSED nodes + links: lane <-> own bank; per quadrant the tree (lane pair -> group node; groups g1->g0, g2->g3 (neighbour
    columns), g0 -> g3 (quadrant node = the innermost group, lane 6)); quadrant node -> fus_hub (centre strip)."""
    for n, r in P.items():
        if n.startswith('fus_'):
            G['nodes'][n] = dict(id=n, kind='FUSED', quadrant=n[4:6] if n != 'fus_hub' else None, w=r['w'], h=r['h'],
                                 area_mm2=round(r['w'] * r['h'] / 1e6, 4), area_src='measured' if n != 'fus_hub' else 'reserve', fixed=False,
                                 provenance='HBM-NEXT-UNITS-FUSED(-SRAM) lane n3: 852,881 cells ~104k um2 std + 2 x 128x256 SRAM'
                                 if n != 'fus_hub' else 'HBM-NEXT-DIE 10-19: ot_hnx_fused_top hub reserve (job decode, prologue, heap, divc, rsqrt)')
    def link(s, d, cls, bits, why):
        G['links'].append(dict(id=f'{s}>{d}:{cls}', src=s, dst=d, cls=cls, bits=bits, bytes_per_token={'qwen': 0.0, 'ds': 0.0},
                               criticality=0.05, rule=None, fixed_return=False, provenance=why))
    for q in ('SW', 'NW', 'SE', 'NE'):
        for i in range(8):
            link(f'fus_{q}{i}', f'vmb_{q}{i}', 'FUSED_VM', FUSED_VM_BITS, 'lane <-> own VM bank rq/rr/wq')
        for g in range(4):
            link(f'fus_{q}{2 * g + 1}', f'fus_{q}{2 * g}', 'FUSED_TREE', FUSED_TREE_BITS, 'tree level 1 (lane pair, stacked)')
        link(f'fus_{q}2', f'fus_{q}0', 'FUSED_TREE', FUSED_TREE_BITS, 'tree level 2 (g1 -> g0, neighbour columns)')
        link(f'fus_{q}4', f'fus_{q}6', 'FUSED_TREE', FUSED_TREE_BITS, 'tree level 2 (g2 -> g3, neighbour columns)')
        link(f'fus_{q}0', f'fus_{q}6', 'FUSED_TREE', FUSED_TREE_BITS, 'tree level 3 (quadrant node = innermost group)')
        if 'fus_hub' in P:
            link(f'fus_{q}6', 'fus_hub', 'FUSED_TREE', FUSED_TREE_BITS, 'quadrant node -> hub (level 4/5 + command broadcast)')


def checks(P, W, H):
    ov = []
    names = sorted(P)
    for i, a in enumerate(names):
        A = P[a]
        for b in names[i + 1:]:
            B = P[b]
            if A['x'] < B['x'] + B['w'] - 1e-3 and B['x'] < A['x'] + A['w'] - 1e-3 and A['y'] < B['y'] + B['h'] - 1e-3 and B['y'] < A['y'] + A['h'] - 1e-3:
                ov.append((a, b))
    outside = [n for n, r in P.items() if r['x'] < -1e-3 or r['y'] < -1e-3 or r['x'] + r['w'] > W + 1e-3 or r['y'] + r['h'] > H + 1e-3]
    short, long_ = sorted((W, H))
    ret = dict(short_margin_um=round(RETICLE[0] - short, 2), long_margin_um=round(RETICLE[1] - long_, 2), margin_req_um=MARGIN,
               ok=RETICLE[0] - short >= MARGIN and RETICLE[1] - long_ >= MARGIN)
    return ov, outside, ret


def sm_hbm_offsets(P):
    out = {}
    for st in ('SW', 'NW'):
        for i in range(8):
            s, p = P[f'sm_{st}{i}'], P[f'pc_{st}{i}']
            out[f'{st}{i}'] = round(abs((s['x'] + s['w'] / 2) - (p['x'] + p['w'] / 2)))
    return out


def flow_png(path, P, G, W, H, ev, tag):
    """flow PNG: blocks faded, every plan-graph link as its pin-to-pin L route, width ~ bits, colour = class family;
    the legend gives bits / bit-weighted stages / longest per class."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fam = {'SM_X': '#08519c', 'SM_OUT': '#6baed6', 'KV_DESC': '#6baed6', 'SM_HBM': '#e6550d', 'HBM_K': '#fd8d3c', 'HBM_VM': '#a63603',
           'VM_HBM': '#a63603', 'VM_HUB': '#31a354', 'VM_RING': '#006d2c', 'COLL_VM': '#756bb1', 'COLL_RING': '#d62728', 'COLL_EP': '#e377c2',
           'HC_CORE': '#8c6d31', 'HC_ENG': '#bd9e39', 'LG_SU': '#74c476', 'LG_SFU': '#74c476', 'LG_HC': '#74c476', 'SU_CORE': '#9e9ac8',
           'SFU_CORE': '#fb6a4a', 'QUANT_VM': '#bcbddc', 'EP_SERDES': '#969696'}
    fig, ax = plt.subplots(figsize=(7.2, 8.4), dpi=240)
    for n, r in P.items():
        ax.add_patch(Rectangle((r['x'] / 1000, r['y'] / 1000), r['w'] / 1000, r['h'] / 1000, fc='#f0f0f0', ec='#bbbbbb', lw=0.3))
    for l in G['links']:
        if l['src'] not in P or l['dst'] not in P:
            continue
        a, b = P[l['src']], P[l['dst']]
        x0, y0 = (a['x'] + a['w'] / 2) / 1000, (a['y'] + a['h'] / 2) / 1000
        x1, y1 = (b['x'] + b['w'] / 2) / 1000, (b['y'] + b['h'] / 2) / 1000
        ax.plot([x0, x0, x1], [y0, y1, y1], color=fam.get(l['cls'], '#444444'), lw=max(0.2, min(3.0, l['bits'] / 900)), alpha=0.6, solid_capstyle='butt')
    from matplotlib.lines import Line2D
    pc = ev['per_class']; lg = ev['by_class_longest_um']
    hs = [Line2D([0], [0], color=fam.get(c, '#444'), lw=2, label=f"{c} {pc[c]['bits']} b, {pc[c]['stages_bw']} st, {lg.get(c, 0) / 1000:.1f} mm")
          for c in sorted(pc, key=lambda c: -pc[c]['bits'])]
    ax.legend(handles=hs, fontsize=3.6, loc='upper right', framealpha=0.85)
    ax.add_patch(Rectangle((0, 0), W / 1000, H / 1000, fill=False, ec='k', lw=1.0))
    ax.add_patch(Rectangle(((W - RETICLE[0]) / 2000, (H - RETICLE[1]) / 2000), RETICLE[0] / 1000, RETICLE[1] / 1000, fill=False, ec='#888888', lw=0.6, ls=':'))
    ax.set_xlim(-0.8, 34.0); ax.set_ylim(-0.5, 33.5); ax.set_aspect('equal'); ax.tick_params(labelsize=5)
    ax.set_title(f"HBM-NEXT {tag} flows: {W/1000:.2f} x {H/1000:.2f} mm; bit-mm {ev['sum_bits_mm']/1e6:.3f} M; stages_bw {ev['stages_bw']}; "
                 f"cut {ev['cut_phy_unmasked']['worst_v']['ratio']}/{ev['cut_phy_unmasked']['worst_h']['ratio']} (dotted = 26 x 33 reticle)", fontsize=5.5)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--plans', default='d4g,f4w,f4c')
    ap.add_argument('--tile-w', type=float, default=TW0 + 5 * LAT)
    ap.add_argument('--tile-h', type=float, default=TH0 + 2 * LAT)
    ap.add_argument('--vmh', default='inner', choices=('inner', 'mid'))
    ap.add_argument('--coll-x', type=float, default=1.0)
    ap.add_argument('--coll-d', type=float, default=500.0, help='F4-C: preferred distance (um) of the COLL pair centre from the die centre line')
    ap.add_argument('--suffix', default='')
    ap.add_argument('--grp-side', type=float, default=None, help='F4-C: SU-group HC client / SFU group plan blocks at this square size '
                    '(GEN2 grant outlines are 216 x 216; the d4g plan blocks 500 x 500 / 500 x 800 are d4f-era placeholders)')
    ap.add_argument('--png', action='store_true')
    ap.add_argument('--coll-l5', action='store_true', help='COLL L = 5 as UNITS-COLL measured it (+1,630 b per quadrant, COLL_VM only)')
    ap.add_argument('--hc', default='quad', choices=('quad', 'one'), help='4 quadrant HC slots (reserve) or ONE engine at the S-E PHY corner')
    ap.add_argument('--vm-dh', type=float, default=0.0, help='VM bank growth in height: 412k words = 5 x 1024x256 macros stacked = +86.4; 524k (Engram ~490k) = 6 = +151.2')
    ap.add_argument('--vm-dw', type=float, default=0.0, help='VM bank growth: um added to every vmb_* width (412k words = 5 macros: 118.8)')
    ap.add_argument('--fused', type=float, default=0.0, help='UNITS-FUSED hnx_fused_lane_1019 square side (um), x32 = 2 per bank pair in row A '
                    '(README outline 259.2 = a guess until the gate prints std_area_um2)')
    ap.add_argument('--fused-h', type=float, default=None, help='FUSED lane height (um) when not square (lane = --fused x --fused-h)')
    ap.add_argument('--fused-hub', type=float, default=0.0, help='FUSED hub tile (ot_hnx_fused_top own logic) square side in the centre strip; '
                    'also adds the FUSED graph (lane<->bank, neighbour-hop tree, hub)')
    ap.add_argument('--idxn', action='store_true', help='UNITS-IDXN N-row adder: key buffers at the quadrant scorers + selectors at idx_sel')
    a = ap.parse_args()
    P0 = json.loads((FRAME / 'd4g_phy.compact.P.json').read_text())
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    need = SM_W0 * SM_H0 / 1e6 + 99.83 / 16
    smw, smh = sm_dims(a.tile_w, a.tile_h)
    res = {}
    for t in a.plans.split(','):
        if t == 'd4g':
            P, W, H = P0, W0, H0
        elif t == 'f4w':
            P, W, H = plan_f4w(P0, a.tile_w, a.tile_h)
        elif t == 'f4c':
            P, W, H = plan_f4c(P0, a.tile_w, a.tile_h, a.vmh, a.coll_d, a.grp_side, a.hc, a.vm_dw, a.vm_dh, a.fused, a.idxn, a.fused_h, a.fused_hub)
        tag = t + a.suffix
        ov, outside, ret = checks(P, W, H)
        G = graph_for(P, a.coll_x if t != 'd4g' else 1.0, a.hc if t == 'f4c' else 'quad', a.coll_l5 and t != 'd4g')
        ev = S.write_plan(out / tag, P, G, H, tag, W=W)
        cut = ev['cut_phy_unmasked']
        placed = sum(r['w'] * r['h'] for r in P.values()) / 1e6
        res[tag] = dict(die_um=[W, H], die_mm2=round(W * H / 1e6, 2), placed_mm2=round(placed, 2), density=round(placed / (W * H / 1e6), 3),
                        sm_column_um=[smw, smh] if t != 'd4g' else [SM_W0, SM_H0], sm_column_mm2_need=round(need, 3),
                        tile_um=[a.tile_w, a.tile_h] if t != 'd4g' else [TW0, TH0],
                        cut_v=cut['worst_v'], cut_h=cut['worst_h'], cut_over_060=cut['over_060'], graph_bit_mm=ev['sum_bits_mm'],
                        stages_bw=ev['stages_bw'], per_class=ev['per_class'], longest_class_um=ev['by_class_longest_um'],
                        relay_flops=ev['graph_relay_flops'], overlaps=len(ov), overlap_pairs=ov[:10], outside=outside, reticle=ret,
                        sm_hbm_offset_um=sm_hbm_offsets(P), vmh=a.vmh if t == 'f4c' else None, grp_side=a.grp_side if t == 'f4c' else None, coll_d=a.coll_d if t == 'f4c' else None, coll_x=a.coll_x if t != 'd4g' else 1.0,
                        hc=a.hc if t == 'f4c' else None, coll_l5=a.coll_l5, vm_dw=a.vm_dw if t == 'f4c' else None, vm_dh=a.vm_dh if t == 'f4c' else None, fused=a.fused if t == 'f4c' else None, fused_h=a.fused_h if t == 'f4c' else None, fused_hub=a.fused_hub if t == 'f4c' else None, idxn=a.idxn if t == 'f4c' else None,
                        hce_um=[P['hce_SE']['w'], P['hce_SE']['h']] if 'hce_SE' in P else None)
        r = res[tag]
        print(tag, f"{W/1000:.2f}x{H/1000:.2f}={r['die_mm2']} cut {cut['worst_v']['ratio']}/{cut['worst_h']['ratio']} bitmm {ev['sum_bits_mm']/1e6:.3f}M "
              f"stg {ev['stages_bw']} ovl {len(ov)} out {len(outside)} ret {ret['ok']} SM_HBM {ev['per_class'].get('SM_HBM', {}).get('stages_bw')} "
              f"SM_X {ev['per_class'].get('SM_X', {}).get('stages_bw')} longest {max(ev['by_class_longest_um'].values())}", flush=True)
        if a.png:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import plan_study_draw_1017 as Dr
            fig, ax = plt.subplots(figsize=(6.6, 8.4), dpi=240)
            Dr.draw(ax, P, G, W, H, f"HBM-NEXT {tag}: {W/1000:.2f} x {H/1000:.2f} mm = {r['die_mm2']} mm2; cut {cut['worst_v']['ratio']}/{cut['worst_h']['ratio']}; "
                    f"bit-mm {ev['sum_bits_mm']/1e6:.2f} M; stages_bw {ev['stages_bw']}", Dr.quad_boxes(P, W, S.QS))
            ax.title.set_fontsize(6)
            ax.set_xlim(-0.5, 26.5); ax.set_ylim(-0.5, 33.5)
            from matplotlib.patches import Rectangle
            ax.add_patch(Rectangle(((W - RETICLE[0]) / 2000, (H - RETICLE[1]) / 2000), RETICLE[0] / 1000, RETICLE[1] / 1000, fill=False, ec='#888888', lw=0.6, ls=':'))
            fig.tight_layout(); fig.savefig(out / f'{tag}.png'); plt.close(fig)
            flow_png(out / f'{tag}_flow.png', P, G, W, H, ev, tag)
    prev = out / 'plan_p4.json'
    allres = json.loads(prev.read_text()) if prev.is_file() else {}
    allres.update(res)
    prev.write_text(json.dumps(allres, indent=1, default=list))


if __name__ == '__main__':
    main()
