import sys, re, json, collections
sys.path.insert(0, '/w')
import geom_rules as G
D = G.Design(sys.argv[1])
pairs = []
m = G.r2r_metrics(D, capture_pairs=pairs)
def cls(n):
    n = n.replace('\\', '')
    mm = re.match(r'u_bin_([A-Za-z0-9_]+?)/', n) or re.match(r'u_bin_([A-Za-z0-9_]+)', n)
    if n.startswith('u_bin_'): return 'IN:' + re.sub(r'(/|\.|\[).*', '', n[6:])
    if n.startswith('u_bout') or n.startswith('u_bmid'): return 'OUTFACE'
    if n.startswith('u_brst'): return 'RST'
    return 'CORE:' + '.'.join(n.split('.')[:4])
c = collections.Counter(); cc = collections.Counter(); worst = {}
for p in pairs:
    k = cls(p['launch']); kc = cls(p['capture'])
    c[k] += 1; cc[(k.split(':')[0], kc.split(':')[0] if kc.startswith(('IN','OUT','RST')) else 'CORE')] += 1
    if p['distance_um'] > worst.get(k, (0,))[0]: worst[k] = (p['distance_um'], p['launch'], p['capture'])
print(json.dumps(dict(metrics={k: m[k] for k in ('r2r_max','r2r_captures_gt405','r2r_captures')},
  by_launch_class=dict(sorted(((k, v) for k, v in collections.Counter(k.split(':')[0] for k in c.elements()).items()))),
  by_pair=[[a, b, v] for (a, b), v in cc.most_common()],
  top_launch=[[k, v, worst[k][0], worst[k][1][:120], worst[k][2][:120]] for k, v in c.most_common(40)]), indent=1))
