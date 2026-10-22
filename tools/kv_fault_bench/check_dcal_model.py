#!/usr/bin/env python3
"""Fleet assertions for exact predecessor preservation and physical refusal."""
import copy,gzip,json
from pathlib import Path
from kv_fault_dcal_successor import successor
from kv_fault_topology import propose

d=Path.cwd();old=json.loads((d/'candidate.json').read_text());inv=json.loads((d/'inventory.json').read_text())
exact=json.loads(gzip.decompress((d/'exact_fault_native_pins.json.gz').read_bytes()));c=successor(inv,old,exact)
assert c['nodes'][:-2]==old['nodes'] and c['sources'][:-1]==old['sources'] and c['transports']==old['transports']
assert len(c['sources'])==357 and c['leaf_latencies']['dcal.fault']==2
assert c['max_leaf_latency_bound']==old['max_leaf_latency_bound']+2==182
assert all(c['leaf_latencies'][s['id']]>=2 for s in old['sources'])
assert c['fixed_status_contract']['terminal_path_edges'] is None and not c['qualified_release']
assert c['fixed_status_contract']['continuous_sticky_health'] and not c['fixed_status_contract']['mask_at_cutoff']
fresh=json.loads((d/'out/inventory357.json').read_text());dc=next(s for s in fresh['sources'] if s['id']=='dcal.fault')
assert len(fresh['sources'])==357 and dc['signal'] is None and dc['pin_xy'] is None
assert dc['clock']=='n_clk_core_c[0]' and dc['reset']=='n_rrs_n_rst_link_t0__m_0__s0[0]'
fresh['sources']=[dc]+[s for s in fresh['sources'] if s is not dc]
refusals=[]
try:propose(fresh)
except ValueError as e:
 assert str(e)=='no proven physical source position dcal.fault',str(e)
 refusals.append(str(e))
else:raise AssertionError('invented DCAL native exposure')
for kind in ('clock','profile','duplicate'):
 x=copy.deepcopy(exact);p=x['additional_dcal_fault'][0]
 if kind=='clock':p['clock_reset_pins']['ck']='n_clk_core_WS[0]'
 elif kind=='profile':p['parameters']['MUT']='1'
 else:x['additional_dcal_fault'].append(copy.deepcopy(p))
 try:successor(inv,old,x)
 except ValueError as e:refusals.append(str(e))
 else:raise AssertionError('accepted invalid '+kind)
result=dict(status='DCAL_MODEL_ASSERTIONS_PASS',qualified_release=False,sources=357,inventory_complete=False,max_leaf_latency=182,
            dcal_leaf_latency=2,predecessor_nodes_sources_transports_unchanged=True,physical_refusals=refusals,
            dcal_source=dc,obligations=c['fixed_status_contract'])
(d/'out/model_checks.json').write_text(json.dumps(result,indent=2)+'\n');print('DCAL_MODEL_ASSERTIONS_PASS')
