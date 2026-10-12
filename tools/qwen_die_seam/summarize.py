#!/usr/bin/env python3
"""el1011-qseam: verdict of one seam-bench run (expect.json from gen_bench.py + the simulator log) -> JSON.

A seam monitor PASSES when it saw >= 1 transaction, every transaction left identical, in order, at the contract
latency (errors 0), and nothing is left in flight (in == out).  The bench PASSES when every monitor passes, every
tree node paired every word (array), every root matched the golden reduction in order (array), every tile emitted
all its words on time (array), every credit lane delivered all words with no overflow / excess (credit), and the
simulation reached its END line.

    summarize.py --expect DIR/expect.json --log DIR/sim.log --out DIR/verdict.json
"""
import argparse, collections, json, re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--expect', required=True)
    ap.add_argument('--log', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    E = json.load(open(a.expect))
    mons = {m['id']: m for m in E['monitors']}
    log = open(a.log, errors='replace').read()
    seen = {}
    for m in re.finditer(r'^MON (\d+) (\d+) (\d+) (\d+) (\d+)$', log, re.M):
        seen[int(m[1])] = tuple(map(int, m.groups()[1:]))
    cls = collections.defaultdict(lambda: dict(seams=0, passed=0, failed=0, transactions=0, relays=0, failures=[]))
    for i, m in mons.items():
        c = cls[m['cls']]
        c['seams'] += 1
        c['relays'] += m.get('K', 0) + m.get('pad', 0)
        nin, ntx, nerr, left = seen.get(i, (0, 0, 1, 0))
        c['transactions'] += ntx
        ok = i in seen and nin > 0 and nerr == 0 and left == 0 and nin == ntx
        c['passed' if ok else 'failed'] += 1
        if not ok and len(c['failures']) < 5:
            c['failures'].append(dict(bus=m['bus'], K=m.get('K'), lat=m['lat'], nin=nin, ntx=ntx, errors=nerr, left=left))
    extra = {}
    nodes = [tuple(map(int, x)) for x in re.findall(r'^NODE (\d+) (\d+) (\d+)$', log, re.M)]
    if nodes:
        extra['nodes'] = dict(n=len(nodes), pairs=sum(x[1] for x in nodes), mismatches=sum(x[2] for x in nodes),
                              nodes_with_mismatch=sum(1 for x in nodes if x[2]))
    roots = [tuple(map(int, x)) for x in re.findall(r'^ROOT (\d+) (\d+) (\d+)$', log, re.M)]
    if roots:
        ng = E['meta'].get('tree_words_per_tile')
        extra['roots'] = dict(n=len(roots), words=sum(x[1] for x in roots), errors=sum(x[2] for x in roots),
                              complete=sum(1 for x in roots if x[1] == ng and x[2] == 0))
    extra['tile_errors'] = len(re.findall(r'^TILE_ERR', log, re.M))
    lanes = [tuple(map(int, x)) for x in re.findall(r'^LANE (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (-?\d+) (\d+)$', log, re.M)]
    if lanes:
        n = E['meta']['transactions_per_lane']
        cr = {i: v['credits_round_trip'] + E['meta']['extra_credits'] for i, v in enumerate(E['meta']['lanes'].values())}
        extra['lanes'] = dict(n=len(lanes), errors=sum(x[7] for x in lanes),
                              complete=sum(1 for x in lanes if x[1] == n and x[2] == n and x[3] == n and x[4] == 0 and x[5] == 0
                                           and x[6] == cr[x[0]] and x[7] == 0))
    m = re.search(r'^READY xw=(\d) xe=(\d)', log, re.M)
    if m:
        extra['station_ready_at_vm'] = [int(m[1]), int(m[2])]
    ended = bool(re.search(r'^QSEAM_\w+ END', log, re.M))
    ok = ended and all(c['failed'] == 0 for c in cls.values())
    if 'nodes' in extra:
        ok = ok and extra['nodes']['mismatches'] == 0 and extra['roots']['complete'] == extra['roots']['n'] and extra['tile_errors'] == 0 \
            and extra.get('station_ready_at_vm') == [1, 1]
    if 'lanes' in extra:
        ok = ok and extra['lanes']['complete'] == extra['lanes']['n']
    first = re.findall(r'^(?:SEAM_ERR|PAIR_MISMATCH|ROOT_ERR|BUFFER_OVERFLOW|CREDIT_EXCESS|WORD_MISMATCH|TILE_ERR).*$', log, re.M)[:4]
    V = dict(verdict='PASS' if ok else 'FAIL', ended=ended, meta=E['meta'], classes=cls, **extra, first_errors=first)
    json.dump(V, open(a.out, 'w'), indent=1)
    print(json.dumps(dict(verdict=V['verdict'], classes={k: (v['passed'], v['seams'], v['transactions']) for k, v in cls.items()},
                          **{k: v for k, v in extra.items()}, first_errors=first))[:1500])


if __name__ == '__main__':
    main()
