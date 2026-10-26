#!/usr/bin/env python3
"""PLAN-KVv3 10-23: L1 (amended COORD 06:01, CAP MEASURED 06:1x: 400k std cells per OpenROAD run, 500k ceiling)
cells per partition + PLANNED hard cores (outline/position/pins derived from the partition plan, never bottom-up);
partition = glue + stations (<= 400k) + cores (<= 400k each).  Core cut:
  head eighth   = head<h> lanes g_t_{2e,2e+1} (lane8 + stin + stk) + g_front_{e/2} (even e) + u_kt (e = 0)
                                                                                  -> 8 cores per head
  PV pair       = pv u_g<g>_b{2k,2k+1} (2 pv_slice_t)                             -> 4 cores per PV group
then, while glue > 400k, the largest remaining leaf becomes its own core (ectlk, kvs_pc, ahub, host_rt, kvs_ctl,
pv joins ...).  A single leaf over 400k is flagged (over_cap; split its RTL or accept up to the 500k ceiling).
usage: l1_cores_v3.py STAGE1 ASBUILT PLAN_REPORT > l1_cores_v3.json"""
import collections, gzip, json, re, sys
from cells_v3 import master_cells

S = json.load(gzip.open(sys.argv[1])); B = json.load(gzip.open(sys.argv[2]))['blocks']
ptype = json.load(open(sys.argv[3]))['part_type']
CAP = 4.0e5


def core_of(loc):
    m = re.match(r'(head\d)__g_(t|front)_(\d+)__', loc)
    if m:
        e = int(m.group(3)) // 2 if m.group(2) == 't' else 2 * int(m.group(3))
        return f'{m.group(1)}_e{e}'
    if re.match(r'head\d__u_kt$', loc):
        return loc.split('__')[0] + '_e0'
    m = re.match(r'pv__u_g(\d)_b(\d)$', loc)
    if m:
        return f'pvg{m.group(1)}_p{int(m.group(2)) // 2}'
    return None


per = collections.defaultdict(lambda: dict(glue=0.0, cores=collections.Counter(), flat=0.0, leaves=[]))
for blk, (p, loc) in S['where'].items():
    b = B.get(blk) or B[blk.split('__s')[0]]
    c, how = master_cells(b['m'], b['w'], b['h'])
    r = per[p]
    r['flat'] += c
    k = core_of(loc) if r is not None else None
    if k:
        r['cores'][k] += c
    else:
        r['glue'] += c
        r['leaves'].append((c, loc, b['m']))
out = {}
for p, r in per.items():
    t = ptype[p]
    if t in out:
        continue
    needs = r['flat'] > CAP
    cores = dict(r['cores']) if needs else {}
    glue = r['glue'] if needs else r['flat']
    kinds = collections.Counter()
    for c, loc, m in sorted(r['leaves'], reverse=True):
        if glue <= CAP:
            break
        cores[loc] = c
        kinds[m] += 1
        glue -= c
    for k in r['cores'] if needs else ():
        kinds['head_eighth' if k.startswith('head') else 'pv_pair'] += 1
    out[t] = dict(rep=p, flat_k=round(r['flat'] / 1e3), glue_k=round(glue / 1e3), n_cores=len(cores),
                  core_k_max=round(max(cores.values()) / 1e3) if cores else 0,
                  core_k_by_kind={k: round(max(v for kk, v in cores.items()
                                               if (kk.startswith('head') and k == 'head_eighth') or
                                               (kk.startswith('pvg') and k == 'pv_pair') or
                                               (k not in ('head_eighth', 'pv_pair') and
                                                any(kk == loc and m == k for _, loc, m in r['leaves']))) / 1e3)
                                  for k in kinds},
                  cores_by_kind=dict(kinds), over_cap=glue > CAP or (bool(cores) and max(cores.values()) > CAP))
tot = collections.Counter()
for p in per:
    tot['cores'] += out[ptype[p]]['n_cores']
print(json.dumps(dict(cap_cells=CAP, die_cores=tot['cores'], per_type=out), indent=1))
