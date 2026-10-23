#!/usr/bin/env python3
"""PLAN-KV: KV latency parameters from the plan (stage1 dest latencies; q = relay-equivalent stages = cycles - 1,
the as-built kv_die.py convention).  RESPONSE_LAT = 8 + krq + krs; RL = 4 + WP + O + DQ(0) + RT, RT = 8 + vq + rs;
F_DLY ~ pvfin.fo -> kvs_attn; PV_LEAD ~ kvs_attn.pvst -> farthest PV row.  Max over instances (one value for all)."""
import gzip, json, re, sys
d = json.load(gzip.open(sys.argv[1])); DL = d['dest_lat']; W = d['where']
def q(src, sp, dst):
    return [(k.split('|')[0], k.split('|')[2], c - 1, a) for k, (c, a) in DL.items()
            if re.match(src, k.split('|')[0]) and re.fullmatch(sp, k.split('|')[1]) and re.match(dst, k.split('|')[2])]
out = {}
rq = {W[s][0]: (c, a) for s, _, c, a in q('ectl_', 'rq', 'pcrow')}
rs = q('slg_', 'krsp', 'hgrp')
rt = [(8 + c + rq[dp][0], 8 + a + rq[dp][1]) for s, dp, c, a in rs if dp in rq]
out['RESPONSE_LAT'] = dict(plan=max(x[0] for x in rt), plan_min=min(x[0] for x in rt), natural_asbuilt_max=max(x[1] for x in rt), rtl6=80, brief_natural=18)
wp = {d_: c for s, d_, c, a in q('pvw_', 'req_t', 'pcrow')}
o = {}
for s, d_, c, a in q('vport_', 'vo', 'pvrow'):
    o[W[s][0]] = max(o.get(W[s][0], 0), c)
vq = {W[s][0]: c for s, d_, c, a in q('vport_', 'vq[01#]', 'pcrow')}
rsp = {d_: c for s, d_, c, a in q('slg_', 'rsp', 'pcrow')}
rl = [4 + wp.get(p, 0) + o[p] + 8 + vq.get(p, 0) + rsp.get(p, 0) for p in o]
out['RL'] = dict(plan=max(rl), plan_min=min(rl), O_max=max(o.values()), WP_max=max(wp.values()), rtl6=112, brief_natural=48)
fd = q('pvfin', 'fo', 'sys_core'); pl = q('kvs_attn', 'pvst', 'pvrow')
out['F_DLY'] = dict(plan=max(c for *_, c, a in fd), asbuilt_relays=max(a for *_, a in fd), rtl6=55, brief_natural=14)
out['PV_LEAD'] = dict(plan=max(c for *_, c, a in pl), asbuilt_relays=max(a for *_, a in pl), rtl6=38, brief_natural=14)
out['PV_FIRST_INPUT_AGE'] = dict(plan=out['RL']['plan'] + 1, note='RL + 1')
g = [dict(dst=x['dst'], port=x['dp'], plan_cycles=x['chain_cycles'], asbuilt=x['asbuilt_stages']) for x in d['gathers']]
out['gathers'] = g
print(json.dumps(out, indent=1))
