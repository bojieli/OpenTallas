"""S81-P9: for core pins whose CORE-KS table entry (largest non-M1 rect centre) is off the kit track after the
[0.108, 0.012] offset, take the centre of another rect of the SAME pin on the same layer that is on track (a
multi-port pin whose wide jog shape was picked over its track-aligned access shape)."""
import json, re, sys, glob
sys.path.insert(0, 'tools/die_plan'); import schema as S
L = {x['name']: x for x in S.ASAP7_LAYERS}; OFF = (0.108, 0.012)
def ontrack(ln, x, y):
    l = L[ln]; c = (x + OFF[0]) if l['dir'] == 'V' else (y + OFF[1])
    k = (c - l['offset_um']) / l['pitch_um']; return abs(k - round(k)) < 1e-4
tot = 0
for f in sorted(glob.glob('physical/die_plan/s81/inputs/core_pins/*.json')):
    j = json.load(open(f)); lef = open(j['lef']).read(); fixed = 0
    rects = {}
    for m in re.finditer(r'PIN (\S+)(.*?)END \1', lef, re.S):
        cur = None
        for t in re.finditer(r'LAYER (\S+) ;|RECT\s+([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)', m.group(2)):
            if t.group(1): cur = t.group(1)
            else:
                a, b, c, d = map(float, t.group(2, 3, 4, 5)); rects.setdefault(m.group(1), []).append((cur, (a + c) / 2, (b + d) / 2))
    for p in j['pins']:
        if p['layer'] not in L or p['layer'] == 'M1' or ontrack(p['layer'], p['x'], p['y']):
            continue
        alt = [r for r in rects.get(p['name'], []) if r[0] == p['layer'] and ontrack(*r)]
        if alt:
            p['x'], p['y'] = round(alt[0][1], 4), round(alt[0][2], 4); fixed += 1
    if fixed:
        j['source'] += f'; S81-P9 10-23: {fixed} multi-port pins re-pointed to their on-track access rect'
        json.dump(j, open(f, 'w'), indent=0); print(f, fixed)
    tot += fixed
print('total', tot)
