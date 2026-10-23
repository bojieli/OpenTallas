#!/usr/bin/env python3
"""PLAN-KVv3 (= kv_params_v2 with hg/hgi heads and the split hub). PLAN-KVv2: KV latency parameters + lane shape metrics from the v2 stage1 (q = cycles - 1, as-built kv_die.py
convention).  RESPONSE_LAT = 8 + krq + krs; RL = 4 + WP + O + DQ(0) + RT, RT = 8 + vq + rs; F_DLY = pvfin.fo ->
kvs_attn; PV_LEAD = kvs_attn.pvst -> farthest PV row (through the hub u_ctl when pvst lands in the hub).
Detour = routed hop length (partition-centre chain) / Manhattan(source partition centre, sink partition centre)."""
import gzip, json, re, sys
d = json.load(gzip.open(sys.argv[1])); DL = d['dest_lat']; W = d['where']; P = d['P']


def q(src, sp, dst):
    return [(k.split('|')[0], k.split('|')[2], c - 1, a) for k, (c, a) in DL.items()
            if re.match(src, k.split('|')[0]) and re.fullmatch(sp, k.split('|')[1]) and re.match(dst, k.split('|')[2])]


out = {}
rq = {s.replace('ectl_', ''): c for s, dp, c, a in q('ectl_', 'rq', 'pc_')}
rt = [8 + c + rq[s.replace('slg_', '')] for s, dp, c, a in q('slg_', 'krsp', 'hg') if s.replace('slg_', '') in rq]
out['RESPONSE_LAT'] = dict(plan=max(rt), plan_min=min(rt), brief_natural=18, v1=12, v2=10, rtl6=80)
wp = {dp: c for s, dp, c, a in q('pvw_', 'req_t', 'pv_')}
o = {}
for s, dp, c, a in q('vport_', 'vo', 'pv_'):
    o[W[s][0]] = max(o.get(W[s][0], 0), c)
vq = {}
for s, dp, c, a in q('vport_', 'vq.*', 'pc_'):
    vq[W[s][0]] = max(vq.get(W[s][0], 0), c)
rsp = {}
for s, dp, c, a in q('slg_', 'rsp', 'pv_'):
    rsp[dp] = max(rsp.get(dp, 0), c)
wpm = max(wp.values()) if wp else 0
rl = [4 + wpm + o[p] + 8 + vq.get(p, 0) + rsp.get(p, 0) for p in o]
out['RL'] = dict(plan=max(rl), plan_min=min(rl), O_max=max(o.values()), WP_max=wpm, brief_natural=48, v1=61, v2=50, rtl6=112)
att = W['kvs_attn'][0]


def dlat(src_pat, dst_part):
    """plan station delay src -> dst partition (0 when co-located: a local flop, no lane)"""
    srcs = [b for b in W if re.match(src_pat, b)]
    if all(W[b][0] == dst_part for b in srcs):
        return 0
    v = [c for s_, d_, c, a_ in q(src_pat, '.*', dst_part)]
    return max(v) if v else None


# F_DLY compiler law (tools/qwen_kv_die/kv_static_params.py:520, ft_kv_stage_plan.py:12; F-DLY check by PLAN-KVv3):
#   F_DLY = 1 (qkd_pv_fin_s pin stage) + (D(ks_pvfst) - PV_LEAD) + D(ks_pvfin) + face_land_fin
#   with the alignment rule D(ks_pvfst) - PV_LEAD == D(ks_pvp_p)  -> F_DLY = 1 + D(pvp) + D(fin) + face_land_fin
d_fin = dlat(r'pvfin$', att)
d_pvp = max(dlat(r'pvw_0__u_RH_r0$', att) or 0, dlat(r'pvw_1__u_RH_r0$', att) or 0)
LAND_FIN = 1          # landed attention tile lands fin one edge later (kv_static_die.py FACE_LAND_TILES kvs_attn fin=1)
out['F_DLY'] = dict(plan=1 + d_pvp + d_fin + LAND_FIN, law='1 + D(pvp) + D(fin) + face_land_fin',
                    D_pvp=d_pvp, D_fin=d_fin, face_land_fin=LAND_FIN,
                    note='pvfin, kvs_attn and both pvw RH_r0 heads in %s; v2 value 1 was a fallback (no pvfin lane in '
                         'dest_lat) that dropped the fin face landing; 1 only with the unlanded kvs_attn_r17' % att,
                    brief_natural=14, v1=17, v2=1, rtl6=55)
pl = q('kvs_attn', 'pvst', '.*')
cm = [c for s, dp, c, a in q(r'pvw_\d__u_ctl', '.*', 'pv_')]
via_hub = W['pvw_0__u_ctl'][0].startswith('hub')
lead = (max((c for *_, c, a in pl), default=0) + 1 + max(cm)) if via_hub else max(c for *_, c, a in pl)
out['PV_LEAD'] = dict(plan=lead, brief_natural=14, v1=19, v2=16, rtl6=38)
out['gathers'] = [dict(dst=x['dst'], port=x['dp'], plan_cycles=x['chain_cycles'], asbuilt=x['asbuilt_stages'])
                  for x in d['gathers']]


def ctr(p):
    return (P[p]['x'] + P[p]['w'] / 2, P[p]['y'] + P[p]['h'] / 2)


bends, det = [], []
for l in d['lanes']:
    bends.append(l['bends'])
    hops = l['hops']
    if len(hops) < 2:
        continue
    pts = [ctr(hops[0][0])] + [ctr(h[1]) for h in hops]
    L = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))
    M = abs(pts[0][0] - pts[-1][0]) + abs(pts[0][1] - pts[-1][1])
    if M > 0:
        det.append(L / M)


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))]


out['lanes'] = dict(n=len(bends), bends_max=max(bends), bends_p90=pct(bends, 0.9),
                    bends_hist={k: bends.count(k) for k in sorted(set(bends))},
                    detour_p90=round(pct(det, 0.9), 3), detour_max=round(max(det), 3), multi_hop_lanes=len(det))
print(json.dumps(out, indent=1))
