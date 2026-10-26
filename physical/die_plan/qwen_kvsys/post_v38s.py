#!/usr/bin/env python3
"""KV-P8-HUB 10-23: FIRM internal stations on the astk legs of kv3_hub_Eo / kv3_hub_Wo (R3-INTERNAL).

GEOM-REVIEW8 22:30 PASS-CONDITIONAL (v3.8h astk hard cores): the legs between the hub's W (hub_Eo) / E (hub_Wo) seam
windows and the astk hard cores at the far corners run 1.0-2.7 mm with only the face register and the core pin.  KV
owner decision (KV-P7 23:24): option (i) = FIRM internal_stations[] (the window move (ii) cannot reach 750 um at 0
cycles: W legs keep dx >= 1,036 um, the bind packs the lanes across stacks).  The 0-cycle per-stack lane re-pack across
hub_C / hub_Ei / hub_Eo stays a v3.8 item.

Per leg (type bus <-> astk core port, core_conns.json + the core pins file): the station path is window -> (XC, y_win) ->
(XC, y_pin) -> pin centroid, XC = 900 um from the seam face (west of the cores on hub_Eo, mirrored on hub_Wo), so no
station sits inside a hard core; legs <= 750 um direct need none; the path is an L that clears the cores and does not run along a type face (the
face-register band and the windows sit there), else the XC detour;
stations = ceil(path / SPACING) - 1 equally spaced (every hop <= SPACING = 675 um, the
GEOM spacing; ft_station_max_um 750 leaves the detour margin).  A bus read by two cores (i_kvs_attn_acal_EN/WN feeds
both stacks) takes the larger count on both legs, so one bus lands at ONE added delay (R8 landed-bundle rule).  The
stations are register stages of the lane, so each affected lane gets lanes[].fixed_cycles += its bus's count (gen.py
latency: cycles = boundary + ft stations + fixed_cycles); the R8 pads follow from that in gen.py latency.

Only partition_types.{kv3_hub_Eo,kv3_hub_Wo}.internal_stations and the fixed_cycles/note of the lanes that end on those
buses are written.  usage: post_v38s.py die_plan.json PLAN_DIR [--table] > die_plan.json"""
import json
import math
import sys
from pathlib import Path

SPACING = 675.0
HOP_MAX = 750.0      # budgets.ft_station_max_um
XC = 900.0
TYPES = {'kv3_hub_Eo': (False, 'hub_Eo'), 'kv3_hub_Wo': (True, 'hub_Wo')}


def load_tools(plan_dir):
    sys.path.insert(0, str(Path(plan_dir).resolve().parents[2] / 'tools/die_plan'))
    import check as C
    import schema as S
    return C, S


def path_pts(a, b, xc):
    return [a, (xc, a[1]), (xc, b[1]), b]


def seg_hits(p, q, bx, m=1.0):
    """axis-parallel segment p-q passes through the interior of box bx (m um inset: pins on the edge are fine)"""
    x0, y0, x1, y1 = bx[0] + m, bx[1] + m, bx[2] - m, bx[3] - m
    lo_x, hi_x = sorted((p[0], q[0]))
    lo_y, hi_y = sorted((p[1], q[1]))
    return lo_x < x1 and hi_x > x0 and lo_y < y1 and hi_y > y0


def on_face(p, q, W, H, m=30.0, lmin=60.0):
    """segment runs ALONG a type face (within m um of it, longer than lmin): the face-register band and the windows"""
    if abs(p[0] - q[0]) + abs(p[1] - q[1]) <= lmin:
        return False
    if p[0] == q[0]:
        return p[0] < m or p[0] > W - m
    return p[1] < m or p[1] > H - m



def plen(pts):
    return sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))


def along(pts, s):
    for p, q in zip(pts, pts[1:]):
        L = abs(p[0] - q[0]) + abs(p[1] - q[1])
        if s <= L + 1e-9:
            f = s / L if L else 0.0
            return (round(p[0] + f * (q[0] - p[0]), 3), round(p[1] + f * (q[1] - p[1]), 3))
        s -= L
    return pts[-1]


def legs(raw, plan_dir):
    C, S = load_tools(plan_dir)
    P = S.Plan(raw)
    cc = json.loads((Path(plan_dir) / 'core_conns.json').read_text())
    out = []
    for tn, (mir, part) in TYPES.items():
        t = P.types[tn]
        W, H = t['outline_um']
        xc = W - XC if mir else XC
        bt = C._bus_targets(P, tn)
        bw = {b['name']: b.get('width') for b in t['buses']}
        boxes = {}
        for hc in t['hard_cores']:
            ox, oy = hc['origin_um']
            boxes[hc['inst']] = (ox, oy, ox + hc['outline_um'][0], oy + hc['outline_um'][1])
        for hc in t['hard_cores']:
            ox, oy = hc['origin_um']
            pins = json.loads((Path(plan_dir) / hc['pins_file']).read_text())['pins']
            pp = {}
            for p in pins:
                pp.setdefault(p['name'].split('[')[0], []).append((p['x'], p['y']))
            for port, conns in cc[tn][hc['inst']].items():
                xs = pp[port]
                pin = (round(ox + sum(a for a, _ in xs) / len(xs), 3), round(oy + sum(b for _, b in xs) / len(xs), 3))
                for c in conns:
                    if not c.startswith('bus:') or c[4:] not in bt:
                        continue
                    bus = c[4:]
                    face, win = bt[bus]
                    win = (round(win[0], 3), round(win[1], 3))
                    outb = bus.startswith('o_')
                    a, b = (pin, win) if outb else (win, pin)
                    direct = abs(a[0] - b[0]) + abs(a[1] - b[1])
                    if direct <= HOP_MAX:
                        continue           # face register -> core pin in one hop (R3: <= ft_station_max_um)
                    pts = None
                    for cand in ([a, (b[0], a[1]), b], [a, (a[0], b[1]), b]):
                        if not any(seg_hits(p, q, bx) for p, q in zip(cand, cand[1:]) for bx in boxes.values()) \
                                and not any(on_face(p, q, W, H) for p, q in zip(cand, cand[1:])):
                            pts = cand
                            break
                    pts = pts or path_pts(a, b, xc)
                    L = plen(pts)
                    out.append(dict(type=tn, part=part, core=hc['inst'], port=port, bus=bus, bits=bw.get(bus),
                                    face=face, a=a, b=b, pts=pts, path=L, direct=direct,
                                    n=math.ceil(L / SPACING - 1e-9) - 1, boxes=boxes, outb=outb))
    nbus = {}
    for e in out:
        k = (e['type'], e['bus'])
        nbus[k] = max(nbus.get(k, 0), e['n'])
    for e in out:
        e['n'] = nbus[(e['type'], e['bus'])]
        step = e['path'] / (e['n'] + 1)
        e['regs'] = [along(e['pts'], step * (i + 1)) for i in range(e['n'])]
        e['hop'] = step
        for r in e['regs']:
            for ci, (x0, y0, x1, y1) in e['boxes'].items():
                assert not (x0 < r[0] < x1 and y0 < r[1] < y1), (e['bus'], r, ci)
    return P, out, nbus


def apply(raw, plan_dir):
    P, L, nbus = legs(raw, plan_dir)
    T = raw['partition_types']
    for tn in TYPES:
        ist = [x for x in T[tn].get('internal_stations', []) if 'KV-P8-HUB' not in x.get('note', '')]
        for e in (x for x in L if x['type'] == tn):
            ist.append(dict(conn=f"bus:{e['bus']}", from_um=list(e['a']), to_um=list(e['b']),
                            regs_um=[list(r) for r in e['regs']], bits=e['bits'],
                            launch=(f"{e['core']}.{e['port']}" if e['outb'] else f"face:{e['face']}"),
                            capture=(f"face:{e['face']}" if e['outb'] else f"{e['core']}.{e['port']}"),
                            note=(f"KV-P8-HUB v3.8s R3-INTERNAL FIRM: path {e['path']:.0f} um via ({e['pts'][1][0]:.0f},{e['pts'][1][1]:.0f}), "
                                  f"{e['n']} stations, hop {e['hop']:.0f} <= {SPACING:g} (KV owner (i) 23:24)")))
        T[tn]['internal_stations'] = ist
    ends = {}
    for (tn, bus), n in nbus.items():
        ends[(TYPES[tn][1], bus)] = n
    ports = {p['id']: p for p in raw['ports']}
    touched = {}
    for ln in raw['lanes']:
        a, b = ports[ln['ports'][0]], ports[ln['ports'][-1]]
        n = ends.get((b['dst']['part'], b['dst']['bus']), 0) + ends.get((a['src']['part'], a['src']['bus']), 0)
        if not n:
            continue
        ln['fixed_cycles'] = int(ln.get('fixed_cycles', 0)) + n
        ln['note'] = ln.get('note', '') + f" | +{n} FIRM astk internal stations (KV-P8-HUB v3.8s, R3-INTERNAL)"
        touched[ln['id']] = n
    raw['note'] = raw.get('note', '') + (" | v3.8s (KV-P8-HUB 10-23): FIRM internal_stations on the hub_Eo/Wo astk "
                                         "legs (post_v38s.py), lane fixed_cycles += stations")
    return L, touched


def main():
    raw = json.loads(Path(sys.argv[1]).read_text())
    plan_dir = sys.argv[2]
    L, touched = apply(raw, plan_dir)
    if '--table' in sys.argv:
        for e in L:
            print(f"{e['type']}\t{e['core']}.{e['port']}\t{e['bus']}\t{e['bits']}\t{e['path']:.0f}\t{e['n']}\t"
                  f"{e['hop']:.0f}", file=sys.stderr)
        print('lanes', json.dumps(touched), file=sys.stderr)
    json.dump(raw, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
