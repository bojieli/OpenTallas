"""S81-ROMOPT-C: test the k-class emission model on PV traces: in hw slot order (ascending class), E = rule(s) for elements whose class rules are pairwise >= 2 edges apart, rule(s) = e0 + last_beat(s) + off(pair) + seg_extra(s).  python3 pvfit3.py DIR...  -> words, mismatches"""
import collections, gzip, json, re, sys
from pathlib import Path
tot = mis = 0; ex = []; nsep = collections.Counter()
byshape = collections.Counter()
for d in sys.argv[1:]:
    for m in sorted(Path(d).glob('p*/meta.json')):
        meta = json.loads(m.read_text()); em = meta['plan']['emission']
        rule = lambda p, s: em['e0'] + em['last_beat'][s] + em['off'][str(p)] + em['seg_extra'][s]
        cls = collections.defaultdict(list)
        for x in meta['plan']['placement']:
            cls[x['pair']].append(x['seg'])
        pred, sep = {}, {}
        for p, ss in cls.items():
            rs = sorted(rule(p, s) for s in ss)
            sep[p] = all(b - a >= 2 for a, b in zip(rs, rs[1:]))
            for s in ss:
                pred[(p, s)] = rule(p, s)
        txt = gzip.open(m.parent / 'run_pv.log.gz', 'rt').read()
        for g in re.finditer(r'^PV (\d+) (\S+) ([01]+) rows (\d+) (\d+) seg (\d+) (\d+) n (\d+)', txt, re.M):
            e, path, bits, r0, r1, s0, s1, n = g.groups(); p = int(re.search(r'u_e(\d+)', path).group(1))
            for bit, sg in zip(bits[::-1], (s0, s1)):
                if bit != '1': continue
                if not sep[p]:
                    nsep[pred[(p, int(sg))] == int(e)] += 1; continue
                tot += 1; byshape[(meta['fmt'], meta['K'])] += 1
                if pred[(p, int(sg))] != int(e):
                    mis += 1; ex.append((m.parent.name, p, sg, e, pred[(p, int(sg))], sorted(cls[p]), em['last_beat']))
print('PVFIT3', ' '.join(sys.argv[1:]), 'separated_words', tot, 'unseparated(exact,shifted)', (nsep[True], nsep[False]), 'mismatch', mis, dict(byshape), ex[:5])
