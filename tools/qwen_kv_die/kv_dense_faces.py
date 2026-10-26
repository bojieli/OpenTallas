"""KV-BIND9 10-20 (COORD 08:20 die checklist): actual pin-to-pin audit (kv_lane_reach.audit, LEF pin rects of the case's
elements.lef = REAL bound views where libs/views.json binds them, stand-in frames otherwise) of every net incident to the
dense-face tiles (HBM PHYs, UCIe PHY, d2d, host root / SerDes).  Per dense tile: data bits, max hop (um), bits > 405 um,
real/stand-in for the tile and its peers.  Clock / reset / PLL distribution excluded (CTS-qualified, not data).
usage: dense_faces2.py RUN TOOLS_DIR OUT.json"""
import json, re, sys, collections
R, T, OUT = sys.argv[1:4]
sys.path.insert(0, T)
import kv_lane_reach as LR
case = R + '/case_kv'
die = open(case + '/die.v').read()
place = open(case + '/place.tcl').read()
lef = open(case + '/elements.lef').read()
views = json.load(open(R + '/libs/views.json'))['views']
real = {m for m, v in views.items() if v.get('bound')}
from kv_fwd_lanes import INST
inst = {}
for line in die.splitlines():
    m = INST.match(line)
    if m:
        inst[m[3]] = m[2]
DENSE = re.compile(r'hbm3e_phy|ucie|qkd_d2ds|d2d_static|serdes|host_rt')
dense = sorted(n for n, mm in inst.items() if DENSE.search(mm))
print('dense tiles', [(n, inst[n]) for n in dense])
rep = LR.audit(die, lef, place, place, dict(changes=[]), [(100000, 405.0)], extra=dense)
CLK = re.compile(r'^(ck|clk|hck|pll|rst)|_ck$|clk|^ck_|rst_n|_rst', re.I)
agg = collections.defaultdict(lambda: dict(bits=0, max_um=0.0, gt405=0, peers=collections.Counter(), standin_peers=set(), worst=None))
for g in rep['groups']:
    (si, sp), (di, dp) = g['src'], g['dst']
    if CLK.search(sp) or CLK.search(dp):
        continue
    for a, ap, b, bp in ((si, sp, di, dp), (di, dp, si, sp)):
        if a not in dense:
            continue
        r = agg[a]
        r['bits'] += g['bit_pairs']
        r['gt405'] += g['after_overreach_bits']
        if g['after_max_um'] > r['max_um']:
            r['max_um'] = g['after_max_um']; r['worst'] = f'{a}.{ap} <-> {b}.{bp} ({inst.get(b)})'
        r['peers'][inst.get(b, '?')] += g['bit_pairs']
        if inst.get(b) not in real:
            r['standin_peers'].add(inst.get(b))
rows = [dict(inst=a, master=inst[a], view='REAL' if inst[a] in real else 'STANDIN', bits=r['bits'], max_um=round(r['max_um'], 1),
             bits_gt405=r['gt405'], worst=r['worst'], standin_peers=sorted(map(str, r['standin_peers'])), peers=r['peers'].most_common(6))
        for a, r in sorted(agg.items())]
json.dump(dict(schema='kv_bind9.dense_faces.v2', run=R, unmeasured=len(rep['unmeasured']), rows=rows), open(OUT, 'w'), indent=1)
print('unmeasured pairs', len(rep['unmeasured']))
for r in rows:
    print(f"{r['inst']:>10} {r['master']:<24} {r['view']:<7} bits {r['bits']:>6} max {r['max_um']:>8} um >405 {r['bits_gt405']:>5} worst {r['worst']} standin peers {r['standin_peers'][:5]}")
