"""S81-ROMOPT-C: re-fit pvmeasure runs per phase shape (fmt, K, nseg) and per (n, j, macro): python3 pvfit.py DIR..."""
import collections, gzip, json, re, sys
from pathlib import Path
out = collections.defaultdict(lambda: collections.defaultdict(set))
cnt = collections.Counter()
for d in sys.argv[1:]:
    for m in sorted(Path(d).glob('p*/meta.json')):
        meta = json.loads(m.read_text()); em = meta['plan']['emission']
        slots = {(x['pair'], x['super_row']): (x['seg'], x.get('slot', 0), x.get('slots', 1)) for x in meta['plan']['placement']}
        txt = gzip.open(m.parent / 'run_pv.log.gz', 'rt').read()
        shape = (meta['fmt'], meta['K'], meta['nseg'])
        for g in re.finditer(r'^PV (\d+) (\S+) ([01]+) rows (\d+) (\d+) seg (\d+) (\d+) n (\d+)', txt, re.M):
            e, path, bits, r0, r1, s0, s1, n = g.groups(); p = int(re.search(r'u_e(\d+)', path).group(1))
            for mb, (bit, row) in enumerate(zip(bits[::-1], (r0, r1))):
                if bit != '1': continue
                rr = int(row) & 0x3FFF; s, j, nn = slots[(p, rr // 2)]
                dd = int(e) - (em['e0'] + em['last_beat'][s] + em['off'][str(p)] + em['seg_extra'][s])
                out[shape][(nn, j, s)].add(dd); cnt[(shape, nn, j, s)] += 1
for shape, t in out.items():
    print('SHAPE', shape)
    for k in sorted(t):
        print('  n %d j %d seg %d' % k, sorted(t[k]), cnt[(shape,) + k])
