#!/usr/bin/env python3
"""H-DIE-R8 10-17 (coordinator 0dg (1)): SFU LG relay chains sfr_<q><k>_{f,b} from R=11 to R stages (default 14) as a
full_die_v16 revision layer, and the SFU core LG_PATH = 1 + R (ot_hgi_sfu_lg_relay / ot_hgi_sfu_split_engine: LG_PATH =
1 pair-leaf edge + R die relays; the bridge returns READ_RETURN = 14 + 2*(LG_PATH+1), WRITE_RETURN = 11 + 2*(LG_PATH+1)).

Why: the 4 pair leaves of a quadrant span x 642..11575 um (10.9 mm); with the core in the row middle the farthest leaf is
~5.6 mm away, ceil(5572 / 405) = 14 relay hops at the measured reach.  R = 11 cannot meet the reach from any core
position (2 x 11 x 405 = 8.9 mm < 10.9 mm).  Price: +3 edges each way = +6 stream edges (5.0 ns) per SFU LG VM round trip
versus R = 11 (LG_PATH 12).  NOTE: run7b carried LG_PATH 24 (the R = 23 value of 9e5ee8245) with R = 11 chains -- an
inconsistent pair; this layer sets the consistent LG_PATH = 15.

Stages are appended at the chain tails (f: before the leaf, b: before the core); die_case_v16 --replan-chains '^(rfr|sfr)_'
re-homes every stage, so the physical order along the route is the generator's, not this naming.
    sfu_r14_layer.py [--r 14] [--spec tools/hbm_die_v15/v16_specs/su_sfu.json] --out tools/hbm_die_v15/v16_layers/sfu_r14_d4f.json
"""
import argparse, copy, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RX = re.compile(r'^(sfr_(?:SW|SE|NW|NE)[0-3]_[fb])(\d{2})$')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--r', type=int, default=14)
    ap.add_argument('--spec', default=str(ROOT / 'tools/hbm_die_v15/v16_specs/su_sfu.json'))
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    s = json.loads(Path(a.spec).read_text())
    groups = {}
    for i in s['instances']:
        m = RX.fullmatch(i['name'])
        if m:
            groups.setdefault(m[1], []).append(i)
    assert len(groups) == 32 and {len(v) for v in groups.values()} == {11}, 'expected 32 R=11 chains'
    R0 = 11
    assert a.r > R0
    inst, edges, clocks, drop = [], [], [], []
    for g, old in sorted(groups.items()):
        proto = min(old, key=lambda x: x['name'])
        last = f'{g}{R0 - 1:02d}'
        for n in range(R0, a.r):
            i = copy.deepcopy(proto)
            i['name'] = f'{g}{n:02d}'; i['slot'] = None
            i['note'] = f'H-DIE-R8 SFU LG relay stage {n} of R{a.r} (coordinator 0dg: core centred, ~14 stages priced); same master as {proto["name"]}'
            inst.append(i)
            for c in s['clocks']:
                if c['inst'] == proto['name']:
                    clocks.append(dict(c, inst=i['name']))
        tail_edges = [e for e in s['edges'] if e['src'][0] == last]
        assert tail_edges, g
        # drop only the tail edges (3-element form names the consumer): a [last, 'o'] drop would also remove this layer's last -> next edge
        drop.extend(sorted({(last, 'o', e['dst'][0]) for e in tail_edges}))
        # stage-to-stage edges carry the full hbfd_rly_624 word (as the spec's own f03 -> f04), pads ride along
        width = next(e['bits'] for e in s['edges'] if e['src'][0] == f'{g}00' and RX.fullmatch(e['dst'][0]))
        chain = [last] + [f'{g}{n:02d}' for n in range(R0, a.r)]
        for x, y in zip(chain, chain[1:]):
            edges.append(dict(src=[x, 'o', 0, width], dst=[y, 'i', 0, width], bits=width, clock='stream',
                              basis=f'H-DIE-R8 SFU LG chain R{a.r} (registered stage, compiler LG_PATH {a.r + 1})'))
        for e in tail_edges:
            e2 = copy.deepcopy(e); e2['src'][0] = chain[-1]
            e2['basis'] = e['basis'] + f' | H-DIE-R8: tail moved to stage {a.r - 1} (R{a.r})'
            edges.append(e2)
    lg = 1 + a.r
    layer = dict(region=f'sfu_r{a.r}_d4f', author='Claude H-DIE-R8 10-17',
                 basis_commit=f'coordinator 0dg (1): SFU core centred among its 4 leaves, chains R11 -> R{a.r}, priced',
                 instances=inst, edges=edges, clocks=clocks, straps=[], gaps=[], drop_edges=drop,
                 param_override={f'sfucore_{q}': {'LG_PATH': lg} for q in ('SW', 'SE', 'NW', 'NE')},
                 notes=[f'R{R0} -> R{a.r}: +{a.r - R0} stages per leg, 32 legs = +{32 * (a.r - R0)} hbfd relay tiles '
                        f'(+{32 * (a.r - R0) * 624} payload FF)',
                        f'LG_PATH {lg} (= 1 + R): bridge READ_RETURN {14 + 2 * (lg + 1)} / WRITE_RETURN {11 + 2 * (lg + 1)} edges; '
                        f'vs R11 (LG_PATH 12): +{2 * (a.r - R0)} edges per SFU LG VM round trip (+{2 * (a.r - R0) * 0.8333:.2f} ns at 833 ps)',
                        'run7b carried LG_PATH 24 (the R23 value of 9e5ee8245) with R11 chains (inconsistent); this layer is consistent',
                        'sfucore SYNTH view was built at LG_PATH 24: same ports, param alias (diagnostic) until the core view is rebuilt at 15'])
    Path(a.out).write_text(json.dumps(layer, indent=1) + '\n')
    print(json.dumps(dict(chains=len(groups), added=len(inst), LG_PATH=lg, drop_edges=len(drop), edges=len(edges))))


if __name__ == '__main__':
    main()
