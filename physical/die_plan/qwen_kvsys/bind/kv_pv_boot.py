#!/usr/bin/env python3
"""KV-P6-PV 10-23: per-vport boot ages (DQ, RT) + pair cfg_fia + W request-lane pads that realise the vport launch
shifts of the PV pad table (kv_pv_pads.py summary.vport_launch_shift).

    kv_pv_boot.py BIND_DIR PV_PADS.json RULES.json OUT_BOOT.json      (also appends the W pad members to PV_PADS.json)

Frame = the pair control's pa (cmd take and arrival check; both fixed in it).  The ctl issues request q at a fixed pa
and expects its first input FIRSTI later, so a cfg_fia change moves the request issue by -dFIA in this frame.
vport launch (V/header out) = request + W + DQ + RT (qkd_pv16_vport_b; as built W + DQ + RT = C_a on all 16 ports,
pair FIRST_INPUT_AGE = 5 + C_a).  Required: launch_k - launch_k,asb = shift_k, i.e.
    W_bound,k + Wpad_k + DQ_k + RT_k = X + shift_k,   X = C_a + dFIA  (one value, both pairs)
X is the smallest value that makes every DQ_k >= 0; DQ_k > 15 (RTL bound) -> the remainder as Wpad_k stages on the
port's W request lane (pr_t 14 b + pr_valid 1 b).  cfg_fia = 5 + X (as-built generator relation fia = 5 + C_a).
RT_k = the regenerated round trip from the RT rule (9 + vq + rs on the bound lanes).
"""
import json, re, sys
B, PADS, RULES, OUT = sys.argv[1:5]
T = json.load(open(PADS))
R = {r['param']: r for r in json.load(open(RULES))['rules']}
RT = R['RT (boot cfg_age)']['regen_kv35']
W = R['DQ (boot cfg_age)']['W_bound']
sh = {k[2:]: v for k, v in T['summary']['vport_launch_shift'].items()}
X = max(W[k] + RT[k] - sh[k] for k in sh)
boot, wpad = {}, {}
for k in sorted(sh):
    need = X + sh[k] - W[k] - RT[k]
    dq = min(need, 15); wp = need - dq
    assert dq >= 0 and 1 <= RT[k] <= 31
    boot[k] = dict(DQ=dq, RT=RT[k], cfg_age=(dq << 8) | RT[k], W_bound=W[k], W_pad=wp, launch_shift=sh[k])
    wpad[k] = wp
fia = 5 + X
assert 1 <= fia <= 127, fia
# W request-lane pads as table members (landing at the vport pr_t / pr_valid)
T['members'] = [m for m in T['members'] if m['sink_port'] not in ('pr_t', 'pr_valid')]   # idempotent re-run
land = json.load(open(B + '/bus_groups.json'))['landing']
added, fl = 0, 0
for x in land:
    if not x['sink'].startswith('vport_') or x['sink'] not in wpad:
        continue
    for m in x['members']:
        if m['sink_port'] in ('pr_t', 'pr_valid') and re.search(r'__u_ctl\.req_(t|valid)$', m['source']):
            p = wpad[x['sink']]
            n = sum(b - a + 1 for a, b in m['sink_bits'])
            T['members'].append(dict(id=f"{x['sink']}.{m['sink_port']}[{','.join(f'{a}:{b}' for a, b in m['sink_bits'])}]<-{m['source']}@{m['asbuilt_stages']}",
                                     sink=x['sink'], sink_part=x['sink_part'], src_part=x['src_part'], sink_port=m['sink_port'],
                                     sink_bits=m['sink_bits'], source=m['source'], asbuilt=m['asbuilt_stages'], bound=m['bound_stages'],
                                     pad=p, landed=m['bound_stages'] + p, lane=m['lane']))
            added += 1; fl += p * n
T['summary']['w_request_pad_members'] = added
T['summary']['w_request_pad_flops'] = fl
T['summary']['crossing_pad_flops_incl_w'] = T['summary']['crossing_pad_flops'] + fl
json.dump(T, open(PADS, 'w'), indent=1)
doc = dict(schema='opentallas.kv.pv_boot.v1', die='qwen_kvsys', plan='v3.6 (kv35 bind lanes) + kv_pv_pads_v36.json',
           generator='physical/die_plan/qwen_kvsys/bind/kv_pv_boot.py', note=__doc__.strip(),
           cfg_fia=dict(value=fia, applies='both pair controls hub_C u_pv[NS]_u_ctl (cfg_fia[7:0])', bound=127),
           X=X, vports=boot, ctl_params=dict(TRUNK_D=T['summary']['TRUNK_D'], FLAG_D=T['summary']['FLAG_D'],
                                             P0_P1_age_shift=T['summary']['P0_P1_age_shift']),
           assumptions=['as-built W+DQ+RT equal on all ports and fia_asb = 5 + C_a (kv_static_params generator rule)',
                        'RT = regenerated round trip (kv_param_rules RT rule) on the bound vq/rsp lanes'])
json.dump(doc, open(OUT, 'w'), indent=1)
print(json.dumps(dict(cfg_fia=fia, X=X, w_pad_members=added, w_pad_flops=fl,
                      vports={k: (v['DQ'], v['RT'], v['W_pad']) for k, v in boot.items()}), indent=0))
