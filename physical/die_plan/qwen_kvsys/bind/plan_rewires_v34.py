#!/usr/bin/env python3
"""KV-P4 10-23: the as-built -> plan connectivity rewrites that KV plan v3.1+ declares in plan_v31.rewrite_asbuilt (BINDER2
13:50 UNPLANNED 28,670 b: 28,485 b of it are these rewrites, which the binder must APPLY, not report):
  (1) astk relabel: astk chain position p serves the head group of plan row p, i.e. every ectl_Q_k <-> astk ep/owner edge
      moves from chain position k to PINV[k] (compiler/static-schedule relabel; the chain order is unchanged);
  (2) S-quadrant host slice chains (hsl_WS_*/hsl_ES_*) take the N-quadrant orientation: master qkd_hslice -> qkd_hslice_dn,
      every chain link n -> n+1 reversed, host <-> hsl_0 becomes host <-> hsl_31 (head 31, like N);
  (3) HBM PHY models split into 8 x 4-PC slices (phy_Q -> phy_Q__s<k>; already in asbuilt.json substitutes).
Output bind/plan_rewires_v34.json: per class, the as-built edges removed and the plan edges added (block names as in
asbuilt_rtl6 / stage1 'where'), plus module substitutions.  Fault-tree edges (v32) are in plan_cell_conns_v34.json.
    python3 bind/plan_rewires_v34.py"""
import collections
import copy
import gzip
import json
import re
import sys
from pathlib import Path

D = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(D))
import plan_v33  # noqa: E402,F401
import plan_v31 as pv  # noqa: E402

raw = json.load(gzip.open(D / 'asbuilt_rtl6_e33504a6f.json.gz'))
asb = copy.deepcopy(raw)
B, moved = pv.rewrite_asbuilt(asb)
key = lambda e: (e['s'], e['sp'], e['d'], e['dp'])
R = collections.Counter(key(e) for e in raw['edges'])
N = collections.Counter(key(e) for e in asb['edges'] if not e.get('v32'))
bits = {key(e): e['bits'] for e in raw['edges']}
bits.update({key(e): e['bits'] for e in asb['edges']})


def cls(k):
    s, sp, d, dp = k
    if re.match(r'(astk_\w\w__u_strip.*g_(ep|owner)_\d)', s + ' ' + d) or 'ectl_' in s + d and 'astk_' in s + d:
        if ('ectl_' in s or 'ectl_' in d) and ('astk_' in s or 'astk_' in d):
            return 'astk_ectl_relabel'
    if re.match(r'hsl_(WS|ES)_', s) or re.match(r'hsl_(WS|ES)_', d):
        return 'hsl_S_orientation'
    if s.startswith('phy_') or d.startswith('phy_'):
        return 'phy_slices'
    if 'serdes' in s + d or 'ucie' in s + d or 'd2d_kv' in s + d:
        return 'fdi_split'
    return 'v32_removed_fault_or_and_relay_gathers'  # replaced by plan_cell_conns_v34 (fault) and the relay leaves (bitcon)


out = collections.defaultdict(lambda: dict(removed=[], added=[]))
for k, n in (R - N).items():
    out[cls(k)]['removed'].append(dict(zip(('s', 'sp', 'd', 'dp'), k), bits=bits[k], n=n))
for k, n in (N - R).items():
    out[cls(k)]['added'].append(dict(zip(('s', 'sp', 'd', 'dp'), k), bits=bits[k], n=n))
subst = sorted({(n, b['m']) for n, b in B.items() if re.match(r'hsl_(WS|ES)_\d+$', n)})
res = dict(schema='opentallas.kv_p4.plan_rewires.v1', source='plan_v31.rewrite_asbuilt (+ v3.2/v3.3 patches), asbuilt rtl6 e33504a6f',
           note=__doc__.split('\n\n')[0], module_substitutions=[dict(inst=n, module=m, was='qkd_hslice') for n, m in subst],
           summary={c: dict(removed=len(v['removed']), removed_bits=sum(x['bits'] for x in v['removed']),
                            added=len(v['added']), added_bits=sum(x['bits'] for x in v['added'])) for c, v in out.items()},
           classes={c: dict(removed=sorted(v['removed'], key=json.dumps), added=sorted(v['added'], key=json.dumps)) for c, v in out.items()})
(D / 'bind' / 'plan_rewires_v34.json').write_text(json.dumps(res, indent=0) + '\n')
print(json.dumps(res['summary'], indent=1), 'subst', len(subst))
