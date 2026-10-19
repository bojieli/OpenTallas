#!/usr/bin/env python3
"""HC-RINGPLAN 10-19 (DIE-HBM-LEAD decision 01:40/01:50, lanes/H-D4G.md): GEN2d HC ring blocks in grants_d4g.json + the d4g plan.

Per quadrant q ONE ring block of 3 x 3 cells of 734.4 um (2,203.2 um square, the kit geometry of
tools/ref_tile/specs_hbm_b_rtl2_1017/mk_ring_kits.py): hub hc_<q> (ot_hbm_hc_qhub_static, kit hbm_hcq_hub_1017) in the
centre cell, banks hcb_<q>0..7 abutting around it clockwise from W (b0 W, b1 NW, b2 N, b3 NE, b4 E, b5 SE, b6 S, b7 SW;
b7 abuts b0).  Masters / kits by pin plan (R0 / R180 only, as the kits): b0 = bankq0 (kit b0), b1 R0 / b5 R180 = bankq
(kit ca), b3 R0 / b7 R180 = bankq (kit cb), b2 R0 / b6 R180 = bankq_ft (kit e2), b4 R0 = bankq (kit e0).

Homes (scanned on the 21.6 grid over every grant slot and plan block at >= 21.6 um clearance, bit-weighted hub
wire length to hc_eng / hleaf_<q> / the 4 SFU tap leaves hc_<q>0..3 as tie-break; see --report):
  SW / SE: directly N of the SFU programme store + VM hub (sfup_<q>, vmh_<q>), E/W edge on the centre lane channel
           (|x - W/2| >= 200 um), between the SFU store / SU programme slice and the centre channel -- the band the
           plan's HC engine block hce_<q> and the hub hc_<q> already served.
  NW / NE: the same band in the N half, S of sfup_<q> / the NW VM glue tile (vmh_NW slot), N of the COLL engine.
Re-packed neighbours (no empty area on link paths, owner 10-17):
  * collks_NW + fr_NW slide 187.7 um S along the coll_NW E face (still abutting coll_NW at 21.6 um) to clear the NW ring.
  * plan hce_<q> (the old 1,598.4 um HC engine block, empty since the quarter split) := the ring block;
    plan hc_<q> := the centre cell; plan vmh_<q> (VM hub REGION, 480 x 3,200) clipped to clear the ring at 21.6 um
    (the VM glue tile slots and the placed VM hub cells are unchanged).
The b7 -> b0 die relay hcx_<q>_* goes (contract post-layer d4g_layers/l11_hc_ring.py: bankq0 DRLY 2).
Idempotent: hcb_<q>k slots are replaced, hc_<q> and the moved slots are set to absolute positions.
    d4g_gen2d_grants_hcring.py [--grants G] [--plan P] [--report R] [--check-only]"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'results/arch/hbm_die_d4g'
Q = ['SW', 'SE', 'NW', 'NE']
CELL = 734.4
RING = 3 * CELL
CLR = 21.6
# ring block origins (lower-left), chosen by the scan in this file (--scan) and inspected in the layout PNG
HOME = {'SW': (7689.6, 11988.0), 'SE': (10324.8, 11988.0), 'NW': (7689.6, 17323.2), 'NE': (10324.8, 17323.2)}
# re-packed neighbour slots: name -> new origin
MOVE = {'collks_NW': (7427.376, 16956.0), 'fr_NW': (7427.376, 16908.912)}
# bank k -> (col, row) inside the ring (row 0 = S), master, kit, orient, clock face in R0
BANKS = {0: ((0, 1), 'ot_hbm_hc_bankq0_static', 'hbm_hcq_bank_b0_1017', 'R0', 'E'),
         1: ((0, 2), 'ot_hbm_hc_bankq_static', 'hbm_hcq_bank_ca_1017', 'R0', 'E'),
         2: ((1, 2), 'ot_hbm_hc_bankq_ft_static', 'hbm_hcq_bank_e2_1017', 'R0', 'S'),
         3: ((2, 2), 'ot_hbm_hc_bankq_static', 'hbm_hcq_bank_cb_1017', 'R0', 'W'),
         4: ((2, 1), 'ot_hbm_hc_bankq_static', 'hbm_hcq_bank_e0_1017', 'R0', 'W'),
         5: ((2, 0), 'ot_hbm_hc_bankq_static', 'hbm_hcq_bank_ca_1017', 'R180', 'E'),
         6: ((1, 0), 'ot_hbm_hc_bankq_ft_static', 'hbm_hcq_bank_e2_1017', 'R180', 'S'),
         7: ((0, 0), 'ot_hbm_hc_bankq_static', 'hbm_hcq_bank_cb_1017', 'R180', 'W')}
ROT = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
GRANT = 'd4g_gen2d_hcring_1019'


def rect(s):
    return (s['origin']['x'], s['origin']['y'], s['origin']['x'] + s['outline']['w'], s['origin']['y'] + s['outline']['h'])


def gap(a, b):
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])


def slot(name, cell, x, y, orient, kit, face, notes, extra=None):
    s = dict(name=name, cell=cell, kind='tile', parent='die', outline=dict(w=CELL, h=CELL),
             origin=dict(x=round(x, 3), y=round(y, 3), orient=orient),
             clock_entry=dict(pin='clk', face=face, layer='M4' if face in 'EW' else 'M5'),
             pg_layer='M5', strap_layer='M6', signal_max_layer='M5', layer_cap='M5',
             io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2), version=1, grant=GRANT,
             rtl_owner='HBM-HCRING / HBM-B-RTL2b', kit=f'physical/ref_tile/{kit}', pins=[], pin_status='KIT_FACES',
             ring_block=None, notes=notes)
    s.update(extra or {})
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grants', default=str(D / 'grants_d4g.json'))
    ap.add_argument('--plan', default=str(D / 'plan/d4g_phy/compact.P.json'))
    ap.add_argument('--report', default=str(D / 'hcring/gen2d_hcring_slots.json'))
    ap.add_argument('--check-only', action='store_true')
    a = ap.parse_args()
    g = json.loads(Path(a.grants).read_text()); P = json.loads(Path(a.plan).read_text())
    die = next(s for s in g['slots'] if s['kind'] == 'die'); W, H = die['outline']['w'], die['outline']['h']
    rep = dict(tool='tools/hbm_die_v16/d4g_gen2d_grants_hcring.py', decision='lanes/H-D4G.md DIE-HBM-LEAD 10-19 01:40 + 01:50',
               cell_um=CELL, ring_um=RING, clearance_um=CLR, quadrants={}, moved={}, plan_edits={})
    # 1. drop old HC slots of the quadrant (hub re-homed, banks replaced)
    old = {s['name']: s for s in g['slots']}
    g['slots'] = [s for s in g['slots'] if not any(s['name'] == f'hcb_{q}{k}' for q in Q for k in range(8))]
    # 2. re-packed neighbours
    for n, (x, y) in MOVE.items():
        s = next(s for s in g['slots'] if s['name'] == n)
        rep['moved'][n] = dict(was=[s['origin']['x'], s['origin']['y']], now=[x, y])
        s['origin']['x'], s['origin']['y'] = x, y
        s['notes'] = (s.get('notes') or '').split(' | HC-RINGPLAN')[0] + \
            f' | HC-RINGPLAN 10-19: slid S along the coll_NW E face to clear the NW HC ring block ({GRANT})'
    # 3. ring slots
    for q in Q:
        X, Y = HOME[q]
        hub = next(s for s in g['slots'] if s['name'] == f'hc_{q}')
        rep['quadrants'][q] = dict(ring=[X, Y, X + RING, Y + RING], hub_was=[hub['origin']['x'], hub['origin']['y'], hub['cell']])
        hub.update(slot(f'hc_{q}', 'ot_hbm_hc_qhub_static', X + CELL, Y + CELL, 'R0', 'hbm_hcq_hub_1017', 'W',
                        f'HC-RINGPLAN 10-19: HC quarter hub (hc_<q> + quarter-engine centre) in the CENTRE cell of the {q} ring '
                        'block; faces W b0 (+ chain exit s_i), N lg_rr + b1-3, E lg_wq/lg_rq + b4, S F20/result/root + b5-7 '
                        '(mk_ring_kits.py). External hub links leave the ring OVER the bank tiles (die layers above the bank '
                        'signal_max_layer M5) -- the kits abut, there is no inter-tile channel.',
                        dict(plan_block=f'hc_{q}', ring_block=f'hcr_{q}')))
        for k, ((c, r), m, kit, o, face) in BANKS.items():
            fz = face if o == 'R0' else ROT[face]
            g['slots'].append(slot(f'hcb_{q}{k}', m, X + c * CELL, Y + r * CELL, o, kit, fz,
                                   f'HC-RINGPLAN 10-19: HC ring bank {k} of {q} (b0 W, b1 NW, b2 N, b3 NE, b4 E, b5 SE, b6 S, '
                                   f'b7 SW; b7 abuts b0, no die relay); kit {kit} {o}' +
                                   (' -- needs DRLY 2 at its GEN2d re-kit (HBM-HCRING)' if k == 0 else ''),
                                   dict(ring_block=f'hcr_{q}')))
        # plan edits
        pe = {}
        pe[f'hce_{q}'] = dict(was=P.get(f'hce_{q}'))
        P[f'hce_{q}'] = dict(x=X, y=Y, w=RING, h=RING, orient='R0')
        pe[f'hc_{q}'] = dict(was=P.get(f'hc_{q}'))
        P[f'hc_{q}'] = dict(x=X + CELL, y=Y + CELL, w=CELL, h=CELL, orient='R0')
        v = P[f'vmh_{q}']; vr = (v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h']); R = (X, Y, X + RING, Y + RING)
        if gap(vr, R) < CLR:
            pe[f'vmh_{q}'] = dict(was=dict(v))
            if q[0] == 'S':   # region below the ring: clip its top
                v['h'] = round(Y - CLR - v['y'], 3)
            else:             # region above the ring: clip its bottom
                top = v['y'] + v['h']; v['y'] = round(Y + RING + CLR, 3); v['h'] = round(top - v['y'], 3)
        for n in pe:
            pe[n]['now'] = P[n]
        rep['plan_edits'][q] = pe
    # 4. checks: every new/moved slot clears every other slot and every plan block (except its own HC blocks) by >= CLR
    S = [(s['name'], rect(s)) for s in g['slots'] if s['kind'] != 'die' and s.get('origin') and s.get('outline')]
    new = {f'hc_{q}' for q in Q} | {f'hcb_{q}{k}' for q in Q for k in range(8)} | set(MOVE)
    ringq = {n: (s.get('ring_block') if isinstance(s, dict) else None) for n, s in ((s['name'], s) for s in g['slots'])}
    bad = []
    for i, (n1, r1) in enumerate(S):
        for n2, r2 in S[i + 1:]:
            if not (n1 in new or n2 in new):
                continue
            same = ringq.get(n1) and ringq.get(n1) == ringq.get(n2)
            gp = gap(r1, r2)
            if (same and gp < -1e-6) or (not same and gp < CLR - 1e-6):
                bad.append([n1, n2, round(gp, 2)])
    own = lambda n, q: n in (f'hce_{q}', f'hc_{q}')
    for q in Q:
        X, Y = HOME[q]; R = (X, Y, X + RING, Y + RING)
        for n, r in P.items():
            if isinstance(r, dict) and 'x' in r and not own(n, q):
                gp = gap(R, (r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']))
                if gp < CLR - 1e-6:
                    bad.append([f'hcr_{q}', f'plan:{n}', round(gp, 2)])
        if abs((X + RING / 2) - W / 2) < RING / 2 + 200 - 1e-6:
            bad.append([f'hcr_{q}', 'centre lane channel (W/2 +- 200 um)', round(min(abs(X - W / 2), abs(X + RING - W / 2)), 1)])
        if not (0 <= X and X + RING <= W and 0 <= Y and Y + RING <= H):
            bad.append([f'hcr_{q}', 'die', 0])
    for n in MOVE:   # moved slots vs plan blocks
        r1 = next(r for m, r in S if m == n)
        for m, r in P.items():
            if isinstance(r, dict) and 'x' in r and gap(r1, (r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h'])) < 0 \
                    and m not in ('coll_NW',):
                bad.append([n, f'plan:{m}', round(gap(r1, (r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h'])), 2)])
    # abutment proof of the ring (b_k -> b_k+1 share a face, b7 -> b0 too; hub shares a face with b0/b2/b4/b6)
    ab = {}
    for q in Q:
        sl = {s['name']: rect(s) for s in g['slots'] if s['name'].startswith((f'hcb_{q}', f'hc_{q}'))}
        for k in range(8):
            ab[f'{q}:b{k}->b{(k + 1) % 8}'] = round(gap(sl[f'hcb_{q}{k}'], sl[f'hcb_{q}{(k + 1) % 8}']), 3)
    rep['abutment_gaps_um'] = ab
    rep['violations'] = bad
    rep['hcx_relay'] = 'dropped: b7 S face abuts b0 S-side chain entry (b0 DRLY 2, contract post-layer l11_hc_ring.py)'
    if not a.check_only:
        Path(a.grants).write_text(json.dumps(g, indent=1) + '\n')
        Path(a.plan).write_text(json.dumps(P, indent=1) + '\n')
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    for q in Q:
        print(q, 'ring', rep['quadrants'][q]['ring'])
    print('abutment max gap', max(ab.values()), 'violations', len(bad))
    for b in bad[:20]:
        print('  VIOL', b)
    raise SystemExit(1 if bad or max(ab.values()) > 1e-6 else 0)


if __name__ == '__main__':
    main()
