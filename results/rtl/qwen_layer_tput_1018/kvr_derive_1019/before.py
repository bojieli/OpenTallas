"""KVR-DERIVE evidence: the new kv_static_params checks on the base run kvs14r-131a7af2c-base (case_kv/die.v, its strict-bind
netlist die_bound.v and the netlist table exported from it)."""
import json, re, sys
W = '/home/ubuntu/wt/kvr-derive-1019/tools'
sys.path[:0] = [W + '/qwen_kv_die', W]
import kv_static_params as P, kv_static_die as KSD, die_relay_stages as DRS
S = '/home/ubuntu/scratch/dkvr/kvr-derive'
doc = DRS.load(f'{S}/base_netlist.json.gz')
gen = json.load(open(f'{S}/base/case_kv/relay_stages.json'))
die_v = f'{S}/base/case_kv/die.v'
txt = open(die_v).read()
masters = {i: m for m, i in re.findall(r'^\s*(\w+)\s+(?:#\s*\(.*?\)\s*)?(\w+)\s*\(', txt, re.M)}
bus_src = {}
for b in gen['buses']:
    if b.get('bid'):
        bus_src.setdefault(b['bid'], [b['src']['inst'], b['src']['port'], b['dst']['inst'], b['dst']['port']])
model = dict(bus_src=bus_src, masters=masters)
tp, probs = P.table_paths(doc)
sched = P.schedule(tp)
tile = KSD.tile_ages()
bound = P.bound_ages(f'{S}/bind_base/die_bound.v')
fails = [dict(id=p['id'], what=json.dumps(p)) for p in probs] + P.schedule_check(sched, tile, bound)
f_, slg = P.slg_identity(die_v); fails += f_
f_, slg_b = P.slg_identity(f'{S}/bind_base/die_bound.v'); fails += [dict(x, id=x['id'] + ' (die_bound.v)') for x in f_]
f_, rd = P.relay_domains(die_v, model); fails += f_
rec = dict(schema='opentallas.qwen_kv.kvr_derive_evidence.v1', run='ot-epyc4:/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-131a7af2c-base',
           table=dict(digest=doc['digest'], how='netlist_relay_stages.py on kv_port_bind_v2.sh die_bound.v (local)'),
           status='FAIL' if fails else 'PASS', paths=tp, schedule=sched, tile_ages=tile,
           bound=dict(ectl=sorted({json.dumps(v) for v in bound['ectl'].values()}), vport=sorted({json.dumps(v) for v in bound['vport'].values()}),
                      pv_ctl_age=bound['pv_ctl_age'], attn=bound['attn'], source=bound['source']),
           fails=fails, slg_identity=dict(die_v=slg, die_bound=slg_b), relay_domain=rd)
json.dump(rec, open(sys.argv[1], 'w'), indent=1, default=str)
print(rec['status'], [(f['id'], f['what'][:150]) for f in fails])
print('relays checked', rd['relays_checked'], 'mixed', len(rd['mixed_domain_buses']))
