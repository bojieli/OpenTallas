# DIE-QC-36: regenerate clock_base_resite.json with the row-keyed shift (bug fix: (net,x)-keyed shift moved 175 extra stacks)
import json, re, sys
old_t, new_t, net_p, lef_p, base_p, out_p = sys.argv[1:7]
old = json.load(open(old_t))['sites']; new = json.load(open(new_t))['sites']; text = open(net_p).read(); lef = open(lef_p).read()
pinnet = {n: (m, dict(re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', p))) for m, n, p in re.findall(r'(?m)^\s*(\w+_ASAP7_75t_R)\s+(\w+)\s*\(([^;]+)\);', text)}
acc = {}
def la(master):
    if master in acc: return acc[master]
    body = re.search(r'(?ms)^MACRO\s+'+re.escape(master)+r'\s*\n(.*?)^END\s+'+re.escape(master)+r'\s*$', lef)[1]; d = {}
    for pin in ('A', 'Y'):
        pm = re.search(r'(?ms)^\s*PIN\s+'+pin+r'\s*\n(.*?)^\s*END\s+'+pin+r'\s*$', body)
        rects = [tuple(map(float, r)) for l, c in re.findall(r'LAYER\s+(\w+)\s*;(.*?)(?=LAYER|\Z)', pm[1], re.S) if l == 'M1' for r in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', c)]
        ty = .09 if pin == 'A' else .18
        bars = [r for r in rects if r[3]-r[1] > r[2]-r[0] and r[2]-r[0] >= .0179 and r[1]+.008 <= ty <= r[3]-.008]
        ch = min(bars, key=lambda r: r[0]) if pin == 'A' else max(bars, key=lambda r: r[2]); d[pin] = (ch[0]+ch[2])/2
    acc[master] = d; return d
shift = {}
for k in new:
    d = round(new[k][0]-old[k][0], 6)
    if abs(d) > 1e-9:
        m, pp = pinnet['ck_'+k]
        for p in ('A', 'Y'): shift[(pp[p], round(old[k][0]+la(m)[p], 3), round(old[k][1], 2))] = d
base = json.load(open(base_p)); out = []; n = 0
for i in range(0, len(base), 7):
    g = base[i:i+7]; cx = round((g[0][2]+g[0][4])/2, 3); cy = (g[0][3]+g[0][5])/2
    d = shift.get((g[0][0], cx, round(cy-.135, 2)), 0.0); n += bool(d)
    out += [[r[0], r[1], r[2]+d, r[3], r[4]+d, r[5]] for r in g]
json.dump(out, open(out_p, 'w')); print('stacks', len(base)//7, 'shifted', n, 'expected', len(shift))
