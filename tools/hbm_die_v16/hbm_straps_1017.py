#!/usr/bin/env python3
"""HBM-TIE 2026-10-17 (stub audit 0da): classify every constant input bit (straps + pads) of an HBM die contract.

Coordinator 0da rulings: (a) identity / position straps accepted, listed per die; (b) tied-low spare bits of quantized
(dedupe) relays accepted only if no consumer reads them -- checked here by following each padded bit through the relay
chain to its first non-relay sink; (c) ties of provably unused modes accepted, listed; (d) functional configuration
straps REJECTED (must come from a real producer).
usage: hbm_straps_1017.py CONTRACT.json OUT.json
"""
import json
import sys
from collections import defaultdict

IDENTITY = {'tgt': 'F20 target id of this target instance', 'pc_id': 'pseudo-channel index of this controller',
            'bid': 'VM bank index', 'sid': 'VM slice / quadrant index', 'id_sm': 'SM index of the service group',
            'id_stack': 'HBM stack index of the service group', 'sm': 'SM index', 'bank_id': 'VM bank index',
            'stk': 'HBM stack index', 'qid': 'collective quadrant index', 'quad': 'quadrant index',
            'first_ord': 'key ordinal base of this scorer slot (slot k owns keys [342 k, 342 k + 342))'}
POSITION = {'rret': 'read-return edge of this LG tap = fixed relay depth of its placed position (compiler table)',
            'wret': 'write-return edge of this LG tap = fixed relay depth of its placed position (compiler table)'}
UNUSED = {('ot_hbm_idx_selector_static', 'in_line'):
          'selector quarters 2-3: the TP192 die has N_Q=2 scorer slots, so the upper 1,184 b carry no scorer; an all-zero '
          'line has valid=0 in every entry, so it adds nothing to the histograms, compaction or emit. Successor: an NQ=2 '
          'selector variant (drops these pins and 6 of the 12 256x256 SRAMs).'}
REJECT = {'refresh_reload', 'k'}


def relay_reads(c, pads):
    out = defaultdict(list)
    for e in c['edges']:
        out[(e['source'][0], e['source'][1])].append(e)
    inst = c['instances']
    reads = []

    def walk(n, lo, hi):
        for e in out.get((n, 'o'), []):
            s0, s1 = e['source'][2], e['source'][3]
            a, b = max(lo, s0), min(hi, s1)
            if a >= b:
                continue
            d = e['sink']
            dlo, dhi = d[2] + a - s0, d[2] + b - s0
            if inst[d[0]]['master'].startswith('hbfd_rly'):
                walk(d[0], dlo, dhi)
            else:
                reads.append([n, d[0], d[1], dlo, dhi])
    for p in pads:
        walk(p['inst'], p['lo'], p['hi'])
    return reads


def main():
    c = json.load(open(sys.argv[1]))
    rows = defaultdict(lambda: dict(instances=0, bits=0))
    pads = []
    for s in c['straps']:
        b = s['hi'] - s['lo']
        if str(s.get('reason', '')).startswith('PAD'):
            pads.append(s)
            key, cls, why = (s['master'], s['port']), 'b_PAD', 'dedupe relay spare bits'
        elif s['port'] in REJECT:
            key, cls, why = (s['master'], s['port']), 'd_REJECTED', 'functional configuration strap'
        elif (s['master'], s['port']) in UNUSED:
            key, cls, why = (s['master'], s['port']), 'c_UNUSED_MODE', UNUSED[(s['master'], s['port'])]
        elif s['port'] in IDENTITY:
            key, cls, why = (s['master'], s['port']), 'a_IDENTITY', IDENTITY[s['port']]
        elif s['port'] in POSITION:
            key, cls, why = (s['master'], s['port']), 'a_POSITION', POSITION[s['port']]
        else:
            key, cls, why = (s['master'], s['port']), 'UNCLASSIFIED', s.get('reason', '')
        r = rows[key + (cls,)]
        r.update(master=key[0], port=key[1], cls=cls, why=why)
        r['instances'] += 1
        r['bits'] += b
    reads = relay_reads(c, pads)
    tot = defaultdict(int)
    for r in rows.values():
        tot[r['cls']] += r['bits']
    json.dump(dict(schema='opentallas.hbm.straps-1017.v1', contract=sys.argv[1], constant_bits=sum(tot.values()),
                   by_class=tot, pad_bits_read_by_a_consumer=reads, rows=sorted(rows.values(), key=lambda r: (r['cls'], -r['bits']))),
              open(sys.argv[2], 'w'), indent=1)
    for k in sorted(tot):
        print(f'{k:14s} {tot[k]}')
    print(f'constant bits {sum(tot.values())}; pad bits reaching a non-relay consumer: {len(reads)}')
    return 1 if (tot.get('d_REJECTED') or tot.get('UNCLASSIFIED') or reads) else 0


if __name__ == '__main__':
    sys.exit(main())
