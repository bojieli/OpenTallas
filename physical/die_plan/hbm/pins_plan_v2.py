#!/usr/bin/env python3
"""HBM-P4 plan-derived core pins (HBM d4g plan v2, G3 prerequisite).

Two cases, both written to cores/pins_plan/<module>.json in the pins_file schema (name, layer, x, y; core frame):

  repin   as-built cores whose LEF pins sit on M2/M3 (or a platform phase) that cannot land on the plan tracks under
          the mirrored instances.  Every pin keeps its edge and its position along the edge; it moves to the plan
          M4 (E/W edges, y on 0.024 + k*0.048) or M5 (N/S edges, x on 0.024 + k*0.048) track nearest to it,
          collisions pushed to the nearest free track.  M4/M5 are mirror-symmetric (offset = pitch/2), so
          track_offset_um = [0, 0] holds under every instance orient.
  ports   cores with no as-built LEF but a real RTL module: the elaborated port list (yosys netlist of the as-built
          view, or a yosys elaboration of the RTL) is spread over the four edges in port order (buses contiguous),
          alternating track use (every 2nd track) when capacity allows.  Connectivity-blind: the order is refined
          by the G3 binder; the pins are legal plan-track pins, not a connectivity claim.

    python3 pins_plan_v2.py --ports PORTS.json [--ports ...] --out cores/pins_plan
"""
import argparse, json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
PITCH, OFF = 0.048, 0.024          # plan M4 (H) and M5 (V)
INSET = 0.019                      # pin centre inset from the edge (as the r18h5 view LEFs)


def track(v, lo, hi):
    k = round((v - OFF) / PITCH)
    kmin = math.ceil((lo - OFF) / PITCH - 1e-9); kmax = math.floor((hi - OFF) / PITCH + 1e-9)
    return max(kmin, min(kmax, k)), kmin, kmax


def place_edge(items, length, used=None):
    """items: [(name, along)] -> {name: along on a free track}."""
    used = set() if used is None else used
    out = {}
    for name, a in sorted(items, key=lambda t: t[1]):
        k, kmin, kmax = track(a, 2 * PITCH, length - 2 * PITCH)
        for d in range(0, kmax - kmin + 2):
            for kk in (k + d, k - d):
                if kmin <= kk <= kmax and kk not in used:
                    used.add(kk); out[name] = round(OFF + kk * PITCH, 4); break
            if name in out:
                break
        if name not in out:
            raise SystemExit(f'edge full: {name} (length {length})')
    return out


def repin(pins, w, h):
    edges = {'S': [], 'N': [], 'W': [], 'E': []}
    for p in pins:
        x, y = p['x'], p['y']
        dist = {'S': y, 'N': h - y, 'W': x, 'E': w - x}
        e = min(dist, key=dist.get)
        edges[e].append((p['name'], x if e in 'SN' else y))
    out = []
    for e, items in edges.items():
        pos = place_edge(items, w if e in 'SN' else h)
        for name, a in pos.items():
            if e in 'SN':
                out.append(dict(name=name, layer='M5', x=a, y=INSET if e == 'S' else round(h - INSET, 4)))
            else:
                out.append(dict(name=name, layer='M4', x=INSET if e == 'W' else round(w - INSET, 4), y=a))
    return sorted(out, key=lambda p: p['name'])


def spread(ports, w, h):
    """ports: [[name, dir, width, lsb]] -> pins round the perimeter in port order."""
    bits = []
    for n, d, wd, lsb in ports:
        if wd == 1:
            bits.append(n)
        else:
            bits += [f'{n}[{lsb + i}]' for i in range(wd)]
    ntr = {e: int((L - 4 * PITCH) / PITCH) for e, L in (('S', w), ('E', h), ('N', w), ('W', h))}
    cap = sum(ntr.values())
    if len(bits) > cap:
        raise SystemExit(f'{len(bits)} pins > {cap} tracks')
    step = 2 if 2 * len(bits) <= cap else 1
    # share per edge proportional to its length
    tot = sum(ntr.values()); share = {}; rem = len(bits)
    for i, e in enumerate(('S', 'E', 'N', 'W')):
        share[e] = rem if i == 3 else min(rem, round(len(bits) * ntr[e] / tot))
        rem -= share[e]
    out = []; i = 0
    for e in ('S', 'E', 'N', 'W'):
        n = share[e]
        L = w if e in 'SN' else h
        k0 = math.ceil((2 * PITCH - OFF) / PITCH)
        span = ntr[e]
        st = step if n * step <= span else 1
        first = k0 + (span - n * st) // 2
        for j in range(n):
            a = round(OFF + (first + j * st) * PITCH, 4)
            nm = bits[i]; i += 1
            if e in 'SN':
                out.append(dict(name=nm, layer='M5', x=a, y=INSET if e == 'S' else round(h - INSET, 4)))
            else:
                out.append(dict(name=nm, layer='M4', x=INSET if e == 'W' else round(w - INSET, 4), y=a))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default=os.path.join(HERE, 'die_plan.json'))
    ap.add_argument('--ports', action='append', default=[], help='JSON {base module: {elaborated name: [[n,dir,w,lsb]]}}')
    ap.add_argument('--out', default=os.path.join(HERE, 'cores', 'pins_plan'))
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    ports = {}
    for f in a.ports:
        for b, v in json.load(open(f)).items():
            ports.setdefault(b, max(v.values(), key=lambda pl: sum(p[2] for p in pl)))   # widest elaboration
    os.makedirs(a.out, exist_ok=True)
    done, skipped = {}, {}
    for tn, t in sorted(plan['partition_types'].items()):
        for c in t.get('hard_cores', []):
            if 'pins_file' in c and 'pins_plan' not in c['pins_file']:
                continue                                # as-built pins that land on the plan tracks
            mod, (w, h) = c['module'], c['outline_um']
            note = c.get('note', '')
            key = f'{mod}@{w}x{h}'
            if key in done or key in skipped:
                continue
            lef = os.path.join(HERE, 'cores', 'pins', f'{mod}.json')
            if 'cannot land' in note and os.path.exists(lef):
                pins = repin(json.load(open(lef)), w, h); how = 'repin'
            elif mod in ports and not re.match(r'sm_(lx|tp)\d', c['inst']):
                pins = spread(ports[mod], w, h); how = 'ports'
            else:
                skipped[key] = ('SM synthetic boundary (lx/tp: wrapper RTL from the SM split)'
                                if re.match(r'sm_(lx|tp)\d', c['inst']) else
                                'split proposal (over-cap RTL split pending)' if 'SPLIT' in note else 'no port list')
                continue
            fn = f'{mod}__{w:g}x{h:g}.json'
            json.dump(pins, open(os.path.join(a.out, fn), 'w'), indent=0)
            done[key] = dict(file=fn, how=how, pins=len(pins),
                             layers=sorted({p['layer'] for p in pins}))
    json.dump(dict(done=done, skipped=skipped), open(os.path.join(a.out, 'index.json'), 'w'), indent=1, sort_keys=True)
    print(f'pins_plan: {len(done)} core shapes written ({sum(d["pins"] for d in done.values())} pins), '
          f'{len(skipped)} skipped')
    for k, v in sorted(skipped.items()):
        print('  skip', k, v)


if __name__ == '__main__':
    main()
