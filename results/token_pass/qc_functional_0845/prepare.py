#!/usr/bin/env python3
"""Prepare the explicitly approved current QC functional source candidate."""
import copy,gzip,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3]
D=Path(__file__).resolve().parent
I=D/'inputs'
for archive in I.glob('*.json.gz'):
 target=archive.with_suffix('')
 if not target.exists():target.write_bytes(gzip.decompress(archive.read_bytes()))
def read(name):
 p=I/name
 return json.loads(p.read_text() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes()))
def write(name,obj):
 (D/name).write_text(json.dumps(obj,indent=1)+'\n')
raw=read('plan.json');ca=read('native_ca.json');side=read('sidecar_previous.json');ab=read('asbuilt_previous.json')
ports={p['id']:p for p in raw['ports']}
assert len(side['ports'])==len(ca['ports'])==2525
changed=[]
for row in side['ports']:
 pid=row['port'];p=ports[pid];c=ca['ports'][pid]
 assert (p['src']['part'],p['dst']['part'],p['width'])==(row['src'],row['dst'],row['width'])
 old=raw['clock']['landing_network']['count_aligned_cycles'][pid];new=c['sched_lat']
 assert old==row['added_cycles']
 if old!=new:changed.append(dict(port=pid,lane=row['lane'],before=old,after=new,delta=new-old))
 row['added_cycles']=new
 raw['clock']['landing_network']['count_aligned_cycles'][pid]=new
sys.path.insert(0,str(R/'tools/die_plan'))
import count_align_bind as CAB
side=CAB.annotate_table(side,ca,root_settle_cycles=64,strap_form=True)
side['note']='Current native perimeter1 CA table + exact data endpoints, approved coherent source candidate; no physical adoption'
raw['note']+=' | CODEX functional candidate: native perimeter1 CA data counts and actual native START provider; explicit coherent HEAD/ROPE profile'
rootrel='results/token_pass/qc_functional_0845'
ab['base']='../../..'
ab['map_file']='../../../physical/die_plan/qwen_compute/bind/asbuilt_map_p6.json'
ab['clock_landing_table']=rootrel+'/sidecar.json'
ab['land_r8']=rootrel+'/inputs/r8_previous.json'
ab['land_r8_extra']=[rootrel+'/inputs/cb16_previous.json','results/token_pass/qc_head_loop_1029/candidate_inner.json']
ab['qwen_head_prepare_profile']=json.loads((R/'results/token_pass/qc_head_profile_1029/candidate_profile.json').read_text())['qwen_head_prepare_profile']
ab['note']+=' | CODEX current native CA/START + explicit approved coherent HEAD_CONTEXT/ROPE/L_CONTEXTS=1 and INNER witness4to8; regenerate R8 before source gate'
write('plan.json',raw);write('sidecar.json',side);write('asbuilt.json',ab)
write('ca_cycle_delta.json',dict(status='SOURCE_CANDIDATE_NOT_ADOPTED',changed_ports=len(changed),
 aggregate_port_cycles=sum(r['delta'] for r in changed),rows=changed,
 model_price='Requires fresh whole bind + regenerated R8; aggregate port cost is not token latency'))
print('PREPARED',len(raw['partitions']),len(raw['partition_types']),len(changed),sum(r['delta'] for r in changed))
