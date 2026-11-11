#!/usr/bin/env python3
"""DIE-QC-97 S1 11-11: die-floorplan reach gate for the Qwen compute die -- every die-level link hop <= 405 um.

Model (the repo's own per-bit die-level model, die_hop_scan.py): for every partition -> partition port and every bit
(epoch bit included)

    hop = |A's last register on the bit -> A's pin| + |A's pin -> B's pin| + |B's pin -> B's first register|

with registers at the exact ft bit sites (bit_sites_um), else regs_um, else spread on check.zroute, and pin-registered
non-ft ends at the pin.  check.py G0 'hops'/'stations' (lane_pin_hops, nominal regs) is run by the caller as a second
gate; this tool closes the per-bit cross-face hops that G0's window-centre model does not see.

Fix forms, cheapest first (OWNER: safe by construction, no retries):
  (c) RE-SITE: the A slot has explicit bit sites and >= 2 stations: each bit over LIMIT of A's LAST station moves to
      the nearest free legal row site (RowAllocator: placed macros + 1.08 um keep-off + clock-buffer halos; every
      existing ft bit site reserved; 2.16 x 0.27 um site grid) on the old-site -> out-pin line such that
          |S(k-2) -> S(k-1)| <= LIMIT  and  |S(k-1) -> out pin| + worst tail of EVERY instance of the type <= LIMIT
      (tail = pin -> pin + pin -> first register of the receiving partition, max over all ports of that type/slot).
      Station counts, windows, pins, outlines, cores, RTL, latency: unchanged (0 added cycles).
      regs_um[k-1] becomes the centroid of the moved station's bit centres.
  (b) ADD STATION: not needed on the 11-11 QC head; a remainder is reported as 'unfixed' (exit 1) with its class.

Every changed lane gets an entry in the ledger with added cycles (TOK-VERIFY list); re-site entries add 0.

    python3 -I qc_s1_reach.py PLAN.json OUT.json LEDGER.json [--limit 400] [--repo REPO]
"""
import argparse, hashlib, json, sys
from collections import defaultdict
from pathlib import Path

GATE = 405.0      # die.reach_um (R3)
LIMIT = 400.0     # accepted (5 um under the gate for the cell-centre vs pin model, as ft_reach_fix.py)
FRACS = (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6)


def md(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def scan(P, H, S, tabs):
    """per-bit cross-face rows (die_hop_scan.main without writing): [(pid, A, B, bit, hop, a_reg_to_pin, tail)]"""
    def tab(tn):
        if tn not in tabs:
            tabs[tn] = H.type_tables(P, tn)
        return tabs[tn]
    rows = []
    for pid, pr in P.ports.items():
        A, B = pr['src']['part'], pr['dst']['part']
        if S.DIE_PART in (A, B):
            continue
        ba, bb = pr['src']['bus'], pr['dst']['bus']
        (pa, ca), (pb, cb) = tab(P.parts[A]['type']), tab(P.parts[B]['type'])
        sa, sb = P.buses(A)[ba].get('slot'), P.buses(B)[bb].get('slot')
        for bit in range(S.port_pins_count(pr)):
            qa, qb = P.to_die(A, pa[ba][bit][:2]), P.to_die(B, pb[bb][bit][:2])
            ra = P.to_die(A, ca[sa][bit][-1]) if sa else qa
            rb = P.to_die(B, cb[sb][bit][0]) if sb else qb
            d = (md(ra, qa), md(qa, qb), md(qb, rb))
            rows.append((pid, A, B, sa, bit, sum(d), d[0], d[1] + d[2]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('ledger')
    ap.add_argument('--limit', type=float, default=LIMIT)
    ap.add_argument('--repo', default=str(Path(__file__).resolve().parents[2]))
    a = ap.parse_args()
    dp = Path(a.repo) / 'tools' / 'die_plan'
    sys.path.insert(0, str(dp)); sys.path.insert(0, str(Path(a.repo)))
    import numpy as np
    import schema as S, check as C, die_hop_scan as H  # noqa: E402
    from placement_obstacles import placement_boxes  # noqa: E402
    from tools.die_trial.legal_sites import RowAllocator  # noqa: E402
    from ft_nudge import KEEPOFF, CELL_DEFAULT, clock_points  # noqa: E402

    src = Path(a.plan).read_bytes()
    raw = json.loads(src)
    P = S.Plan(raw, Path(a.plan))
    rows = scan(P, H, S, {})
    over = [r for r in rows if r[5] > GATE + 1e-6]
    before = dict(bits_over=len(over), ports_over=len({r[0] for r in over}), max_hop_um=round(max(r[5] for r in rows), 1))

    # group the over bits by the A (driving) type + slot; tail = worst over EVERY instance of that type/slot
    tail = defaultdict(float)          # (type, slot, bit) -> worst pin->pin + pin->first register
    for pid, A, B, sa, bit, h, d0, t in rows:
        if sa:
            k = (P.parts[A]['type'], sa, bit)
            tail[k] = max(tail[k], t)
    need = defaultdict(set)
    unfixed, margin = [], []
    for pid, A, B, sa, bit, h, d0, t in rows:
        if h <= a.limit + 1e-6:
            continue
        tn = P.parts[A]['type']
        slot = next((s for s in P.types[tn].get('ft_slots', []) if s['name'] == sa), None) if sa else None
        if slot is None or not slot.get('bit_sites_um') or int(slot.get('stations', 1)) < 2:
            (unfixed if h > GATE + 1e-6 else margin).append(dict(port=pid, bit=bit, hop_um=round(h, 1), cls='b' if slot is None else 'b/c',
                                why='A end is a pin register' if slot is None else 'A slot has no explicit bit sites'))
            continue
        need[(tn, sa)].add(bit)

    ledger = dict(tool='qc_s1_reach.py', plan=a.plan, plan_sha256=hashlib.sha256(src).hexdigest()[:12], gate_um=GATE,
                  limit_um=a.limit, before=before, resite=[], lanes={}, unfixed=unfixed, margin_left=margin)
    for (tn, sn), bits in sorted(need.items()):
        t = raw['partition_types'][tn]
        s = next(x for x in t['ft_slots'] if x['name'] == sn)
        k = int(s['stations'])
        w, h = t['outline_um'][:2]
        boxes = [(x0 - KEEPOFF, y0 - KEEPOFF, x1 + KEEPOFF, y1 + KEEPOFF) for x0, y0, x1, y1 in placement_boxes(t).values()]
        hh = C.CLOCK_BUF_HALO_UM + 0.01; cw0, ch0 = CELL_DEFAULT
        boxes += [(q[0] - hh - cw0, q[1] - hh - ch0, q[0] + hh, q[1] + hh) for q in clock_points(t)]
        alloc = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL_DEFAULT,
                             column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
        for s2 in t['ft_slots']:
            cw_, ch_ = s2.get('bit_site_cell_um', CELL_DEFAULT)
            for st in s2.get('bit_sites_um') or []:
                for x, y in st:
                    alloc.reserve_rectangle((x, y, x + cw_, y + ch_))
        pins, chains = H.type_tables(P, tn)
        po = pins[sn + '_o']
        cw_, ch_ = s.get('bit_site_cell_um', CELL_DEFAULT)
        rec = dict(type=tn, slot=sn, stage=k - 1, bits=len(bits), moved=0, max_move_um=0.0, worst_before=0.0,
                   worst_after=0.0, worst_prev_hop_after=0.0, failed=[],
                   instances=sorted(p for p, v in P.parts.items() if v['type'] == tn))
        for bit in sorted(bits):
            ch = chains[sn][bit]
            prev, old, pin = np.array(ch[k - 2]), np.array(ch[k - 1]), np.array(po[bit][:2])
            tl = tail[(tn, sn, bit)]
            rec['worst_before'] = max(rec['worst_before'], round(md(old, pin) + tl, 1))
            budget = a.limit - tl
            done = False
            for f in FRACS:
                c = old + (pin - old) * f
                try:
                    p, _ = alloc.allocate(c, 1, max_radius_um=30.0)
                except ValueError:
                    continue
                q = p[0]
                if md(q, pin) <= budget and md(prev, q) <= a.limit:
                    s['bit_sites_um'][k - 2][bit] = [round(float(q[0] - cw_ / 2), 6), round(float(q[1] - ch_ / 2), 6)]
                    rec['moved'] += 1
                    rec['max_move_um'] = max(rec['max_move_um'], round(md(q, old), 2))
                    rec['worst_after'] = max(rec['worst_after'], round(md(q, pin) + tl, 1))
                    rec['worst_prev_hop_after'] = max(rec['worst_prev_hop_after'], round(md(prev, q), 1))
                    done = True
                    break
            if not done:
                rec['failed'].append(dict(bit=bit, prev_to_pin=round(md(prev, pin), 1), tail=round(tl, 1)))
        if s.get('regs_um') and len(s['regs_um']) >= k:
            cs = [(x + cw_ / 2, y + ch_ / 2) for x, y in s['bit_sites_um'][k - 2]]
            s['regs_um'][k - 1] = [round(sum(c[0] for c in cs) / len(cs), 4), round(sum(c[1] for c in cs) / len(cs), 4)]
        ledger['resite'].append(rec)
        for p in rec['failed']:
            unfixed.append(dict(type=tn, slot=sn, bit=p['bit'], cls='b', why='no legal site within both hops: add a station'))

    # lanes through a changed slot: added cycles (re-site = 0)
    changed = {(r['type'], r['slot']) for r in ledger['resite'] if r['moved']}
    for lid, ln in raw['lanes'].items() if isinstance(raw['lanes'], dict) else ((l['id'], l) for l in raw['lanes']):
        for pid in ln['ports']:
            pr = P.ports[pid]; A = pr['src']['part']
            if A != S.DIE_PART and (P.parts[A]['type'], P.buses(A)[pr['src']['bus']].get('slot')) in changed:
                ledger['lanes'].setdefault(lid, dict(added_cycles=0, form='re-site last station (c)', ports=[]))['ports'].append(pid)
    raw['note'] = ('DIE-QC-97 S1 qc_s1_reach: %d ft last-station bits re-sited in %d type slots for per-bit die hops <= %g um '
                   '(0 added cycles) <- ' % (sum(r['moved'] for r in ledger['resite']), len(changed), a.limit)) + raw.get('note', '')
    Path(a.out).write_text(json.dumps(raw) + '\n')
    P2 = S.Plan(json.loads(Path(a.out).read_text()), Path(a.out))
    rows2 = scan(P2, H, S, {})
    over2 = [r for r in rows2 if r[5] > GATE + 1e-6]
    ledger['after'] = dict(bits_over=len(over2), ports_over=len({r[0] for r in over2}),
                           max_hop_um=round(max(r[5] for r in rows2), 1),
                           over_ports=sorted({r[0] for r in over2}))
    ledger['out_sha256'] = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()[:12]
    ledger['tok_verify'] = {lid: v['added_cycles'] for lid, v in sorted(ledger['lanes'].items())}
    Path(a.ledger).write_text(json.dumps(ledger, indent=1) + '\n')
    print('before', before, 'after', {k: v for k, v in ledger['after'].items() if k != 'over_ports'},
          'resite slots', len(ledger['resite']), 'bits moved', sum(r['moved'] for r in ledger['resite']),
          'unfixed', len(unfixed), 'out', ledger['out_sha256'])
    return 1 if over2 or unfixed else 0


if __name__ == '__main__':
    sys.exit(main())
