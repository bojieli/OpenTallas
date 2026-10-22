"""KVR-DERIVE evidence: the generator output of a local kv_die case on claude/kvr-derive-1019 (production flags of the base
run, old ECTL slot, ASTK_EXPAND 0 like the base): plan schedule + checks, bound sidecar, slg straps, relay clock audit."""
import json, sys, collections
W = '/home/ubuntu/wt/kvr-derive-1019/tools'
sys.path[:0] = [W + '/qwen_kv_die', W]
import kv_static_params as P
C = '/home/ubuntu/scratch/dkvr/kvr-derive/case2/case_kv'
ml = json.load(open(f'{C}/static_model.json'))
sc = json.load(open(f'{C}/die.v.params.json'))
ss = ml['static_schedule']
f_slg, slg = P.slg_identity(f'{C}/die.v')
f_rd, rd = P.relay_domains(f'{C}/die.v', ml)
rec = dict(schema='opentallas.qwen_kv.kvr_derive_evidence.v1', case=C, status='FAIL' if ss['fails'] or f_slg or f_rd else 'PASS',
           paths=ss['paths'], schedule=ss['schedule'], tile_ages=ml['tile_ages'], plan_fails=ss['fails'],
           sidecar=dict(ectl=sorted({json.dumps(v) for k, v in sc.items() if k.startswith('ectl_')}),
                        vport=sorted({json.dumps(v) for k, v in sc.items() if k.startswith('vport_')}), instances=len(sc)),
           bindings_pv_ctl_age=ml['bindings']['pv_ctl_age'], slg_fails=f_slg, relay_domain_fails=f_rd, relay_domain=rd)
json.dump(rec, open(sys.argv[1], 'w'), indent=1, default=str)
print(rec['status'], [f['id'] for f in ss['fails']], 'slg', f_slg, 'relay', [f['what'] for f in f_rd], rd['relays_checked'], len(rd['mixed_domain_buses']))
print(rec['sidecar'], rec['bindings_pv_ctl_age'])
v = ss['schedule']['vport']; print({k: (x['sides'], x['RT'], x['W']) for k, x in list(v.items())[:4]})
print(collections.Counter(x['RESPONSE_LAT'] for x in ss['schedule']['ectl'].values()), ss['schedule']['attn'], ss['schedule']['pv'])
