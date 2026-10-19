#!/usr/bin/env python3
"""Compare old proposed source objects against exact selected parent; no view adoption."""
import argparse,hashlib,json,re
from pathlib import Path
from pc_fault_plane_trace import SHA,bits
p=argparse.ArgumentParser();p.add_argument('die',type=Path);p.add_argument('old',type=Path);p.add_argument('--basis',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
b=a.die.read_bytes();assert hashlib.sha256(b).hexdigest()==SHA
ins={}
for line in b.decode().splitlines():
 m=re.fullmatch(r'\s*(\w+)(?:\s*#\((.*?)\))?\s+(\w+)\s*\((.*)\);\s*',line)
 if m:ins[m[3]]=dict(master=m[1],parameters=dict(re.findall(r'\.(\w+)\((.*?)\)',m[2] or '')),ports=dict(re.findall(r'\.(\w+)\((.*?)\)(?=,\s*\.|$)',m[4])))
old=json.loads(a.old.read_text());basis_raw=a.basis.read_bytes();assert hashlib.sha256(basis_raw).hexdigest()==old['input_sha256']['inventory.json'];basis=json.loads(basis_raw);records=[]
for s in old['sources']:
 i=ins.get(s['instance']);ps=i['ports'] if i else {};port=ps.get(s['port']);signal=s.get('signal');expected=[(signal[0],signal[1])] if signal else None
 r=dict(id=s['id'],instance=s['instance'],old_master=s.get('master'),selected_master=i['master'] if i else None,instance_identity=bool(i and (not s.get('master') or s['master']==i['master'])),old_clock=s['clock'],selected_clock=ps.get('ck'),clock_identity=s['clock']==ps.get('ck'),old_reset=s['reset'],selected_reset=ps.get('rs',ps.get('rst_n',ps.get('rsi'))),reset_identity=s['reset']==ps.get('rs',ps.get('rst_n',ps.get('rsi'))),old_signal=signal,selected_port_expression=port,pin_identity=(bits(port)==expected if port is not None and expected is not None else None),selected_parameters=i['parameters'] if i else None,old_parameters=s.get('parameters'),physical_view_transferred=False)
 records.append(r)
new=[]
for n,i in ins.items():
 if i['master'] in ('qkd_kvs_pc','qkd_kvs_pc_h'):
  new += [dict(id=n+'.u_pc.u_chain.fault',kind='chain_sticky_cause',selected_instance=n),dict(id=n+'.u_pc.u_pce.u_esm.fault',kind='ES_aggregate_sticky_cause',selected_instance=n)]
assert len(new)==256
oldids={s['id'] for s in records};newids={s['id'] for s in new};assert not(oldids&newids)
out=dict(status='SOURCE_MEMBERSHIP_RECONCILIATION_ONLY',old_die_sha256=basis['pinned_files'][basis['input_die']],old_basis='103049e43 successor model from canonical7006cbd0; original provenance retained',selected_die_sha256=SHA,old_source_objects=len(records),all_old_instance_master_ids_match=all(r['instance_identity'] for r in records),old_objects_not_exported_in_selected=[r['id'] for r in records if r['selected_port_expression'] is None],clock_mismatch_ids=[r['id'] for r in records if not r['clock_identity']],reset_mismatch_ids=[r['id'] for r in records if not r['reset_identity']],signal_mismatch_ids=[r['id'] for r in records if r['pin_identity'] is False],new_PC_cause_objects=new,new_and_old_ids_overlap=False,qualified_health_source_total=None,unique_physical_collector_source_count=None,joined_STATUS_tail_bound=None,reason='Two PC cause objects share each existing field301 and32group aggregates. Old source ports/native exposure remain open; producer causes are not equivalent to qualified health collector leaves.',old_records=records)
a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('old_records','new_PC_cause_objects')}))
