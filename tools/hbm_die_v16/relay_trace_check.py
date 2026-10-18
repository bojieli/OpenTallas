#!/usr/bin/env python3
"""H-NETLIST/D4F-RELAY 10-17: full-coverage static trace check of a relay-layer contract against its LAYER=none base.

Every load bit of a non-relay instance in the FINAL contract is traced back through relay tiles (hbfd_rly_*: o / o<k> bit
j <- i bit j) to its driver bit; the same is done in the BASE contract.  PASS needs, for every load bit:
  * the same driver bit in both (the relay layer changes no connectivity, spare lanes feed only relay inputs);
  * final depth == base depth + the compiler's sink_edges for that (bus, sink) (relay layer report) -- 0 when unrelayed;
  * every relay tile of the final contract lies on some traced path (no dangling or dead relays);
and, per fixed-depth chain (rfr_* / sfr_*), the final chain depth == the base depth (or the --chain-depth override,
e.g. sfr=21 once the SFU leg latency is raised).
    relay_trace_check.py --base BASE.json.gz --final FINAL.json[.gz] --report relays_d4f_report.json [--chain-depth sfr=21]
"""
import argparse, collections, gzip, json, re, sys
from pathlib import Path


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


def is_rly(m):
    return m.startswith('hbfd_rly_')


def tracer(c):
    I = c['instances']; drv = {}
    for e in c['edges']:
        s, d = e['source'], e['sink']
        for k in range(s[3] - s[2]):
            drv[(d[0], d[1], d[2] + k)] = (s[0], s[1], s[2] + k)
    used = set()

    def trace(b):
        n = 0; seen = 0
        while True:
            src = drv.get(b)
            if src is None:
                return None, n
            if not is_rly(I[src[0]]['master']):
                return src, n
            used.add(src[0]); n += 1; seen += 1
            if seen > 10000:
                return 'LOOP', n
            b = (src[0], 'i', src[2])
    loads = [b for b in drv if not is_rly(I[b[0]]['master'])]
    return trace, loads, used, I


def chain_depths(c, pat):
    I = c['instances']; succ = collections.defaultdict(set); pred = collections.defaultdict(set)
    rel = {n for n in I if pat.match(n)}
    for e in c['edges']:
        s, d = e['source'][0], e['sink'][0]
        if s in rel and d in rel:
            succ[s].add(d); pred[d].add(s)
    out = {}
    for h in rel:
        if pred[h]:
            continue
        n, x = 1, h
        while succ[x]:
            x = next(iter(succ[x])); n += 1
        out[re.sub(r'\d+$', '', h)] = n
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', required=True); ap.add_argument('--final', required=True); ap.add_argument('--report', required=True)
    ap.add_argument('--chain-depth', action='append', default=[], help='prefix=depth override (e.g. sfr=21)')
    ap.add_argument('--json')
    a = ap.parse_args()
    B, F, rep = load(a.base), load(a.final), load(a.report)
    tb, lb, _, IB = tracer(B); tf, lf, used, IF = tracer(F)
    # expected extra depth per (driver inst, sink inst) of each relayed bus
    exp = {}
    lay_bits = {}
    for x in rep['compiler']:
        di = x['driver'].split('.', 1)[0]
        for s_, d_ in x['sink_edges'].items():
            exp[(x['bus'], s_)] = d_
    if rep.get('splice_loads'):
        lay_bits = {tuple(k): v for k, v in rep['splice_loads']}
    errs = collections.Counter(); ex = collections.defaultdict(list); n = 0; relayed = 0
    lbset = set(lb)
    for b in lf:
        n += 1
        if b not in lbset:
            errs['load bit not in base'] += 1; ex['load bit not in base'].append(b); continue
        (sb, db), (sf, df) = tb(b), tf(b)
        if sb != sf:
            errs['driver bit differs'] += 1; ex['driver bit differs'].append((b, sb, sf)); continue
        want = db + lay_bits.get(b, 0)
        if lay_bits.get(b):
            relayed += 1
        if df != want:
            errs['depth != base + sink_edges'] += 1; ex['depth != base + sink_edges'].append((b, db, df, want))
    for b in lbset - set(lf):
        errs['base load bit missing in final'] += 1; ex['base load bit missing in final'].append(b)
    rly = {k for k, v in IF.items() if is_rly(v['master'])}
    dead = sorted(rly - used)
    if dead:
        errs['relay tile on no traced path'] += len(dead); ex['relay tile on no traced path'] = dead[:10]
    ov = dict(x.split('=') for x in a.chain_depth)
    pat = re.compile(r'^(rfr|sfr)_')
    cb, cf = chain_depths(B, pat), chain_depths(F, pat)
    chain_bad = {}
    for k, d0 in cb.items():
        want = int(ov.get(k.split('_')[0], d0))
        if cf.get(k) != want:
            chain_bad[k] = (d0, cf.get(k), want)
    if chain_bad:
        errs['fixed chain depth'] += len(chain_bad); ex['fixed chain depth'] = list(chain_bad.items())[:10]
    ok = not errs
    res = dict(schema='opentallas.hbm.relay_trace_check.v1', verdict='PASS' if ok else 'FAIL', load_bits=n, relayed_load_bits=relayed,
               relay_tiles=len(rly), chains=len(cb), chain_depths=dict(sorted(cf.items())), errors=dict(errs),
               examples={k: [str(x) for x in v[:5]] for k, v in ex.items()})
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1) + '\n')
    print(f"RELAY_TRACE_CHECK {res['verdict']} load_bits={n} relayed={relayed} relay_tiles={len(rly)} chains={len(cb)} "
          f"chain_depths={sorted(set(cf.values()))} errors={dict(errs)}")
    for k, v in res['examples'].items():
        print(' ', k, v[:3])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
