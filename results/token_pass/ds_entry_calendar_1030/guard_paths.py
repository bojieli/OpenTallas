import copy,json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030');S=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029');D0=Path('/srv/opentallas-scratch2/claude/codex-ds-native-1029')
sys.path[:0]=[str(R/'code'),str(S/'tools/s81_dv'),str(S/'tools/die_plan')]
from layer_prog.entry_page_protocol import encode
from native_boot import compile_boot
from native_phase import seqhost_phase_contract
read=lambda p:json.loads(p.read_text())
t=read(D0/'timing_current.json');t['seqhost_input_clock']=seqhost_phase_contract(read(D0/'seqhost_current.json'))
i=read(R/'inventory_vn.json');page=read(R/'load_pages_L14/job002.json');cfg=read(R/'shared_pages_L14/job002.json')['local_mux_config']
kw=dict(source_root=S,manifest='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json',inventory=i)
key='accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4';caught=[]
cases=[]
for label,val in [('missing',None),('boolean',True),('negative',-1),('outside',4)]:
 q=copy.deepcopy(t)
 if val is None:q.pop('seqhost_input_clock')
 else:q['seqhost_input_clock']={key:val}
 cases.append((label,q))
q=copy.deepcopy(t);q['input_clock']={key:1};cases.append(('conflicting_key_versions',q))
for label,q in cases:
 for mode in ('booked','unbooked','entry_page'):
  config=copy.deepcopy(cfg)
  if mode=='booked':config['launch']=dict(reset_release_pin_edge=64,ks_pin_edges=[67])
  try:
   if mode=='entry_page':encode(page,q,stage=0,start_phase=0,**kw)
   else:compile_boot(config,q,allow_unbooked_launch=mode=='unbooked',**kw)
  except ValueError:caught.append(label+':'+mode)
  else:raise AssertionError('phase guard escaped '+label+mode)
for label in('changed_dependency','changed_master','changed_actual_parameter','missing_dependencies'):
 q=copy.deepcopy(t);K=dict(kw)
 if label=='changed_dependency':q['source_sha256'][next(iter(q['source_sha256']))]='0'*64
 if label=='changed_master':q['masters']['dsdv_hostb_seqhost_mux']['source_path']='wrong.sv'
 if label=='missing_dependencies':q['source_sha256']={}
 if label=='changed_actual_parameter':
  I=copy.deepcopy(i);I['units']['u_seqhost']['params']['FMUT']='1';K['inventory']=I
 try:compile_boot(cfg,q,allow_unbooked_launch=True,**K)
 except ValueError:caught.append(label)
 else:raise AssertionError('source guard escaped '+label)
r=dict(status='PASS_NATIVE_BOOKED_UNBOOKED_PAGE_PHASE_AND_SOURCE_GUARDS',controls_caught=caught,phase_controls_per3_APIs=15,source_controls=4,selected_measured_reset_relative_phase=3,missing_default_phase=False)
(R/'guard_paths.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(caught))
