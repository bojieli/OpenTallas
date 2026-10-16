#!/usr/bin/env python3
"""HBM v15 compact die plan (owner 2026-10-15 12:05: 660 mm2 compact option; grow only on measured GRT congestion or
area misfit).  T_band2-style coherent groups rebuilt with MEASURED block areas (Codex 0bd + H-ELEM-B + H-DIE synth):

  per quadrant (SW frame; SE = x-mirror, NW/NE = y-mirror):
    PHY + PC row on the die edge, 2 x 4 SM block (6609.6 x 1712.08 frames) with a 1.8 mm VM band between SM rows 2/3;
    the VM band holds 4 bank-pair GROUPS  [bank pair (2 VM banks + LG chain) | HC shell | SFU port group] + SU slice G
    (SU slice G sits AT bank pair {2G,2G+1}: every fixed-return LG link stays inside its group), the VM hub column
    (hub >= 1.1 mm per the adoption condition, DMA back, IDX operand leaf on SW), the SU core (RF replica + reducer)
    and the quadrant COLL engine at the centre end of the band (rings + SerDes endpoints are in the centre column).
  centre column: SerDes + endpoints on the S and N shorelines, the 4 IDX scorer clusters (512 CLOSED hslices each,
    3008.88 x 3840.48 rotated) stacked SW, SE | glue | NE, NW so each stack's keys enter from its own die half,
    IDX query/selector/link glue in the middle; 0.93 mm routing channels either side of the column.
Areas (um): SU slice 1330 x 1780 (Codex 0bd lower bound 34.75 mm2 leaf outlines / 16 slices + 15 % RF/control/
channels, H-ELEM-B per-slice pins ~3.46 k), SU core 250 x 1780, SFU group 0.40 mm2 (quadrant macro floor 0.838 mm2
x 1.25 halo + logic), HC shell 500 x 500 (GEO-H combined-shell request), VM hub 1100 x 1100, COLL 963.36 x 721.44
(v15 grant), DMA back 432 x 360.72, IDX scorer 3840.48 x 3008.88.

    compact_plan.py --area 660 --out DIR [--graph G]      -> DIR/compact.P.json, compact.graph.json, compact.metrics.json

Scored with tools/hbm_globalfp.py `score` (same objective/cut model as GLOBAL-FP-H, die outline patched) and pinned with
tools/hbm_globalfp_pins.py so tools/hbm_die_v15/grants.py can consume the result exactly like T_band2.
"""
import argparse, copy, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_globalfp as F  # noqa: E402

GAP = 20.0
SMW, SMH = 6609.6, 1712.08
BAND = 1800.0
SU_W, SU_H = 1250.0, 1780.0
CORE_W = 250.0
HC = 500.0
SFU_A = 400000.0
HUB = 1100.0
COLL_W, COLL_H = 963.36, 721.44
DBK_W, DBK_H = 432.0, 360.72
SC_W, SC_H = 3008.88, 3840.48          # IDX scorer, rotated (w x h)
COLUMN_W = 3100.0
CHANNEL = 930.0
EDGE = 120.0
SC_GAP = 100.0                         # relay row between the two scorers of a die half (cross-column relay homes)


def build(G0, area_mm2, channel=CHANNEL, band=None, hub_w=0.0):
    BAND = band or globals()['BAND']
    G = copy.deepcopy(G0)
    N = G['nodes']
    P = {}
    qw = 2 * SMW + GAP
    W = EDGE + qw + channel + COLUMN_W + channel + qw + EDGE
    H = area_mm2 * 1e6 / W
    # one quadrant's vertical stack (SW frame)
    y_pc = 21.6 + 1177.2 + 20.0
    y_a = y_pc + 399.6 + 20.0
    y_b = y_a + SMH + GAP
    y_band = y_b + SMH + GAP
    y_c = y_band + BAND + GAP
    y_d = y_c + SMH + GAP
    top = y_d + SMH
    if 2 * top + GAP > H:
        raise SystemExit(f'area {area_mm2} mm2 too small: H {H:.0f} < {2 * top + GAP:.0f}')

    def setn(i, w, h, src):
        if i not in N:
            N[i] = dict(id=i, kind=src.split(':')[0], w=w, h=h, area_mm2=w * h / 1e6, area_src='measured', provenance=src)
        else:
            N[i] = dict(N[i], w=w, h=h, area_mm2=round(w * h / 1e6, 4), area_src='measured (H-DIE compact plan)', provenance=src)

    def put(i, x, y, q):
        w, h = N[i]['w'], N[i]['h']
        if q in ('SE', 'NE'):
            x = W - x - w
        if q in ('NW', 'NE'):
            y = H - y - h
        P[i] = dict(x=round(x, 3), y=round(y, 3), w=w, h=h, orient='R0')

    for q in F.QS:
        # PHY + PC row
        put(f'phy_{q}', 1455.84, 21.6, q)
        pcs = sorted([k for k in N if k.startswith(f'pc_{q}')])
        for k, p in enumerate(pcs):
            put(p, 1457.8 + k * (N[p]['w'] + GAP), y_pc, q)
        sms = sorted([k for k in N if k.startswith(f'sm_{q}')], key=lambda s: int(s[len(f'sm_{q}'):]))
        rows = [y_a, y_b, y_c, y_d]
        for k, s in enumerate(sms):
            put(s, EDGE + (k % 2) * (SMW + GAP), rows[k // 2], q)
        # VM band
        x = EDGE
        banks = sorted([k for k in N if k.startswith(f'vmb_{q}')], key=lambda s: int(s[len(f'vmb_{q}'):]))
        su = sorted([k for k in N if k.startswith(f'su_{q}')])
        sfu = sorted([k for k in N if k.startswith(f'sfu_{q}')])
        hc = sorted([k for k in N if k.startswith(f'hc_{q}')])
        for g in range(4):
            bw = N[banks[2 * g]]['w']
            bh = N[banks[2 * g]]['h']
            # left column (500 wide): HC shell / QUANT (NW) / SFU group, each within 500 um of BOTH banks of the pair
            setn(hc[g], HC, HC, 'HC combined shell 500 x 500 (GEO-H)')
            put(hc[g], x, y_band, q)
            yq = y_band + HC + GAP
            if q == 'NW':
                put(f'quant_NW{g}', x, yq, q)
                yq += 245 + GAP
            sh = round(SFU_A / HC, 3)
            setn(sfu[g], HC, sh, 'SFU port group 0.40 mm2 (quadrant macro floor 0.838 mm2 x1.25 + logic, Codex 0bd)')
            put(sfu[g], x, yq, q)
            assert yq + sh <= y_band + BAND + 1e-6, (q, g, yq + sh - y_band)
            x += HC + GAP
            yb = y_band + 400.0
            put(banks[2 * g], x, yb, q)
            put(banks[2 * g + 1], x, yb + bh + GAP, q)
            x += bw + GAP
            setn(su[g], SU_W, SU_H, 'SU slice (Codex 0bd 34.75 mm2 leaf lower bound /16, +2.4 %)')
            put(su[g], x, y_band, q)
            x += SU_W + GAP
        setn(f'sucore_{q}', CORE_W, SU_H, 'SU:ot_hbm_su_static_qcore RF replica + reducer (H-ELEM-B)')
        put(f'sucore_{q}', x, y_band, q)
        x += CORE_W + GAP
        if hub_w:
            # TALL HUB (H-DIE r2 cut fix): hub reshaped to hub_w x (BAND - 2 GAP) at the quadrant's inner edge, so its
            # band-facing (W) and channel-facing (E) faces are ~1.8 mm long (pin density and the face cut both drop by
            # 1.1/1.76); COLL, DMA back and the IDX operand leaf stack in one column west of the hub.
            hh = BAND - 2 * GAP
            hx = EDGE + qw - hub_w
            cx = hx - GAP - COLL_W
            slack = cx - GAP - x
            assert slack >= -1e-6, (q, 'band too long for the tall hub', slack)
            setn(f'coll_{q}', COLL_W, COLL_H, 'COLL v15 grant')
            put(f'coll_{q}', cx, y_band + GAP, q)
            setn(f'dbk_{q}', DBK_W, DBK_H, 'DMA:ot_hgi_dma_back_static v15 grant (no T_band2 block)')
            put(f'dbk_{q}', cx, y_band + GAP + COLL_H + GAP, q)
            if q == 'SW':
                setn('idx_op', 360.72, 317.52, 'IDX:ot_hbm_idx_vm_query_static grant')
                put('idx_op', cx + DBK_W + GAP, y_band + GAP + COLL_H + GAP, q)
            setn(f'vmh_{q}', hub_w, hh, f'VM hub reshaped tall {hub_w:.0f} x {hh:.0f} (area >= 1.1 mm square; faces >= 1.1 mm on W/E)')
            put(f'vmh_{q}', hx, y_band + GAP, q)
            x = hx + hub_w
        else:
            # COLL then the VM hub column at the CENTRE end of the band: VM ring / COLL ring / COLL endpoint traffic
            # enters from the centre channel without running along the band (worst-cut driver in the first compact try)
            setn(f'coll_{q}', COLL_W, COLL_H, 'COLL v15 grant')
            put(f'coll_{q}', x, y_band + (BAND - COLL_H) / 2, q)
            x += COLL_W + GAP
            setn(f'vmh_{q}', HUB, HUB, 'VM hub >= 1.1 mm (T_band2 adoption condition)')
            put(f'vmh_{q}', x, y_band, q)
            setn(f'dbk_{q}', DBK_W, DBK_H, 'DMA:ot_hgi_dma_back_static v15 grant (no T_band2 block)')
            put(f'dbk_{q}', x, y_band + HUB + GAP, q)
            if q == 'SW':
                setn('idx_op', 360.72, 317.52, 'IDX:ot_hbm_idx_vm_query_static grant')
                put('idx_op', x + DBK_W + GAP, y_band + HUB + GAP, q)
            x += HUB + GAP
        assert x <= EDGE + qw + 1e-6, (q, x, EDGE + qw)
    # centre column
    c0 = EDGE + qw + channel
    # HC engine (estimate 1.0 mm2, single NE engine) in the NE-side channel at the NE band height
    setn('hc_eng', channel - 2 * GAP, round(1.0e6 / (channel - 2 * GAP), 3), 'HC_ENGINE 1.0 mm2 estimate in the NE channel')
    P['hc_eng'] = dict(x=c0 + COLUMN_W + GAP, y=H - y_band - N['hc_eng']['h'], w=N['hc_eng']['w'], h=N['hc_eng']['h'], orient='R0')
    for side, n, q0 in (('S', 5, 'SW'), ('N', 4, 'NW')):
        lks = sorted([k for k in N if k.startswith(f'lk_{side}')])
        eps = sorted([k for k in N if k.startswith(f'ep_{side}')])
        for k, l in enumerate(lks):
            put(l, c0 + k * (250.056 + GAP), 20.0, q0)
        ex = c0 + len(lks) * (250.056 + GAP)
        for k, e in enumerate(eps):
            put(e, ex + (k % 2) * (434.72 + GAP), 20.0 + (k // 2) * (515.2 + GAP), q0)
    ys = 20.0 + 2250.216 + GAP
    for i, sc in enumerate(('idx_s0', 'idx_s1')):       # SW, SE stacks from the south half
        setn(sc, SC_W, SC_H, 'IDX scorer: 512 CLOSED hslices 172.8x103.68 + glue (v15 grant, rotated)')
        P[sc] = dict(x=c0 + (COLUMN_W - SC_W) / 2, y=ys + i * (SC_H + SC_GAP), w=SC_W, h=SC_H, orient='R90')
    yg = ys + 2 * SC_H + SC_GAP + GAP
    glue = [('idx_q', 449.28, 449.28), ('idx_sel', 1164.24, 317.52), ('idx_link', 745.2, 317.52)]
    gx = c0
    for g, w, h in glue:
        setn(g, w, h, 'IDX glue (v15 grant, measured synth)')
        P[g] = dict(x=gx, y=yg, w=w, h=h, orient='R0')
        gx += w + GAP
    yn = yg + 449.28 + GAP
    for i, sc in enumerate(('idx_s3', 'idx_s2')):       # NE, NW from the north half
        setn(sc, SC_W, SC_H, 'IDX scorer (v15 grant, rotated)')
        P[sc] = dict(x=c0 + (COLUMN_W - SC_W) / 2, y=yn + i * (SC_H + SC_GAP), w=SC_W, h=SC_H, orient='R90')
    assert yn + 2 * SC_H + SC_GAP + GAP <= H - 20 - 2250.216 + 1e-6, ('centre column too tall', yn + 2 * SC_H + 2 * GAP, H - 2270)
    return G, P, W, H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', default='results/arch/hbm_globalfp_1015/noatt/graph_sm_npg4.json')
    ap.add_argument('--ref', default='results/arch/hbm_globalfp_1015/noatt/ref_sm.json')
    ap.add_argument('--area', type=float, default=660.0)
    ap.add_argument('--channel', type=float, default=CHANNEL)
    ap.add_argument('--band', type=float, default=BAND, help='VM band height (SM row 2 to row 3 gap) in um')
    ap.add_argument('--hub-w', type=float, default=0.0, help='tall VM hub of this width (0 = 1.1 mm square hub)')
    ap.add_argument('--fit', action='store_true', help='grow --area to the smallest outline that fits (10 mm2 steps of 0.1)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    G0 = json.loads((ROOT / a.graph).read_text())
    if a.fit:
        area = a.area
        while True:
            try:
                G, P, W, H = build(G0, area, a.channel, a.band, a.hub_w); break
            except SystemExit:
                area = round(area + 0.1, 1)
    else:
        G, P, W, H = build(G0, a.area, a.channel, a.band, a.hub_w)
    F.W_DIE, F.H_DIE = W, H
    missing = [i for i in G['nodes'] if i not in P]
    ov = F.overlaps(P)
    out = F.outside(P)
    m = F.score(G, P, json.loads((ROOT / a.ref).read_text()), cut_detail=False)
    placed = sum(r['w'] * r['h'] for r in P.values()) / 1e6
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    (o / 'compact.P.json').write_text(json.dumps(P, indent=1))
    (o / 'compact.graph.json').write_text(json.dumps(G, indent=1))
    keep = {k: v for k, v in m.items() if not isinstance(v, (list, dict)) or k in ('worst_cut_where',)}
    rec = dict(die_um=[round(W, 3), round(H, 3)], die_mm2=round(W * H / 1e6, 2), placed_mm2=round(placed, 2),
               density=round(placed * 1e6 / (W * H), 3), unplaced=missing, overlaps=ov[:20], n_overlaps=len(ov),
               outside=out, metrics=keep)
    (o / 'compact.metrics.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps(dict((k, rec[k]) for k in ('die_um', 'die_mm2', 'placed_mm2', 'density', 'n_overlaps', 'unplaced', 'outside'))))
    print(json.dumps(keep)[:1500])


if __name__ == '__main__':
    main()
