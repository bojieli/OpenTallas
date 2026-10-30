"""Intake actual saved VP proof; exercise dirty receipt/route/variant controls."""
import copy,importlib.util,json,sys
from pathlib import Path
from unittest.mock import patch
W=Path(sys.argv[1]);R=Path(sys.argv[2]);SRC=Path(sys.argv[3])
sys.path[:0]=[str(W/'tools/s81_dv'),str(SRC/'tools/die_plan')]
from layer_prog.vp_local_intake import attach,VP
T=json.load(open(R/'entry_transport.json'));I=json.load(open(R/'inventory_entry.json'));P=json.load(open(R/'vp_prior_result.json'))
M='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json'
r=attach(T,I,P,SRC,M);caught=[]
def reject(name,t,i,p):
 try:attach(t,i,p,SRC,M)
 except ValueError:caught.append(name)
 else:raise AssertionError('control missed '+name)
p=copy.deepcopy(P);p['checks']['negative_payload']['exit_code']=0;reject('missing_payload_control',T,I,p)
p=copy.deepcopy(P);p['source_sha256'][VP]='0'*64;reject('changed_production_source',T,I,p)
i=copy.deepcopy(I);i['source_asbuilt_sha256']='f'*64;reject('wrong_bound_inventory',T,i,P)
i=copy.deepcopy(I);i['units'][T['leaves'][0]['vp']]['params']={'ML':6};reject('different_VP_parameter',T,i,P)
t=copy.deepcopy(T);t['leaves'][0]['fields']['sw_d']['age_edges']+=1;reject('incoherent_store_word_age',t,I,P)
from layer_prog.slice_source import manifest_selection
selection=manifest_selection(SRC,M);ab=dict(selection[1]);ab['defines']=ab['defines']+['OT_MEM_FAULTS']
with patch('layer_prog.slice_source.manifest_selection',return_value=(selection[0],ab,selection[2],selection[3])):
 reject('activated_memory_fault_variant',T,I,P)
summary=dict(status='PASS_UNCHANGED_LOCAL_BODY_INTAKE',leaves=len(r['leaves']),
 source_asbuilt_sha256=r['source_asbuilt_sha256'],die_sha256=r['die_sha256'],
 prior_proof_asbuilt_sha256=P['source_asbuilt_sha256'],local_store_commit_edges=max(P['commit_edges']),
 local_HLOAD_last_VP_output_edges=P['output_edges']['HLOAD'],local_GAIN_last_VP_output_edges=P['output_edges']['GAIN'],
 from_XR_target5_output_to_VP_commit_range=[min(x['from_xr_target5_output_to_vp_store_commit_edges']for x in r['leaves']),max(x['from_xr_target5_output_to_vp_store_commit_edges']for x in r['leaves'])],
 from_XR_command_output_to_HLOAD_last_VP_output_range=[min(x['from_xr_command_output_to_vp_hload_last_output_edges']for x in r['leaves']),max(x['from_xr_command_output_to_vp_hload_last_output_edges']for x in r['leaves'])],
 from_XR_command_output_to_GAIN_last_VP_output_range=[min(x['from_xr_command_output_to_vp_gain_last_output_edges']for x in r['leaves']),max(x['from_xr_command_output_to_vp_gain_last_output_edges']for x in r['leaves'])],
 controls_caught=caught,source_hashes_checked=len(P['source_sha256']),selected_local_proof=r['vp_local_intake'],
 VN_capture_or_store_qualified=False,XR_target5_decode_qualified=False,readiness_qualified=False,physical_START_qualified=False,native_job_sealed=False,full_token=False)
Path(sys.argv[4]).write_text(json.dumps(summary,indent=2)+'\n')
print('VP_INTAKE',summary['leaves'],'leaves CONTROLS',len(caught),'PASS; VN/physical readiness held')
