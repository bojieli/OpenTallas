"""Compose actual80 destinations and refuse six unsafe source/payload controls."""
import copy,json,sys
from pathlib import Path
W,R,S=map(Path,sys.argv[1:4]);sys.path[:0]=[str(W/'tools/s81_dv'),str(S/'tools/die_plan')]
from layer_prog.target5_arrivals import compose
c=json.load(open(R/'control_current.json'));t=json.load(open(R/'vp_local_attached.json'));i=json.load(open(R/'inventory_entry.json'))
p=json.load(open(W/'results/token_pass/ds_entry_calendar_1030/xrt_target5.json'))
m='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json'
r=compose(c,t,i,p,S,m);caught=[]
def reject(name,C,T,I,P):
 try:compose(C,T,I,P,S,m)
 except ValueError:caught.append(name)
 else:raise AssertionError('missed '+name)
C=copy.deepcopy(c);C['die_sha256']='bad';reject('wrong_control_source',C,t,i,p)
P=copy.deepcopy(p);P['checks']['age_mutant']=0;reject('missing_caught_age_control',c,t,i,P)
P=copy.deepcopy(p);P['source_sha256'][next(iter(P['source_sha256']))]='bad';reject('dirty_measured_source',c,t,i,P)
I=copy.deepcopy(i);I['units'][t['leaves'][0]['xr']]['params']['FACE_LAND']='0';reject('wrong_wrapper_parameter',c,t,I,p)
# Exercise date lowering without relabelling old programme data: a single
# explicitly synthetic command, never emitted or presented as actual programme.
d=r['target5_store_destinations'][0]
C=copy.deepcopy(c);C['commands']=[dict(kind='TARGET5',status='PARTIAL',slice=d['slice'],leaf=d['leaf'],payload186=f'{(5<<16)|(1<<(21+d["leaf"])):047x}',seqhost_output_edge_from_age0_command=100)]
a=compose(C,t,i,p,S,m)['commands'][0]
assert a['leaf_store_commit_edge']==100+d['from_seqhost_output_to_vp_store_commit_edges']
C['commands'][0]['payload186']='0';reject('mislabeled_target5_payload',C,t,i,p)
C['commands'][0]['payload186']=f'{(5<<16)|(31<<21):047x}';reject('wrong_target5_leaf_mask',C,t,i,p)
q=dict(status='PASS_SOURCE_RELATIVE_TARGET5_COMPOSITION',destinations=80,source_asbuilt_sha256=r['source_asbuilt_sha256'],die_sha256=r['die_sha256'],from_actual_seqhost_output_to_vp_commit_range=[min(x['from_seqhost_output_to_vp_store_commit_edges']for x in r['target5_store_destinations']),max(x['from_seqhost_output_to_vp_store_commit_edges']for x in r['target5_store_destinations'])],controls_caught=caught,actual_programme_commands_lowered=0,synthetic_date_lowering_checked=True,native_job_sealed=False,full_token=False)
Path(sys.argv[4]).write_text(json.dumps(q,indent=2)+'\n')
print(q)
