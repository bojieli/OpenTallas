#!/usr/bin/env python3
"""PLAN-KVv3 10-23: L1 (amended COORD 06:01, CAP MEASURED 06:1x: 400k std cells per OpenROAD run, 500k ceiling)
cells per partition + PLANNED hard cores (outline/position/pins derived from the partition plan, never bottom-up);
partition = glue + stations (<= 400k) + cores (<= 400k each).  Core cut:
  head eighth   = head<h> lanes g_t_{2e,2e+1} (lane8 + stin + stk) + g_front_{e/2} (even e) + u_kt (e = 0)
                                                                                  -> 8 cores per head
  PV pair       = pv u_g<g>_b{2k,2k+1} (2 pv_slice_t)                             -> 4 cores per PV group
then, while glue > 400k, the largest remaining leaf becomes its own core (ectlk, kvs_pc, ahub, host_rt, kvs_ctl,
pv joins ...).  A single leaf over 400k is flagged (over_cap; split its RTL or accept up to the 500k ceiling).
usage: l1_cores_v31.py STAGE1 ASBUILT PLAN_REPORT > l1_cores_v31.json

v3.1 (KV-P2 10-23): the host frame qkd_host_rt is no longer a 403k density estimate (777.6 x 518.4 um x 1.0): it is the
HOST root qkd_host_root_admission, MEASURED at 784,320 std cells hierarchical / 571k flat (results/arch/qwen_split_1014/
host_root_cluster/census, RVT TT), and it already decomposes EXACTLY (lockstep-proven, gen_cluster.py) into the
qkd_hr_cluster children below -> each child is a planned core (max 97k hier), no core over the 400k cap."""
import collections, gzip, json, re, sys
from cells_v3 import master_cells

S = json.load(gzip.open(sys.argv[1]))
import plan_v31, cells_v3  # noqa: E402
cells_v3.HARD.add('ot_qfd_serdes_112g_x6_phy')
B = plan_v31.rewrite_asbuilt(json.load(gzip.open(sys.argv[2])))[0]
ptype = json.load(open(sys.argv[3]))['part_type']
CAP = 4.0e5
HOST_CORES = {   # partition_plan.md (hier std cells; x8 adp)
    'qkd_hr_phy_adp': (6924, 8), 'qkd_hr_phy_pad': (13017, 1), 'qkd_hr_core_prompt': (40025, 1),
    'qkd_hr_core_rx': (49650, 1), 'qkd_hr_core_tx': (54742, 1), 'qkd_hr_core_guard': (47616, 1),
    'qkd_hr_core_queue': (43301, 1), 'qkd_hr_core_order': (79710, 1), 'qkd_hr_core_peer': (71728, 1),
    'qkd_hr_host_qm': (4249, 1), 'qkd_hr_ingest_eng': (97410, 1), 'qkd_hr_cdc_pc': (76242, 1),
    'qkd_hr_cdc_ch': (76392, 1), 'qkd_hr_cdc_hi': (37795, 1), 'qkd_hr_cdc_ci': (35764, 1)}


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


per = collections.defaultdict(lambda: dict(glue=0.0, cores=collections.Counter(), flat=0.0, leaves=[], host_cores=False))
for blk, (p, loc) in S['where'].items():
    b = B.get(blk) or B[blk.split('__s')[0]]
    c, how = master_cells(b['m'], b['w'], b['h'])
    r = per[p]
    if b['m'] == 'qkd_host_rt':                       # v3.1: measured cluster children = planned cores
        for ch, (cc, n) in HOST_CORES.items():
            for i in range(n):
                k = f'host.{ch}' + (f'_{i}' if n > 1 else '')
                r['cores'][k] += cc
                r['flat'] += cc
        r['host_cores'] = True
        continue
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
    needs = r['flat'] > CAP or r.get('host_cores')
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
        kinds['host_cluster_child' if k.startswith('host.') else 'head_eighth' if k.startswith('head') else 'pv_pair'] += 1
    out[t] = dict(rep=p, flat_k=round(r['flat'] / 1e3), glue_k=round(glue / 1e3), n_cores=len(cores),
                  core_k_max=round(max(cores.values()) / 1e3) if cores else 0,
                  core_k_by_kind={k: round(max(v for kk, v in cores.items()
                                               if (kk.startswith('head') and k == 'head_eighth') or
                                               (kk.startswith('pvg') and k == 'pv_pair') or
                                               (kk.startswith('host.') and k == 'host_cluster_child') or
                                               (k not in ('head_eighth', 'pv_pair', 'host_cluster_child') and
                                                any(kk == loc and m == k for _, loc, m in r['leaves']))) / 1e3)
                                  for k in kinds},
                  cores_by_kind=dict(kinds), over_cap=glue > CAP or (bool(cores) and max(cores.values()) > CAP))
tot = collections.Counter()
for p in per:
    tot['cores'] += out[ptype[p]]['n_cores']
print(json.dumps(dict(cap_cells=CAP, die_cores=tot['cores'], per_type=out), indent=1))
