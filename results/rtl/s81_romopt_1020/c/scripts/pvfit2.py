"""S81-ROMOPT-C: fit k-class PV traces: key every pv word by (pair, row, seg from the PV line); report d per
(shape, element class set, slot j, seg) -- python3 pvfit2.py DIR..."""
import collections, gzip, json, re, sys
from pathlib import Path
out = collections.defaultdict(lambda: collections.defaultdict(set))
for d in sys.argv[1:]:
    for m in sorted(Path(d).glob('p*/meta.json')):
        meta = json.loads(m.read_text()); em = meta['plan']['emission']
        slots, cls = {}, collections.defaultdict(list)
        for x in meta['plan']['placement']:
            slots[(x['pair'], x['super_row'], x['seg'])] = (x.get('slot', 0), x.get('slots', 1)); cls[x['pair']].append(x['seg'])
        txt = gzip.open(m.parent / 'run_pv.log.gz', 'rt').read()
        shape = (meta['fmt'], meta['K'], meta['nseg'])
        for g in re.finditer(r'^PV (\d+) (\S+) ([01]+) rows (\d+) (\d+) seg (\d+) (\d+) n (\d+)', txt, re.M):
            e, path, bits, r0, r1, s0, s1, n = g.groups(); p = int(re.search(r'u_e(\d+)', path).group(1))
            for mb, (bit, row, sg) in enumerate(zip(bits[::-1], (r0, r1), (s0, s1))):
                if bit != '1': continue
                rr = int(row) & 0x3FFF; s = int(sg)
                if (p, rr // 2, s) not in slots:
                    print('UNPLACED', m.parent.name, p, rr, s); continue
                j, nn = slots[(p, rr // 2, s)]
                dd = int(e) - (em['e0'] + em['last_beat'][s] + em['off'][str(p)] + em['seg_extra'][s])
                out[shape][(tuple(sorted(cls[p])), j, s, mb)].add(dd)
for shape, t in out.items():
    print('SHAPE', shape, 'last_beat', em['last_beat'] if shape == (meta['fmt'], meta['K'], meta['nseg']) else '')
    for k in sorted(t):
        print('  classes %s j %d seg %d mb %d' % k, sorted(t[k]))
