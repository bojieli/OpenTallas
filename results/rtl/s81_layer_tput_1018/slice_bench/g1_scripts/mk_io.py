import json, sys
cut, out = sys.argv[1], sys.argv[2]
P = json.load(open(f'{cut}/tb_ports.json'))
ix = {p['port']: p['index'] for p in P}
lanes = {'xrW_3S_l0': (276, 10), 'xrW_2S_l3': (276, 10), 'r_f_3L01': (70, 4)}   # compiler age_edges = ceil(n/2)+E+1
K0 = 100
with open(f'{out}/in.txt', 'w') as f:
    for c in (K0, K0 + 1):
        for ln in lanes:
            f.write(f"{c} {ix['i__w_' + ln + '_src']} {'6789' if c == K0 else '0'}\n")
rows = []
for ln, (w, age) in lanes.items():
    m = format((1 << w) - 1, 'x'); p = ix['o__w_' + ln + '_lnd']
    e = K0 - 1 + age      # event at k = source register launch at edge k-1; o sampled after edge (k-1+age)
    rows += [(e - 1, p, m, '0'), (e, p, m, '6789'), (e + 1, p, m, '0')]
with open(f'{out}/out.txt', 'w') as f:
    for r in sorted(rows):
        f.write('%d %d %s %s\n' % r)
