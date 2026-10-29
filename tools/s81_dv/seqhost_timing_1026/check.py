#!/usr/bin/env python3
"""Extract only observed local edge offsets; reject a shifted timing receipt."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--sources',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expect-shift',type=int,default=0);a=p.parse_args()
s=a.log.read_text()
if not re.search(r'^PASS$',s,re.M) or not re.search(r'^SEQ_TIMING jobs=2 north=4 south=2 gunit=2 kits=2 errors=0$',s,re.M):raise ValueError('actual local wrapper run did not pass')
ks={int(j):int(e) for j,e in re.findall(r'SEQ_KS job=(\d+) edge=(\d+) phase=0',s)}
accept=[int(d) for d in re.findall(r'SEQ_ACCEPT.*ks_delta=(\d+)',s)]
age0=[int(d)-[12,24,36,48][int(op)] for op,d in re.findall(r'SEQ_CMD.*op=(\d+).*ks_delta=(\d+)',s)]
def metric(xs,n):
 if not xs or len(set(xs))!=1:raise ValueError('nonconstant/missing '+n+':'+str(xs))
 return xs[0]
m={'fks_to_accept':metric(accept,'accept'),'fks_to_age0_command':metric(age0,'age0')}
for port in ['vo_n','vo_s']:
 m['command_to_'+port]=metric([int(d) for d in re.findall(r'SEQ_OUT.*port='+port+r'.*command_delta=(\d+)',s)],port)
m['command_to_cw']=metric([int(d) for d in re.findall(r'SEQ_CW.*command_delta=(\d+)',s)],'cw')
m['fks_to_kit_issue0']=metric([int(d)-72 for d in re.findall(r'SEQ_KIT.*ks_delta=(\d+)',s)],'kit')
# A receipt is accepted only when each claimed metric equals its measured event
# differences. The same source binary's +1-cycle metadata control must fail.
claim={k:v+a.expect_shift for k,v in m.items()}
if claim!=m:raise ValueError('TIMING_RECEIPT_MUTANT_CAUGHT shifted measured edges')
r=json.loads(a.sources.read_text());r.update(schema='opentallas.s81.local_unit_timing.v1',master='dsdv_hostb_seqhost_mux',verdict='PASS_LOCAL_COMPONENT',metrics=m,accepted_issuer_input_phase=0,input_clock=dict(reset_deassert_after_edge=30,first_unreset_edge=31,accepted_ks_edge_mod4=metric([v%4 for v in ks.values()],'clockphase'),accepted_ks_offset_from_first_unreset_mod4=metric([(v-31)%4 for v in ks.values()],'resetphase')),scope='Real atomic seqhost wrapper only; no bound inter-partition age, die-clock/reset release or token claim')
r['schema']='opentallas.s81.bound_control_local.v1';r['verdict']='PASS'
r['masters']={'dsdv_hostb_seqhost_mux':dict(source_path='physical/die_plan/s81/bind/source_modules/portfix178/dsdv_hostb_seqhost_mux.sv',params=r['params'],defines=r['defines'],edges=dict(calendar_command_to_vo_n=m['command_to_vo_n'],calendar_command_to_vo_s=m['command_to_vo_s'],calendar_command_to_cw=m['command_to_cw'],f_ks_pin_event_to_issuer_accept=m['fks_to_accept']+1,f_ks_to_issuer=m['fks_to_accept']+1,f_ks_sampling_to_issuer_accept=m['fks_to_accept'],f_ks_to_issuer_accept=m['fks_to_accept']+1,issuer_accept_to_age0_command=m['fks_to_age0_command']-m['fks_to_accept'],f_ks_pin_event_to_age0_command=m['fks_to_age0_command']+1,f_ks_to_age0_command=m['fks_to_age0_command']+1,f_ks_sampling_to_age0_command=m['fks_to_age0_command'],f_ks_pin_event_plus_kit_issue_to_t_kd=m['fks_to_kit_issue0']+1,f_ks_plus_kit_issue_to_t_kd=m['fks_to_kit_issue0']+1))}
r['input_clock'].update(accepted_ks_sampling_edge_mod4=metric([v%4 for v in ks.values()],'sampleclockphase'),accepted_ks_pin_event_mod4=metric([(v-1)%4 for v in ks.values()],'pinclockphase'),accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4=metric([(v-1-30)%4 for v in ks.values()],'resetphase'))
r['edge_convention']= 'Primary edges: input pin valid after posedge -> output pin valid after posedge. Input sampling occurs next edge. Explicit sampling metrics are separate.'
manifest=r.pop('source_manifest','physical/die_plan/s81/bind/asbuilt_b178_coll.json')
r['selection_manifest']=dict(path=manifest,sha256=r['source_sha256'].pop(manifest))
a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(m,sort_keys=True))
