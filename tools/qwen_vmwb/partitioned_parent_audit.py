#!/usr/bin/env python3
"""Trace actual parent port bits into black-box clocks and real sequential cells."""
import argparse,json,re
from collections import Counter
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('netlist',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--expect',choices=['pass','fail'],default='pass');a=p.parse_args()
x=json.loads(a.netlist.read_text());mods=x['modules'];top='qfd_sp_vector_memory_par_partitioned';tm=mods[top]
labels={}
for n,v in tm['ports'].items():
 for i,b in enumerate(v['bits']):labels[b]=n if len(v['bits'])==1 else f'{n}[{i}]'
clock_rows=[];ff=Counter();owned=Counter();leaf_counts=Counter()
physical=['ot_qfd_vm_bctl_nx','ot_qfd_vm_delay1_t','ot_qfd_vm_delay2_t','ot_qfd_vm_rr2_nx','ot_qfd_vm_rr4_t','ot_qfd_vm_sctl_t','ot_qfd_vm_su1024_t','qfd_vm_qcommit','qvm_bank_banked_native','qvm_su_bank_native']
roles=['ck_ctrl','ck_in_lo','ck_in_hi','ck_mem_lo','ck_mem_hi','ck_cap_lo','ck_cap_hi','ck_out_lo','ck_out_hi']
def basename(n):return n.split('\\')[-1]
def mapbit(b,mp,path):return mp.get(b,f'{path}::bit{b}') if isinstance(b,int) else f'constant:{b}'
def walk(name,mp,path):
 m=mods[name]
 for n,c in m.get('cells',{}).items():
  t=c['type'];base=basename(t);cp=path+'.'+n;cc={k:[mapbit(b,mp,path) for b in v] for k,v in c['connections'].items()}
  if t in ['$dff','$adff','$sdff','$dffe','$adffe','$sdffe','$aldff','$dffsr']:
   count=len(c['connections']['Q']);ff[cc['CLK'][0]]+=count;owned[basename(name)]+=count
  if base in physical or base in ['ot_qfd_vm_su_return_plane','ot_qfd_vm_su_read_control']:
   leaf_counts[base]+=1
   pins=roles if base.startswith('qvm_') else (['ck'] if base.startswith('ot_qfd_vm_su_return') or base in ['ot_qfd_vm_su_read_control','qfd_vm_qcommit'] else ['clk'])
   for pin in pins:
    assert len(cc[pin])==1
    clock_rows.append({'instance':cp,'master':base,'pin':pin,'parent_clock_port':cc[pin][0]})
  if t in mods and base not in physical:
   cm={}
   for pn,pv in mods[t]['ports'].items():
    for b,label in zip(pv['bits'],cc.get(pn,[])):cm[b]=label
   walk(t,cm,cp)
walk(top,labels,top)
ports=Counter(r['parent_clock_port'] for r in clock_rows);all_used=set(ports)|set(ff);legacy={n:ports.get(n,0)+ff.get(n,0) for n in tm['ports'] if re.fullmatch(r'ck_r\d+_\d+',n)}
actual={'source_ports':sum(len(v['bits']) for v in tm['ports'].values()),'physical_clock_endpoints':len(clock_rows),'unique_physical_leaf_clock_inputs':len(ports),'all_active_clock_inputs_including_residual':len(all_used),'legacy_retained_clock_pins':len(legacy),'legacy_retained_used':sum(v>0 for v in legacy.values()),'legacy_unused_pins':[n for n,v in legacy.items() if not v],'source_ff_bits_total':sum(ff.values()),'source_ff_bits_by_parent_clock':dict(ff),'source_ff_bits_by_module':dict(owned),'leaf_counts':dict(leaf_counts),'clock_endpoints':clock_rows,'phase_status':'Every endpoint needs exact source/view insertion R and leaf/parent composition audit; no default phase or assumed equal R. No physical qualification.'}
checks={'port_bits':actual['source_ports']==15864,'row_bank_count':leaf_counts['qvm_bank_banked_native']==64,'operand_bank_count':leaf_counts['qvm_su_bank_native']==48,'return_planes':leaf_counts['ot_qfd_vm_su_return_plane']==96,'read_controls':leaf_counts['ot_qfd_vm_su_read_control']==3}
for prefix,want in [('native_ck[',1008),('return_ck[',96),('read_control_ck[',3)]:
 vals=[r['parent_clock_port'] for r in clock_rows if r['parent_clock_port'].startswith(prefix)];checks[prefix]=len(vals)==want and len(set(vals))==want
checks.update({'unique_leaf_clocks':actual['unique_physical_leaf_clock_inputs']==1482,'active_clocks':actual['all_active_clock_inputs_including_residual']==1483,'all_retained_legacy_pins_used':not actual['legacy_unused_pins'],'no_constant_clock':all(not r['parent_clock_port'].startswith('constant:') for r in clock_rows)})
actual['checks']=checks;actual['passed']=all(checks.values())
a.out.write_text(json.dumps(actual,indent=2)+'\n');print(json.dumps({k:v for k,v in actual.items() if k not in ['clock_endpoints','source_ff_bits_by_parent_clock','source_ff_bits_by_module']},indent=2))
assert actual['passed']==(a.expect=='pass'), 'Actual clock-port ledger does not match expected result'
