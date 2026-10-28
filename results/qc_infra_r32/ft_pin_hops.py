#!/usr/bin/env python3
"""INFRA-FIRST-QC-R32 per-bit FT pin model (COORD ruling R31 (3)).

Per ft_slot and per INSTANCE: bit i leaves on its out_face at the linear out-window point
u_i = lo + (i+0.5)/n (hi-lo) (hi - ... for order lsb_high) -- the packet's own out convention -- and ENTERS on its
in_face at the point where the abutting neighbour's same-named slot leaves (that neighbour's out pin of bit i,
mapped through both orientations into this frame).  Hops (Manhattan, um, cell centre):
  in  = in pin(i) -> bank0 site(i)   (station 0 -> first bank register)
  out = last bank site(i) -> out pin(i)
A slot whose in-pin has no matching abutting neighbour slot is reported 'in_unmatched' with the pessimistic model
(any point of a window as wide as the out window centred on regs_um[0]; R31 numcheck form), never silently passed.
Limit 405 um (METHODOLOGY 12.1e).  Usage: ft_pin_hops.py PLAN(.json|.json.gz) OUT.json
"""
import gzip, json, sys
from collections import defaultdict
LIM = 405.0
def load(p): return json.load(gzip.open(p) if p.endswith('.gz') else open(p))
def man(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
OPP = dict(N='S', S='N', E='W', W='E')
def face_pt(face, W, H, u): return {'N': (u, H), 'S': (u, 0.0), 'E': (W, u), 'W': (0.0, u)}[face]
def to_die(part, W, H, q):
    x, y = q; o = part.get('orient', 'R0'); ox, oy = part['origin_um']
    if o in ('MY', 'R180'): x = W - x
    if o in ('MX', 'R180'): y = H - y
    return (ox + x, oy + y)
def die_face(face, o):
    if o in ('MX', 'R180') and face in 'NS': face = OPP[face]
    if o in ('MY', 'R180') and face in 'EW': face = OPP[face]
    return face
def out_pins(s, W, H):
    B = s['bit_sites_um']; n = len(B[0]); lo, hi = s['out_window_um']; rev = s.get('order') == 'lsb_high'
    return [face_pt(s['out_face'], W, H, (hi - (i+.5)/n*(hi-lo)) if rev else (lo + (i+.5)/n*(hi-lo))) for i in range(n)]
def main(plan, outp):
    p = load(plan); PT = p['partition_types']; parts = p['partitions']
    rect = {q['name']: (q['origin_um'][0], q['origin_um'][1], q['origin_um'][0]+PT[q['type']]['outline_um'][0],
                        q['origin_um'][1]+PT[q['type']]['outline_um'][1]) for q in parts}
    rows, worst = [], dict(in_hop=0., out_hop=0.)
    for q in parts:
        t = PT[q['type']]; W, H = t['outline_um']; r = rect[q['name']]
        for s in t.get('ft_slots') or []:
            B = s.get('bit_sites_um') or []
            if not B: continue
            n = len(B[0]); cw, ch = s.get('bit_site_cell_um', [1.404, 0.27])
            c = lambda b: (b[0]+cw/2, b[1]+ch/2)
            op = out_pins(s, W, H)
            out_h = max(man(c(B[-1][i]), op[i]) for i in range(n))
            # abutting neighbour across the in face (die frame) with the same-named slot leaving toward us
            df = die_face(s['in_face'], q.get('orient', 'R0'))
            mid = to_die(q, W, H, tuple(s['regs_um'][0]))
            nb = None
            for m in parts:
                if m is q: continue
                R = rect[m['name']]
                touch = {'N': abs(R[1]-r[3]) < 1e-3, 'S': abs(R[3]-r[1]) < 1e-3, 'E': abs(R[0]-r[2]) < 1e-3, 'W': abs(R[2]-r[0]) < 1e-3}[df]
                if not touch: continue
                if df in 'NS' and not (R[0]-1e-3 <= mid[0] <= R[2]+1e-3): continue
                if df in 'EW' and not (R[1]-1e-3 <= mid[1] <= R[3]+1e-3): continue
                ms = [z for z in PT[m['type']].get('ft_slots') or [] if z['name'] == s['name'] and z.get('bit_sites_um')
                      and die_face(z['out_face'], m.get('orient', 'R0')) == OPP[df]]
                if ms: nb = (m, ms[0]); break
            if nb is not None and len(nb[1]['bit_sites_um'][0]) == n:
                m, z = nb; Wm, Hm = PT[m['type']]['outline_um']
                pins = []
                for pp in out_pins(z, Wm, Hm):
                    dx, dy = to_die(m, Wm, Hm, pp)            # die point -> this instance frame
                    x, y = dx - q['origin_um'][0], dy - q['origin_um'][1]
                    o = q.get('orient', 'R0')
                    if o in ('MY', 'R180'): x = W - x
                    if o in ('MX', 'R180'): y = H - y
                    pins.append((x, y))
                in_h = max(man(pins[i], c(B[0][i])) for i in range(n)); model = f"neighbour {m['name']}/{z['name']}"
            else:
                lo, hi = s['out_window_um']; half = (hi-lo)/2; u0 = s['regs_um'][0][1 if s['in_face'] in 'EW' else 0]
                in_h = max(man(face_pt(s['in_face'], W, H, uu), c(B[0][i])) for i in range(n) for uu in (u0-half, u0+half))
                model = 'in_unmatched (pessimistic window)' if nb is None else f"width mismatch {len(nb[1]['bit_sites_um'][0])} vs {n}"
            rows.append(dict(part=q['name'], type=q['type'], slot=s['name'], n=n, in_hop=round(in_h, 3), out_hop=round(out_h, 3), in_model=model))
            worst['in_hop'] = max(worst['in_hop'], in_h); worst['out_hop'] = max(worst['out_hop'], out_h)
    over = [r for r in rows if r['in_hop'] > LIM or r['out_hop'] > LIM]
    res = dict(schema='opentallas.ft_pin_hops.v1', plan=plan, limit_um=LIM, slots_instances=len(rows),
               worst={k: round(v, 3) for k, v in worst.items()}, over_limit=over,
               unmatched=sum(1 for r in rows if not r['in_model'].startswith('neighbour')),
               top_in=sorted(rows, key=lambda r: -r['in_hop'])[:10], top_out=sorted(rows, key=lambda r: -r['out_hop'])[:10], rows=rows)
    json.dump(res, open(outp, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ('rows',)}, indent=1)[:5000])
    return 1 if over else 0
if __name__ == '__main__': raise SystemExit(main(*sys.argv[1:3]))
