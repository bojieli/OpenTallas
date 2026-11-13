"""HEAD-97 rp21 (COORD 11-13 (1)): the relays that stand in the 4 elemA outline strips are placed one per pin, 1.96 um
off the core face (inside pin_relay_um 4.32), at the along-face coordinate of their own face pin (pin list order =
relay bit order), instead of stacked at the strip end.  Pins from street_rule's core model (face_pos)."""
import sys, json, re
N, src, out = sys.argv[1:4]
sys.path[:0] = [N + '/tools/die_plan']
import street_rule as S
cap = {}
orig = S.analyze
def an(W, H, cores, *a, **k):
    cap.setdefault('cores', cores); cap.setdefault('W', W)
    return orig(W, H, cores, *a, **k)
S.analyze = an
S.main(['check', src, '--die', 's81_head', '--types', 'hd_tile', '--repo', N, '--out', '/dev/null'])
P = json.load(open(src)); t = P['partition_types']['hd_tile']; rs = t['relay_sites']; W = t['outline_um'][0]
OFF = 1.96
bit = lambda k: [int(v) for v in re.findall(r'\d+', k)]
rep = {}
for c in cap['cores']:
    m = re.search(r'u_eA(\d)$', c['inst'])
    if not m: continue
    k = int(m.group(1)); face = 'W' if c['x'] < W / 2 else 'E'
    x0, y0, x1, y1 = c['x'], c['y'], c['x'] + c['w'], c['y'] + c['h']
    inst = 'u_b.g_a[%d].' % k
    grp = sorted([n for n, (x, y) in rs.items() if n.startswith(inst) and ((face == 'W' and x < x0) or (face == 'E' and x > x1))], key=bit)
    pins = S.face_pos(c, face, -1e18, 1e18)
    assert len(grp) == len(pins), (c['inst'], len(grp), len(pins))
    pins = sorted(pins)
    xr = round(x0 - OFF, 4) if face == 'W' else round(x1 + OFF, 4)
    for n, py in zip(grp, pins): rs[n] = [xr, round(py, 4)]
    rep[c['inst']] = dict(face=face, n=len(grp), x=xr, y=[round(min(pins), 2), round(max(pins), 2)])
t['note'] = t.get('note', '') + ' | HEAD-97 rp21: outline-strip relays one per pin (pin registers, REACH-TOOL-3 reading)'
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n')
print(json.dumps(rep))
