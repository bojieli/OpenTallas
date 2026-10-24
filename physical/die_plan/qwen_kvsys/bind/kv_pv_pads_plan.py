#!/usr/bin/env python3
"""KV-P6-V37 10-23 (from kv_pv_pads.py, KV-P6-PV): PV trunk landing-pad LP with re-routed V / header / cmd depths
(--option model or --plan/--lat plan lanes, see kv_pv_route.py).  Original doc:
KV-P6-PV 10-23: PV trunk landing-pad table for the FIRST functional proof (KV-P6 decision: option (c), COORD R8 PAD
BUDGET ruling) -- minimum pads that restore the as-built PV schedule on the bound lanes.

    kv_pv_pads_plan.py BIND_DIR R8_TABLE OUT.json [--option v36|turn7|turnC|mid] [--plan PLAN --lat LAT]

Model (integer LP, scipy highs).  Every pv_<S|N>_<n> partition keeps its as-built internals, so all its leaves (slices,
joins, result-trunk T units, the vport inside it) move by ONE offset t_P against the as-built schedule.  A crossing
member src -> sink must then land at  landed - asbuilt = t(sink) - t(src);  pad = landed - bound >= 0.
INNER:<part>:... members are intra-partition edges the binder emulates with ot_dp_dly (as-built depth = 'asbuilt'); their
'landed' is the NEW internal delay (bound 0 = direct); BINDER3 re-sizes / splits those ot_dp_dly per sink accordingly.
Endpoints: pvw_<i>__u_ctl.cmd = 0 (frame of each pair control); ctl col_valid/col_fault = t_FLG and RH (u_RH_r0) = t_RH,
both SHARED by the two pairs (one ctl type: TRUNK_D = 54 + t_RH, FLAG_D = 58 + t_FLG - t_RH; the pvfin P0/P1 cal ages
move with t_RH); ctl in_t/in_valid/in_epoch = 0 (arrival check and the cmd take share pa; only the request -> arrival distance is boot cfg_fia); external leaves (astk pe2 source, hg
read_addr sink) free.  A vport's launch moves with its host partition (internal V to its own columns), set by DQ / W
request-lane pads (boot; reported as vport_shift).  Not modelled (pad 0, timing by boot regen): rst, cfg_age, pr_t /
pr_valid (DQ), vq / rsp (RT), afv fault.
Output member schema = r8 landing members.  MERGE RULE: this table is authoritative for every member it lists (pad 0
included); BINDER3 replaces the r8 entry with the same id (sink.port[bits]<-source@asbuilt) and keeps the r8 pad for
every other member -> no member is padded twice.  'overrides' lists the r8 ids replaced with their r8 pad.
"""
import collections, json, re, sys
import numpy as np
from scipy.optimize import linprog

import argparse
ap = argparse.ArgumentParser()
ap.add_argument('bind'); ap.add_argument('r8'); ap.add_argument('out')
ap.add_argument('--option', default='bound', choices=['bound', 'v36', 'turn7', 'turnC', 'mid', 'ctlmid'])
ap.add_argument('--plan', help='v3.x die_plan.json: take V / header / cmd depths from its tap-tree lanes (+ --lat)')
ap.add_argument('--lat', help='gen.py latency json of --plan')
ap.add_argument('--entry', action='store_true', help='cost pads at the sink PARTITION ENTRY: members of one source-bit range into one partition share one delay line (fanout counted once)')
A_ = ap.parse_args()
B, R8, OUT = A_.bind, A_.r8, A_.out
land = json.load(open(B + '/bus_groups.json'))['landing']
r8 = {m['id']: m for m in json.load(open(R8))['members']}
TD_ASB, FD_ASB = 54, 58


def rid(sink, port, bits, src, asb):
    return f"{sink}.{port}[{','.join(f'{a}:{b}' for a, b in bits)}]<-{src}@{asb}"


def end(part, leaf, port, is_src, src_name):
    if re.match(r'pv_[SN]_\d+$', part):
        if not is_src and re.match(r'vport_', leaf):
            return None                     # vport inputs (pr_t / rsp / cfg): DQ / RT boot regen
        return 'L:' + leaf
    if part == 'hub_C':
        m = re.match(r'(pvw_\d)__u_ctl$', leaf)
        if m:
            if is_src:
                return 'ZERO' if port == 'cmd' else None
            if port in ('col_valid', 'col_fault'):
                return 'FLG'
            if port in ('in_t', 'in_valid', 'in_epoch'):
                return 'ZERO'               # arrival check and cmd take run off the same pa (ctl 'cmd word for the arrival at pa+1')
            return None
        if re.match(r'pvw_\d__u_RH_r0$', leaf):
            return 'RH'
        return None
    if is_src and re.search(r'astk_\w+_owner_\d+__u_owner\.response_data$', src_name):
        return 'EXT:' + leaf
    if not is_src and port in ('read_addr', 'read_v'):
        return 'EXT:' + leaf
    return None


mem = []
for x in land:
    if not (re.match(r'pv_[SN]_', x['src_part']) or re.match(r'pv_[SN]_', x['sink_part'])):
        continue
    for m in x['members']:
        src_leaf, src_port = m['source'].rsplit('.', 1)
        a = end(x['src_part'], src_leaf, src_port, True, m['source'])
        b = end(x['sink_part'], x['sink'], m['sink_port'], False, m['source'])
        if a is None or b is None:
            continue
        n = sum(hi - lo + 1 for lo, hi in m['sink_bits'])
        mem.append(dict(id=rid(x['sink'], m['sink_port'], m['sink_bits'], m['source'], m['asbuilt_stages']), sink=x['sink'],
                        sink_part=x['sink_part'], src_part=x['src_part'], sink_port=m['sink_port'], sink_bits=m['sink_bits'],
                        source=m['source'], asbuilt=m['asbuilt_stages'], bound=m['bound_stages'], lane=m['lane'], bits=n, a=a, b=b,
                        sw=sum(hi - lo + 1 for lo, hi in m['source_bits']), sb=json.dumps(m['source_bits'])))
# intra-partition edges of the bound pv partitions (binder ot_dp_dly = as-built internal depth, re-chosen here)
top = open(B + '/rtl/qwen_kvsys_bound_top.sv').read()
inner = []
for mod, part in re.findall(r'^\s*(kv3_pv\w*)\s+(pv_[SN]_\d+)\s*\(', top, re.M):
    t_ = open(f'{B}/rtl/{mod}.sv').read()
    loc = dict((l, g) for g, l in re.findall(r'// as-built (\S+)\n\s*\w+\s*(?:#\(.*?\))?\s*u_(\w+)\s*\(', t_))
    width = {n: int(w) + 1 for w, n in re.findall(r'wire\s*\[(\d+):0\]\s*(\w+);', t_)}
    for blk in re.finditer(r'// as-built (\S+)\n\s*\w+\s*(?:#\(.*?\))?\s*u_\w+\s*\((.*?)\n\s*\);', t_, re.S):
        g_sink, body = blk.group(1), blk.group(2)
        if re.match(r'vport_', g_sink):
            continue
        for port, expr in re.findall(r'\.(\w+)\((.*?)\)(?:,|$)', body, re.M | re.S):
            for ref, rng in re.findall(r'\b((?:w|d\d+)_\w+?)(\[\d+(?::\d+)?\])?(?=[\s,}\]]|$)', expr):
                m_ = re.match(r'(?:w|d(\d+))_(\w+)$', ref)
                D_ = int(m_.group(1) or 0); rest = m_.group(2)
                src_l = max((l for l in loc if rest.startswith(l + '_')), key=len, default=None)
                if src_l is None:
                    continue
                if rng:
                    ab = [int(v) for v in rng[1:-1].split(':')]
                    n_ = ab[0] - ab[-1] + 1
                else:
                    n_ = width.get(ref, 1)
                inner.append(dict(part=part, src=loc[src_l], sink=g_sink, port=port, asb=D_, bits=n_, ref=ref))
agg = collections.defaultdict(lambda: [0, None])
for e in inner:
    k = (e['part'], e['src'], e['sink'], e['port'], e['asb']); agg[k][0] += e['bits']
for (part, src, sink, port, asb), (n_, _) in agg.items():
    if src.endswith('__u_ctl') or sink.endswith('__u_ctl'):
        continue
    mem.append(dict(id=f'INNER:{part}:{sink}.{port}<-{src}@{asb}', sink=sink, sink_part=part, src_part=part, sink_port=port,
                    sink_bits=[], source=src, asbuilt=asb, bound=0, lane=None, bits=n_, a='L:' + src, b='L:' + sink, inner=True))
from kv_pv_route import reroute
route_info = reroute(mem, A_.option, A_.plan, A_.lat)
var = sorted({v for m in mem for v in (m['a'], m['b'])} - {'ZERO'})
ix = {v: i for i, v in enumerate(var)}
nv = len(var)
c = np.zeros(nv); A, bu = [], []; const = 0
for m in mem:
    row = np.zeros(nv)          # pad = t_b - t_a + asb - bound >= 0   ->  -(t_b - t_a) <= asb - bound
    if m['b'] != 'ZERO': row[ix[m['b']]] -= 1; c[ix[m['b']]] += m['bits']
    if m['a'] != 'ZERO': row[ix[m['a']]] += 1; c[ix[m['a']]] -= m['bits']
    A.append(row); bu.append(m['asbuilt'] - m['bound']); const += m['bits'] * (m['asbuilt'] - m['bound'])
bounds = [(-400, 400)] * nv
G = collections.defaultdict(list)
if A_.entry:
    for i, m in enumerate(mem):
        if not m.get('inner') and 'sb' in m:
            G[(m['source'], m['sb'], m['sink_part'])].append(i)
    G = {g: v for g, v in G.items() if sum(mem[i]['bits'] for i in v) > mem[v[0]]['sw']}
gix = {}
for g, lst in G.items():
    gix[g] = len(c); c = np.append(c, -(sum(mem[i]['bits'] for i in lst) - mem[lst[0]]['sw'])); bounds.append((0, 400))
    for i in lst:
        m = mem[i]; row = np.zeros(len(c)); row[gix[g]] = 1
        if m['b'] != 'ZERO': row[ix[m['b']]] -= 1
        if m['a'] != 'ZERO': row[ix[m['a']]] += 1
        A.append(row); bu.append(m['asbuilt'] - m['bound'])
A = [np.pad(r_, (0, len(c) - len(r_))) for r_ in A]
row = np.zeros(len(c)); row[ix['RH']] = -1; A.append(row); bu.append(TD_ASB)                       # TRUNK_D >= 0
row = np.zeros(len(c)); row[ix['RH']] = 1; row[ix['FLG']] = -1; A.append(row); bu.append(FD_ASB)   # FLAG_D >= 0
r = linprog(c, A_ub=np.array(A), b_ub=np.array(bu), bounds=bounds, method='highs', integrality=np.ones(len(c)))
assert r.status == 0, r.message
t = {v: int(round(r.x[ix[v]])) for v in var}; t['ZERO'] = 0
out, ov, tot = [], [], collections.Counter()
for m in mem:
    pad = t[m['b']] - t[m['a']] + m['asbuilt'] - m['bound']
    assert pad >= 0
    e = {k: m[k] for k in ('id', 'sink', 'sink_part', 'src_part', 'sink_port', 'sink_bits', 'source', 'asbuilt', 'bound')}
    e.update(pad=pad, landed=m['bound'] + pad, lane=m['lane'])
    out.append(e)
    kind = ('V' if 'out_v_' in m['source'] else 'cmd' if m['source'].endswith('u_ctl.cmd') else 'flag' if m['b'] == 'FLG'
            else 'hdr' if m['b'].startswith('HDR') else 'rs' if '_r0.b' in m['source'] else 'pe2' if 'response_data' in m['source']
            else 'hg_read' if m['b'].startswith('EXT') else 'other')
    if m.get('inner'):
        kind = 'inner_' + kind
        tot['inner_asbuilt_' + kind[6:]] += m['asbuilt'] * m['bits']
    tot[kind] += pad * m['bits']
    if m['id'] in r8 and r8[m['id']]['pad']:
        ov.append(dict(id=m['id'], r8_pad=r8[m['id']]['pad'], pv_pad=pad))
ent = collections.Counter()
gval = {g: int(round(r.x[gix[g]])) for g in G}
gof = {i: g for g, lst in G.items() for i in lst}
for i, m in enumerate(mem):
    if m.get('inner'):
        continue
    pad = t[m['b']] - t[m['a']] + m['asbuilt'] - m['bound']
    k_ = ('V' if 'out_v_' in m['source'] else 'cmd' if m['source'].endswith('u_ctl.cmd') else 'flag' if m['b'] == 'FLG'
          else 'rs' if '_r0.b' in m['source'] else 'pe2' if 'response_data' in m['source'] else 'other')
    e_ = gval.get(gof.get(i), 0)
    ent[k_] += m['bits'] * (pad - e_)
for g, e_ in gval.items():
    m = mem[G[g][0]]
    k_ = ('V' if 'out_v_' in m['source'] else 'cmd' if m['source'].endswith('u_ctl.cmd') else 'flag' if m['b'] == 'FLG'
          else 'rs' if '_r0.b' in m['source'] else 'pe2' if 'response_data' in m['source'] else 'other')
    ent[k_] += m['sw'] * e_
TRUNK_D = TD_ASB + t['RH']; FLAG_D = FD_ASB + t['FLG'] - t['RH']
shift = {v: k for v, k in t.items() if v.startswith('L:vport')}
cross = sum(v for k, v in tot.items() if not k.startswith('inner'))
for o in ov:
    o['r8_pad_flops'] = o['r8_pad'] * sum(hi - lo + 1 for lo, hi in r8[o['id']]['sink_bits'])
summary = dict(entry_costed=A_.entry, entry_pad_flops=int(sum(ent.values())), entry_pad_flops_by_kind=dict(ent), option=A_.option, route=route_info, members=len(out), padded_members=sum(1 for e in out if e['pad']), crossing_pad_flops=int(cross),
               inner_delay_flops_new=int(tot['inner_other']), inner_delay_flops_bound_asis=int(tot['inner_asbuilt_other']),
               pad_flops_by_kind=dict(tot), max_pad=max(e['pad'] for e in out), lp_objective=int(round(r.fun + const)),
               TRUNK_D=TRUNK_D, FLAG_D=FLAG_D, TRUNK_D_asb=TD_ASB, FLAG_D_asb=FD_ASB,
               P0_P1_age_shift=t['RH'], hdr_shift=t.get('HDR:pvw_0'), hdr_shift_N=t.get('HDR:pvw_1'),
               vport_launch_shift=shift, r8_overrides=len(ov), r8_override_pad_flops=sum(o['r8_pad_flops'] for o in ov))
json.dump(dict(schema='opentallas.die_plan.r8_landing.v1', die='qwen_kvsys', kind='pv_trunk_pads',
               note=__doc__.strip(), merge_rule='authoritative for listed ids; replaces r8 entry of the same id; others keep r8 pad',
               summary=summary, overrides=ov, members=out), open(OUT, 'w'), indent=1)
print(json.dumps(summary, indent=1))
