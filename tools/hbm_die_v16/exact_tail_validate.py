#!/usr/bin/env python3
"""Compare every actual old/narrow station data edge, removing spare positions only."""
import collections
import copy
import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v15'))
import full_die_v16 as F


def load(path):
    return json.loads(gzip.open(path, 'rt').read())


def main():
    old, new = map(load, sys.argv[1:3])
    spec = importlib.util.spec_from_file_location('old_full_die', sys.argv[3])
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    rtl = F.Rtl()
    # Parse each source once; 981 new masters share one generated source.
    for source in sorted({x['source'] for layer in (old, new) for x in layer['instances']}):
        text = F.dpb.preprocess(F.dpb.strip_comments((ROOT/source).read_text()), {})
        for mod in F.dpb.parse_modules(text, str(ROOT/source)):
            rtl.cache[(mod.name, source)] = mod
    ports = []
    for layer in (old, new):
        ports.append({x['name']: rtl.ports(x['master'], x['source'], x['params']) for x in layer['instances']})
    digest = hashlib.sha256()
    total = removed = 0
    for original, narrowed in zip(old['relay_splice_v2'], new['relay_splice_v2']):
        width = original['width']
        tails = {}
        for node in original['nodes']:
            tails[node['names'][-1]] = narrowed['lane_widths'][-1]
        for sink in original['sinks'].values():
            for stage in sink['chain']:
                tails[stage[-1]] = narrowed['lane_widths'][-1]
        def edges(bus, which):
            problems = []
            result = F.apply_relay_splice_v2([copy.deepcopy(bus)], [], ports[which], problems)
            assert all(x.startswith('relay splice v2:') for x in problems), problems
            if which == 0:
                oldproblems = []
                assert result == baseline.apply_relay_splice_v2([copy.deepcopy(bus)], [], ports[which], oldproblems), bus['bus']
                assert problems == oldproblems
            out = collections.Counter()
            for edge in result:
                src, dst = F.rng(edge['src'], ports[which]), F.rng(edge['dst'], ports[which])
                assert src[3]-src[2] == dst[3]-dst[2] == edge['bits']
                assert src[3] <= ports[which].get(src[0], {}).get(src[1], {'bits':src[3]})['bits']
                assert dst[3] <= ports[which].get(dst[0], {}).get(dst[1], {'bits':dst[3]})['bits']
                for k in range(edge['bits']):
                    a, b = src[:2]+(src[2]+k,), dst[:2]+(dst[2]+k,)
                    if which == 0:
                        converted = []
                        for ref in (a,b):
                            name, port, bit = ref
                            narrow = tails.get(name, width)
                            if name in tails and port in ('a','b','i','o','o0','o1','o2','o3'):
                                branch, offset = divmod(bit, width)
                                if offset >= narrow:
                                    break
                                ref = name,port,branch*narrow+offset
                            converted.append(ref)
                        if len(converted) != 2:
                            continue
                        a,b = converted
                    out[(a,b)] += 1
            return out
        expected, actual = edges(original,0), edges(narrowed,1)
        assert expected == actual, (original['bus'], list((expected-actual).items())[:3], list((actual-expected).items())[:3])
        assert max(actual.values(), default=0) == 1, original['bus']
        total += sum(actual.values())
        digest.update(repr(sorted(actual.items())).encode())
    assert old['clocks'] == new['clocks'] and old['edges'] == new['edges']
    # --classes re-masters the landing K straps onto the class master: identical apart from that master name
    newmaster = {x['name']: x['master'] for x in new['instances']}
    def strip(straps):
        return [{k: v for k, v in s.items() if k != 'master'} for s in straps or []]
    assert strip(old.get('straps')) == strip(new.get('straps')) and old.get('die_pins') == new.get('die_pins')
    assert all(s.get('master') in (None, newmaster.get(s['inst'])) for s in new.get('straps') or [])
    print('EXACT_TAIL_MAP_PASS', json.dumps(dict(buses=len(old['relay_splice_v2']), real_edge_bits=total, map_sha256=digest.hexdigest(), clock_reset_epoch_edges_unchanged=True)))


if __name__ == '__main__':
    main()
