#!/usr/bin/env python3
"""KV-KITS-21: event27 ahub ck[3..6] entries (DIE-KV-27, round um: 150/450/580) sit off the M5 die-symmetric tracks; the plan
note allows 'kit may slide <=20 um off macros'.  Snap x of each off-track M5 clock entry to the nearest track (<=0.024 um); an
entry inside a hard-child block (+4.32 halo) slides by the smallest on-track move off it (<=20 um, asserted); write PINS_OUT, and point a COPY of the plan's ahub hard core at it.
usage: snap_ahub_pins.py REPO PLAN_DIR   (writes PLAN_DIR/event27/qkd_ahub_pins_r27s.json + PLAN_DIR/plan_e27f_ahubs.json)"""
import json, sys, hashlib
from pathlib import Path
repo, pd = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(repo / 'physical/die_plan/qwen_kvsys/cores/harden'), str(repo / 'tools/die_plan')]
import gen_core_kit_kv as GK
src = pd / 'event27/qkd_ahub_pins_r27.json'
d = json.loads(src.read_text())
hc = json.loads((repo / 'physical/die_plan/qwen_kvsys/cores/harden/qkd_ahub_hard_children.json').read_text())
HALO = 4.32   # config MACRO_PLACE_HALO
SZ = {}
for m, v in hc['children'].items():
    lef = (repo / v / f'{m}.lef').read_text()
    a, b = lef.split('SIZE', 1)[1].split(';')[0].replace('BY', ' ').split()
    SZ[m] = (float(a), float(b))
BOX = [(b['inst'], b['x'] - HALO, b['y'] - HALO, b['x'] + SZ[b['master']][0] + HALO, b['y'] + SZ[b['master']][1] + HALO)
       for b in hc['blocks']]   # square children: orientation keeps the bbox
def inside(x, y):
    return [n for n, x0, y0, x1, y1 in BOX if x0 < x < x1 and y0 < y < y1]
def trk(v, L, up):
    import math
    k = (v - GK.OFFS[L]) / GK.PITCH[L]
    return round(GK.OFFS[L] + (math.ceil(k) if up else math.floor(k)) * GK.PITCH[L], 6)
moves = []
for p in d['pins']:
    L = p['layer']; ax = 'x' if L in ('M3', 'M5', 'M7') else 'y'
    k = (p[ax] - GK.OFFS[L]) / GK.PITCH[L]
    if abs(k - round(k)) <= 0.05:
        continue
    assert p['name'].startswith('ck['), p['name']
    new = round(GK.OFFS[L] + round(k) * GK.PITCH[L], 6)
    assert abs(new - p[ax]) <= 20.0
    frm = (p['x'], p['y'])
    p[ax] = new
    hit = inside(p['x'], p['y'])
    if hit:   # slide off the macro (+halo): smallest move, x on M5 tracks, y free (interior M5 pin)
        n, x0, y0, x1, y1 = [b for b in BOX if b[0] == hit[0]][0]
        c = [(abs(trk(x1, L, True) - p['x']), 'x', trk(x1, L, True)), (abs(p['x'] - trk(x0, L, False)), 'x', trk(x0, L, False)),
             (abs(y1 - p['y']), 'y', round(y1 + 0.001, 3)), (abs(p['y'] - y0), 'y', round(y0 - 0.001, 3))]
        dmv, a2, v2 = min(c)
        p[a2] = v2
        assert not inside(p['x'], p['y']) and abs(p['x'] - frm[0]) + abs(p['y'] - frm[1]) <= 20.0, (p, hit)
    moves.append(dict(name=p['name'], frm=list(frm), to=[p['x'], p['y']], off_macro=hit or None))
    p['note'] = p.get('note', '') + f' | KV-KITS-21: on M5 track' + (f', slid off {hit[0]}+halo' if hit else '') + ' (plan allows <=20 um)'
d['note'] = d.get('note', '') + ' | KV-KITS-21 r27s: ck[3..6] snapped to M5 tracks; ck entries off hard-child macros+halo'
out = pd / 'event27/qkd_ahub_pins_r27s.json'
out.write_text(json.dumps(d, indent=1) + '\n')
P = json.loads((pd / 'plan_e27f.json').read_bytes())
hit = 0
for tn, t in P['partition_types'].items():
    for h in t.get('hard_cores', []):
        if h['module'] == 'qkd_ahub':
            assert h['pins_file'] == 'event27/qkd_ahub_pins_r27.json'
            h['pins_file'] = 'event27/qkd_ahub_pins_r27s.json'; hit += 1
assert hit == 1
(pd / 'plan_e27f_ahubs.json').write_text(json.dumps(P, indent=1))
print(json.dumps(dict(moves=moves, pins_sha256=hashlib.sha256(out.read_bytes()).hexdigest(), blocks=[b['inst'] for b in hc['blocks']])))
