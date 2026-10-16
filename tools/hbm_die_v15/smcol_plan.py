#!/usr/bin/env python3
"""HBM v15 'SM COLUMN' floorplan candidate v8 (H-DIE 2026-10-15, coordinator: PLAN ONLY -- no die shrink or die run until
the owner, who set 660 mm2, has the comparison).

Per quadrant (SW frame; SE = x-mirror, NW/NE = y-mirror):
  PHY (8.5 mm) + PC row (8 boxes 1036.8 x 399.6) on the die edge, exactly as compact660_v5;
  8 SM COLUMNS: SM k = 1036.8 x SMH (default 2750 um: ~2.85 mm2 = ~60 % fill of the synthesized SM, 1.19 mm2 std +
    132 x 128x256 SRAM) DIRECTLY over PC box k (its own four PHY channels 4k..4k+3);
  the VM/SU band (same groups and order as compact660_v5: [HC | QUANT(NW) | SFU] + bank pair + SU slice, x4, SU core,
    COLL, VM hub + DMA back (+ IDX operand leaf on SW)) directly above the SM columns;
  the stack's IDX scorer (3008.88 x 3840.48) beside its PHY / SM columns at the quadrant's inner end (keys stay in the
    stack's own quadrant); the centre column keeps SerDes + endpoints at the shorelines and the IDX glue + HC engine.
Writes DIR/{smcol.P.json, smcol.graph.json, smcol.metrics.json, pins/smcol.pins.json} (pins: tools/hbm_globalfp_pins.py
rule, one segment per link end on the face nearest its peer, 1-D packed).
    smcol_plan.py --out DIR [--smh 2750] [--channel 930] [--mid 600]
"""
import argparse, copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_globalfp as F  # noqa: E402
import hbm_globalfp_pins as PINS  # noqa: E402
import compact_plan as C  # noqa: E402  (tools/hbm_die_v15 on path below)

GAP = 20.0
SMGAP = 20.0


def build(G0, smh, channel, mid, column_w, P5, W5, H5, y_band5):
    G = copy.deepcopy(G0); N = G['nodes']; P = {}
    qw = 2 * C.SMW + GAP                        # the band length of compact660_v5 (band-limited quadrant width)
    W = C.EDGE + qw + channel + column_w + channel + qw + C.EDGE
    y_pc = 21.6 + 1177.2 + 20.0
    y_sm = y_pc + 399.6 + 20.0
    y_band = y_sm + smh + SMGAP
    top = y_band + C.BAND
    H = 2 * top + mid

    def setn(i, w, h, src):
        N[i] = dict(N.get(i, dict(id=i, kind=src.split(':')[0])), w=w, h=h, area_mm2=round(w * h / 1e6, 4), provenance=src)

    def put(i, x, y, q):
        w, h = N[i]['w'], N[i]['h']
        if q in ('SE', 'NE'):
            x = W - x - w
        if q in ('NW', 'NE'):
            y = H - y - h
        P[i] = dict(x=round(x, 3), y=round(y, 3), w=w, h=h, orient='R0')
    for q in F.QS:
        put(f'phy_{q}', 1455.84, 21.6, q)
        pcs = sorted([k for k in N if k.startswith(f'pc_{q}')])
        for k, p in enumerate(pcs):
            put(p, 1457.8 + k * (N[p]['w'] + GAP), y_pc, q)
        sms = sorted([k for k in N if k.startswith(f'sm_{q}')], key=lambda s: int(s[len(f'sm_{q}'):]))
        for k, s in enumerate(sms):
            setn(s, 1036.8, smh, f'SM column 1036.8 x {smh} (v8 candidate; synth 1.19 mm2 std + 132 x 128x256 SRAM)')
            put(s, 1457.8 + k * (1036.8 + GAP), y_sm, q)
        # the VM/SU band: compact660_v5's band EXACTLY (same blocks, x, order, tall hub), shifted to sit on the SM columns
        for i, r5 in P5.items():
            if i.split('_')[0] not in ('hc', 'sfu', 'quant', 'vmb', 'su', 'sucore', 'coll', 'vmh', 'dbk', 'idx') or i.startswith('idx_s') \
                    or i in ('idx_q', 'idx_sel', 'idx_link'):
                continue
            iq = i.split('_')[1][:2] if i != 'idx_op' else 'SW'
            if iq != q:
                continue
            xl = r5['x'] if q in ('SW', 'NW') else W5 - r5['x'] - r5['w']
            yl = r5['y'] if q in ('SW', 'SE') else H5 - r5['y'] - r5['h']
            N[i] = dict(N[i], w=r5['w'], h=r5['h'])
            put(i, xl, yl - y_band5 + y_band, q)
        # the stack's IDX scorer at the quadrant's inner end, beside the PHY / SM columns, below the band
        sc = {'SW': 'idx_s0', 'SE': 'idx_s1', 'NE': 'idx_s3', 'NW': 'idx_s2'}[q]
        setn(sc, C.SC_W, C.SC_H, 'IDX scorer (v15 grant, rotated) in its own quadrant')
        sx = C.EDGE + qw - C.SC_W
        assert sx >= 1457.8 + 8 * (1036.8 + GAP) + GAP - 1e-6, (q, 'scorer overlaps SM columns', sx)
        assert 21.6 + C.SC_H <= y_band - GAP + 1e-6, (q, 'scorer taller than PHY+PC+SM', 21.6 + C.SC_H, y_band)
        put(sc, sx, 21.6, q); P[sc]['orient'] = 'R90'
    c0 = C.EDGE + qw + channel
    for side, n, q0 in (('S', 5, 'SW'), ('N', 4, 'NW')):
        lks = sorted([k for k in N if k.startswith(f'lk_{side}')]); eps = sorted([k for k in N if k.startswith(f'ep_{side}')])
        for k, l in enumerate(lks):
            put(l, c0 + k * (250.056 + GAP), 20.0, q0)
        ex = c0 + len(lks) * (250.056 + GAP)
        for k, e in enumerate(eps):
            put(e, ex + (k % 2) * (434.72 + GAP), 20.0 + (k // 2) * (515.2 + GAP), q0)
    yg = H / 2 - 449.28 / 2
    gx = c0
    for g, w, h in [('idx_q', 449.28, 449.28), ('idx_sel', 1164.24, 317.52), ('idx_link', 745.2, 317.52)]:
        setn(g, w, h, 'IDX glue (v15 grant)')
        P[g] = dict(x=gx, y=yg, w=w, h=h, orient='R0'); gx += w + GAP
    hw = channel - 2 * GAP
    setn('hc_eng', hw, round(1.0e6 / hw, 3), 'HC_ENGINE 1.0 mm2 estimate')
    P['hc_eng'] = dict(x=c0 + column_w + GAP, y=H - y_band - N['hc_eng']['h'], w=hw, h=N['hc_eng']['h'], orient='R0')
    return G, P, W, H


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', default='results/arch/hbm_die_v15/compact660_v5')
    ap.add_argument('--ref', default='results/arch/hbm_globalfp_1015/noatt/ref_sm.json')
    ap.add_argument('--smh', type=float, default=2750.0)
    ap.add_argument('--channel', type=float, default=C.CHANNEL)
    ap.add_argument('--column', type=float, default=C.COLUMN_W)
    ap.add_argument('--mid', type=float, default=600.0, help='channel between the S and N halves (um)')
    ap.add_argument('--smgap', type=float, default=20.0, help='channel between the SM columns and the band (um)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    global SMGAP
    SMGAP = a.smgap
    G0 = json.loads((ROOT / a.base / 'compact.graph.json').read_text())
    P5 = json.loads((ROOT / a.base / 'compact.P.json').read_text())
    m5 = json.loads((ROOT / a.base / 'compact.metrics.json').read_text())
    W5, H5 = m5['die_um']
    y_band5 = min(r['y'] for k, r in P5.items() if k.startswith('su_SW'))
    G, P, W, H = build(G0, a.smh, a.channel, a.mid, a.column, P5, W5, H5, y_band5)
    F.W_DIE, F.H_DIE = W, H
    ov = F.overlaps(P); out = F.outside(P); missing = [i for i in G['nodes'] if i not in P]
    m = F.score(G, P, json.loads((ROOT / a.ref).read_text()), cut_detail=False)
    o = Path(a.out); (o / 'pins').mkdir(parents=True, exist_ok=True)
    (o / 'smcol.P.json').write_text(json.dumps(P, indent=1)); (o / 'smcol.graph.json').write_text(json.dumps(G, indent=1))
    pp, faces = PINS.pins(G, P, m)
    doc = dict(schema='opentallas.hbm_globalfp.pins.v1', candidate='smcol_v8', die_outline_um=[W, H], pin_density_per_um=PINS.PIN_DENSITY,
               rule='one pin segment per link end on the face nearest its peer, centred at the closest-outline point, 1-D packed',
               blocks={b: dict(x=round(P[b]['x'], 1), y=round(P[b]['y'], 1), w=G['nodes'][b]['w'], h=G['nodes'][b]['h'],
                               kind=G['nodes'][b]['kind'], orient=P[b].get('orient', 'R0'), faces=pp.get(b, {})) for b in G['nodes'] if b in P},
               faces_over_1=[dict(block=b, face=f, utilisation=u, bits=bits) for b, f, u, bits in faces if u > 1.0],
               worst_faces=[dict(block=b, face=f, utilisation=u, bits=bits) for b, f, u, bits in faces[:20]])
    (o / 'pins' / 'smcol.pins.json').write_text(json.dumps(doc, indent=1))
    placed = sum(r['w'] * r['h'] for r in P.values()) / 1e6
    keep = {k: v for k, v in m.items() if not isinstance(v, (list, dict)) or k in ('worst_cut_where',)}
    rec = dict(die_um=[round(W, 3), round(H, 3)], die_mm2=round(W * H / 1e6, 2), placed_mm2=round(placed, 2),
               density=round(placed * 1e6 / (W * H), 3), n_overlaps=len(ov), overlaps=ov[:10], outside=out, unplaced=missing,
               faces_over_1=len(doc['faces_over_1']), metrics=keep)
    (o / 'smcol.metrics.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ('die_um', 'die_mm2', 'placed_mm2', 'density', 'n_overlaps', 'unplaced', 'outside', 'faces_over_1')}))
    print(json.dumps(keep)[:800])


if __name__ == '__main__':
    main()
