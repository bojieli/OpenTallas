#!/usr/bin/env python3
"""Absolute pin-track audit of every real-LEF child of a native HBM die candidate.

For each (master, orientation, origin residue) class, every signal/clock pin RECT
on M2..M7 is transformed to die coordinates and its centre is tested against the
ASAP7 preferred-axis track of its layer.  A RECT is on track when a track lies
inside its span with half a minimum wire width on both sides (a centred
minimum-width pin, or a wide pin that covers a whole track).  A pin with no
on-track RECT is OFFTRACK.  Residue classes are exact (integer nm), so 5k instances cost only the
distinct classes.  This is not DRC or via access; it is the legality screen for
R0/MY/MX/R180 placement on the 0.432 x 2.16 um integration grid.
"""
import argparse, collections, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
# layer: (axis of track coordinate, offset_nm, pitch_nm); M2 has seven tracks per 270 nm row
TR = {'M3': ('x', [9], 36), 'M4': ('y', [12], 48), 'M5': ('x', [12], 48), 'M6': ('y', [16], 64),
      'M7': ('x', [16], 64), 'M2': ('y', [45, 81, 117, 153, 189, 225, 270], 270)}
HW = {'M2': 9, 'M3': 9, 'M4': 12, 'M5': 12, 'M6': 16, 'M7': 16}


def nm(v):
    return int(round(float(v) * 1000))


def parse(path):
    text = path.read_text()
    size = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text)
    w, h = nm(size.group(1)), nm(size.group(2))
    pins = {}
    for m in re.finditer(r'\n\s*PIN\s+(\S+)(.*?)\n\s*END\s+\1', text, re.S):
        body = m.group(2)
        if re.search(r'USE\s+(POWER|GROUND)', body):
            continue
        layer, rects = None, []
        for line in body.splitlines():
            t = line.split()
            if t[:1] == ['LAYER']:
                layer = t[1]
            elif t[:1] == ['RECT'] and layer:
                rects.append((layer, *[nm(v) for v in t[1:5]]))
        pins[m.group(1)] = rects
    return w, h, pins


def _spans(pins, orient, w, h):
    """Per pin, the oriented (axis, lo, hi, layer) spans of its routing-layer RECTs, half-width trimmed."""
    out = {'x': [], 'y': []}
    for name, rects in pins.items():
        per = {'x': [], 'y': []}
        for layer, x0, y0, x1, y1 in rects:
            if layer not in TR:
                continue
            if orient in ('MY', 'R180'):
                x0, x1 = w - x1, w - x0
            if orient in ('MX', 'R180'):
                y0, y1 = h - y1, h - y0
            axis = TR[layer][0]
            lo, hi = (x0, x1) if axis == 'x' else (y0, y1)
            per[axis].append((layer, lo + HW[layer], hi - HW[layer]))
        # a pin is judged on the axis of its first routing RECT (its access layer)
        first = next((TR[r[0]][0] for r in rects if r[0] in TR), None)
        if first:
            out[first].append(per[first])
    return out


def _axis_ok(pinspans, origin):
    for spans in pinspans:
        if not any(lo + origin <= o + -((o - lo - origin) // TR[layer][2]) * TR[layer][2] <= hi + origin
                   for layer, lo, hi in spans for o in TR[layer][1]):
            return False
    return True


def legal_origin(pins, orient, w, h, ox, oy, reach=(288, 96), step=4):
    """Nearest origin (nm) at which every signal pin has an on-track RECT; None on an axis with no solution."""
    spans = _spans(pins, orient, w, h)
    result = []
    for axis, origin, lim in (('x', ox, reach[0]), ('y', oy, reach[1])):
        # distinct pins repeat the same residues; reduce to the distinct (layer, lo % pitch, hi - lo) sets
        uniq = {tuple(sorted({(l, a % TR[l][2], b - a) for l, a, b in s})) for s in spans[axis]}
        red = [[(l, a, a + d) for l, a, d in s] for s in uniq]
        found = None
        for k in sorted(range(-lim, lim + 1, step), key=abs):
            if _axis_ok(red, origin + k):
                found = origin + k
                break
        result.append(found)
    return result


def audit(candidate):
    cache, classes = {}, collections.defaultdict(list)
    for r in candidate['children']:
        if r.get('view_lef'):
            classes[(r['view_lef'], r['orientation'], nm(r['xy_um'][0]) % 1728, nm(r['xy_um'][1]) % 8640)].append(r)
    out = []
    for (lef, orient, rx, ry), rows in sorted(classes.items()):
        if lef not in cache:
            cache[lef] = parse(ROOT / lef)
        w, h, pins = cache[lef]
        ox, oy = nm(rows[0]['xy_um'][0]), nm(rows[0]['xy_um'][1])
        bad = collections.Counter()
        layers = collections.Counter()
        for name, rects in pins.items():
            ok = False
            for layer, x0, y0, x1, y1 in rects:
                if layer not in TR:
                    continue
                if orient in ('MY', 'R180'):
                    x0, x1 = w - x1, w - x0
                if orient in ('MX', 'R180'):
                    y0, y1 = h - y1, h - y0
                axis, offs, pitch = TR[layer]
                lo, hi = (ox + x0, ox + x1) if axis == 'x' else (oy + y0, oy + y1)
                lo, hi = lo + HW[layer], hi - HW[layer]
                if any(lo <= o + -((o - lo) // pitch) * pitch <= hi for o in offs):
                    ok = True
                    layers[layer] += 1
                    break
            if not ok:
                bad[rects[0][0] if rects else 'NO_RECT'] += 1
        out.append({'view_lef': lef, 'master': rows[0]['logical_module'], 'orientation': orient,
                    'origin_residue_nm': [rx, ry], 'instances': len(rows), 'signal_pins': len(pins),
                    'offtrack_pins_by_layer': dict(bad), 'ontrack_pins_by_layer': dict(layers),
                    'example_instance': rows[0]['instance']})
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    cand = json.loads(a.candidate.read_text())
    rows = audit(cand)
    bad = [r for r in rows if r['offtrack_pins_by_layer']]
    summary = collections.Counter()
    for r in rows:
        summary[(r['master'], r['orientation'], 'OFFTRACK' if r['offtrack_pins_by_layer'] else 'ok')] += r['instances']
    rec = {'schema': 'opentallas.hbm.native_pin_track_audit.v1', 'candidate': str(a.candidate),
           'classes': len(rows), 'offtrack_classes': len(bad),
           'offtrack_instances': sum(r['instances'] for r in bad),
           'audited_instances': sum(r['instances'] for r in rows),
           'summary': [{'master': k[0], 'orientation': k[1], 'status': k[2], 'instances': v} for k, v in sorted(summary.items())],
           'offtrack': bad, 'pass': not bad}
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ['classes', 'offtrack_classes', 'offtrack_instances', 'audited_instances', 'pass']}))
    for s in rec['summary']:
        if s['status'] != 'ok' or s['orientation'] not in ('R0',):
            print(s)
    for r in bad[:12]:
        print(r['master'], r['orientation'], r['origin_residue_nm'], r['instances'], r['signal_pins'], r['offtrack_pins_by_layer'], r['ontrack_pins_by_layer'])
