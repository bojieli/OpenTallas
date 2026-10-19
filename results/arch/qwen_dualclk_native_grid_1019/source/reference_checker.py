#!/usr/bin/env python3
"""Audit the SC2 abstract's internal-route protection, not parent routing."""
import argparse
import copy
import json
import hashlib
import re
from pathlib import Path


def contains(a, b):
    return a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]


def grow(r, n):
    return [r[0]-n, r[1]-n, r[2]+n, r[3]+n]


def intersects(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def covered(r, boxes):
    """Exact positive-area rectangle-union coverage using x slabs."""
    xs = sorted({r[0], r[2]} | {max(r[0], min(r[2], b[k])) for b in boxes for k in (0, 2)})
    for x0, x1 in zip(xs, xs[1:]):
        if x0 == x1:
            continue
        intervals = sorted((max(r[1], b[1]), min(r[3], b[3])) for b in boxes
                           if b[0] <= x0 and b[2] >= x1 and b[1] < r[3] and b[3] > r[1])
        y = r[1]
        for lo, hi in intervals:
            if lo > y:
                break
            y = max(y, hi)
        if y < r[3]:
            return False
    return True


def audit(m):
    width, _ = m['outline_nm']
    spacing = m['proof']['native_PRL_thin_spacing_nm']
    assert spacing == 24 and m['rules']['width_nm'] == 24
    obs = {}
    for o in m['proposed_obstruction_rectangles']:
        obs.setdefault(o['layer'], []).append(o['rect_nm'])
    errors = []
    counts = dict(paths=0, exposed_terminal_shapes=0, internal_shapes=0,
                  vias=0, protected_via_enclosures=0, legal_abstract_approaches=0)
    for p in m['paths']:
        counts['paths'] += 1
        x, y = p['terminal_nm']
        pin = [x-12, y-12, x+12, y+12]
        window = [0, y-12, 72, y+12] if p['face'] == 'W' else [width-72, y-12, width, y+12]
        if any(intersects(o, pin) for o in obs.get('M4', [])):
            errors.append([p['pin'], 'PIN_OBSTRUCTED'])
        for s in p['shapes']:
            r = s['rect_nm']; boxes = obs.get(s['layer'], [])
            if covered(r, boxes):
                counts['internal_shapes'] += 1
                continue
            if s['layer'] != 'M4' or not covered(r, boxes+[window]):
                errors.append([p['pin'], 'METAL_OUTSIDE_OBS_AND_TERMINAL', s])
            else:
                counts['exposed_terminal_shapes'] += 1
            # Every foreign-net shape touching internal neck must violate
            # actual thin-wire spacing to the visible PIN or the OBS.
            if not covered(r, [grow(o, spacing) for o in boxes]+[grow(pin, spacing)]):
                errors.append([p['pin'], 'UNPROTECTED_NECK', s])
        for v in p['vias']:
            counts['vias'] += 1
            for layer, key in [('M4', 'm4_rect_nm'), ('M5', 'm5_rect_nm')]:
                if not covered(v[key], obs.get(layer, [])):
                    errors.append([p['pin'], 'INTERNAL_VIA_ENCLOSURE_EXPOSED', layer, v[key]])
                else:
                    counts['protected_via_enclosures'] += 1
        # A same-net M4 approach can terminate on the visible PIN without
        # entering OBS. Its 108x24nm connected patch exceeds 2000nm2.
        approach = [-84, y-12, 24, y+12] if p['face'] == 'W' else [width-24, y-12, width+84, y+12]
        if any(intersects(approach, o) for o in obs.get('M4', [])):
            errors.append([p['pin'], 'APPROACH_BLOCKED'])
        if (approach[2]-approach[0])*(approach[3]-approach[1]) < m['rules']['minimum_area_nm2']:
            errors.append([p['pin'], 'APPROACH_AREA'])
        for q in m['paths']:
            if q['pin'] == p['pin']:
                continue
            qx, qy = q['terminal_nm']
            qp = [qx-12, qy-12, qx+12, qy+12]
            # Approaches span only the external face and their own pin;
            # y pitch is 192nm, with 168nm clear metal separation.
            if q['face'] == p['face'] and abs(qy-y)-24 < spacing:
                errors.append([p['pin'], 'OTHER_PIN_APPROACH_SPACING', q['pin']])
        counts['legal_abstract_approaches'] += 1
    return dict(status='PASS' if not errors else 'FAIL', counts=counts, errors=errors,
                scope='abstract native-width/spacing/OBS; parent routing grid, access points, PG escape and client arrays remain unqualified',
                neck_protection='24nm PIN halo reaches x48; 24nm OBS halo starts x48; no positive-width foreign conductor can occupy the intervening neck',
                additional_timing_qualification=False)


def main():
    p = argparse.ArgumentParser(); p.add_argument('model'); p.add_argument('--out', required=True)
    p.add_argument('--prototype', required=True); p.add_argument('--lef', required=True)
    a = p.parse_args(); m = json.loads(Path(a.model).read_text())
    prototype = json.loads(Path(a.prototype).read_text())
    assert prototype['access_paths'] == m['paths']
    assert prototype['obstruction_rectangles'] == m['proposed_obstruction_rectangles']
    lef = Path(a.lef).read_text()
    obs_text = lef.split('  OBS\n')[1].split('  END\n')[0]
    actual_obs = []
    for layer, coords in re.findall(r'LAYER (\S+)\s*;\s*RECT ([0-9. ]+)\s*;', obs_text):
        actual_obs.append(dict(layer=layer, rect_nm=[round(float(x)*1000) for x in coords.split()]))
    assert actual_obs == m['proposed_obstruction_rectangles']
    for path in m['paths']:
        name = path['pin']; x, y = path['terminal_nm']
        block = lef.split('  PIN '+name+'\n')[1].split('  END '+name+'\n')[0]
        rectangles = re.findall(r'RECT ([0-9. ]+)\s*;', block)
        assert len(rectangles) == 1
        assert [round(float(x)*1000) for x in rectangles[0].split()] == [x-12,y-12,x+12,y+12]
    results = {'positive': audit(m), 'mutants': {}}
    results['input_sha256'] = {n:hashlib.sha256(Path(v).read_bytes()).hexdigest()
                              for n,v in [('model',a.model),('prototype',a.prototype),('lef',a.lef)]}
    for name in ['wide_gap', 'missing_west_m5', 'blocked_terminal']:
        q = copy.deepcopy(m)
        if name == 'wide_gap':
            next(x for x in q['proposed_obstruction_rectangles'] if x['layer']=='M4')['rect_nm'][0] = 120
        elif name == 'missing_west_m5':
            q['proposed_obstruction_rectangles'] = [x for x in q['proposed_obstruction_rectangles'] if not (x['layer']=='M5' and x['rect_nm'][0]==72)]
        else:
            next(x for x in q['proposed_obstruction_rectangles'] if x['layer']=='M4')['rect_nm'][0] = 0
        results['mutants'][name] = audit(q)
    Path(a.out).write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps({'positive':results['positive']['status'], 'counts':results['positive']['counts'], 'mutants':{k:v['status'] for k,v in results['mutants'].items()}}))
    if results['positive']['errors'] or any(v['status']!='FAIL' for v in results['mutants'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
