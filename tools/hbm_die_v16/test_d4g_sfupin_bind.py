#!/usr/bin/env python3
"""H-D4G GEN2 10-18: test of die_case_v16 synth_pin_bind on the sfucore grant (fake east peers; kit faces + N window must win;
window lands on k9_pin_grant_0gj.die_x after each quadrant orientation).  Exit 1 on failure."""
# Harness: runs die_case_v16's SYNTH face-assignment block (lines cap=... .. before fp=) for sfucore with a fake layout,
# then synth_lef, then checks pins (local) and die windows after place xf for each quadrant orientation.
import sys, json, re, textwrap, types, collections, os
from pathlib import Path
import subprocess, tempfile
W = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, W + '/tools'); sys.path.insert(0, W + '/tools/hbm_die_v15')
import die_port_bind as DPB
from die_case import synth_lef
import case_reach as CR
src = open(W + '/tools/hbm_die_v15/die_case_v16.py').read().splitlines()
a0 = next(i for i, l in enumerate(src) if l.startswith('        cap = {f: 0.9'))
a1 = next(i for i, l in enumerate(src) if l.startswith('        fp = {f: L for f, L in faces.items() if L}'))
block = textwrap.dedent('\n'.join(src[a0:a1]))
g = json.load(open(W + '/results/arch/hbm_die_d4g/grants_d4g.json'))
S = {s['name']: s for s in g['slots']}
idx, _ = DPB.rtl_index([W + '/rtl/hbm_accel/generic/peers'], [], {}, [])
m = idx['ot_hgi_sfu_core_split3']; env = m.env({})
c = 'ot_hgi_sfu_core_split3'
ports = {c: {p: m.width(p, env) for p in m.order}}
dirs = {c: {p: m.ports[p][0] for p in m.order}}
w, h = 1598.4, 1771.2
Q = ['SW', 'SE', 'NW', 'NE']
pl = {f'sfucore_{q}': dict(x=S[f'sfucore_{q}']['origin']['x'], y=S[f'sfucore_{q}']['origin']['y'],
                           o=S[f'sfucore_{q}']['origin']['orient'], w=w, h=h) for q in Q}
centre = lambda n: (pl[n]['x'] + w / 2, pl[n]['y'] + h / 2)
# fake peers: every port's peer due EAST in die coords (wrong for most kit faces) -> the bind must override
peer_xy = {}
for q in Q:
    cx, cy = centre(f'sfucore_{q}')
    for p in m.order:
        peer_xy[(f'sfucore_{q}', p)] = [(cx + 5000, cy)]
a = types.SimpleNamespace(compact_pins=True, max_pin_density=6.0)
ns = dict(cap=None, c=c, ports=ports, dirs=dirs, w=w, h=h, gsl=S['sfucore_SW'], flags={}, a=a, peer_xy=peer_xy,
          rep='sfucore_SW', clk={}, re=re, V={c: {'instances': list(pl)}}, pl=pl, centre=centre, PIN_STEP0=0.096,
          pin_density_over=[], collections=collections)
exec(block, ns)
lef = tempfile.mkdtemp() + '/sfucore.lef'
synth_lef(c, w, h, ns['pinlist'], lef, keepout=[])
L = CR.lef(lef)[c]
fp = json.loads(subprocess.check_output(['git', '-C', W, 'show', 'origin/claude/sfuk9-1018:physical/ref_tile/hbm_sfucore_k9/floorplan.json']))
kitf = {p: f for f, Lp in fp['pins'].items() for p in Lp}
def face_of(x, y):
    return 'N' if y > h - 1 else 'S' if y < 1 else 'E' if x > w - 1 else 'W'
bad, win = [], collections.defaultdict(list)
for pn, (px, py) in L['pins'].items():
    b = re.sub(r'\[\d+\]$', '', pn)
    if face_of(px, py) != kitf[b]:
        bad.append((pn, face_of(px, py), kitf[b]))
    if b in ('io_word', 'compiler_control', 'fault'):
        win[b].append(px)
print('flags', ns['flags'], 'pins', len(L['pins']), 'off-kit-face', len(bad), bad[:5])
allx = [x for v in win.values() for x in v]
print('window pins', len(allx), 'local x', round(min(allx), 3), round(max(allx), 3), 'inside', all(1040.4 <= x <= 1576.8 for x in allx))
for q in Q:
    v = dict(pl[f'sfucore_{q}'], orient=pl[f'sfucore_{q}']['o'])
    xs = [CR.xf(v, w, h, x, h)[0] for x in allx]; ys = {round(CR.xf(v, w, h, x, h)[1], 3) for x in allx}
    k = S[f'sfucore_{q}']['k9_pin_grant_0gj']
    print(q, v['orient'], 'die x', round(min(xs), 1), round(max(xs), 1), 'grant', k['die_x'], 'y', ys, 'grant', k['die_y'],
          'inside', k['die_x'][0] - 0.5 <= min(xs) and max(xs) <= k['die_x'][1] + 0.5)

ok = not bad and all(1040.4 <= x <= 1576.8 for x in allx) and len(allx) == 2214
print('SFUPIN_BIND', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
