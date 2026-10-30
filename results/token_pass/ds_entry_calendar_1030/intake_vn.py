import copy,json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030');S=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029')
sys.path[:0]=[str(R/'code'),str(S/'tools/die_plan')]
from layer_prog.vn_local_intake import attach
read=lambda p:json.loads(p.read_text())
t=read(R/'vp_local_attached.json');v=read(R/'vp_vn.json');i=read(R/'inventory_vn.json');p=read(Path('/srv/opentallas-scratch2/claude/codex-vn-commit-1030/vn_local.json'))
m='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json'
a=attach(t,v,i,p,S,m);caught=[]
def reject(name,T,V,I,P):
 try:attach(T,V,I,P,S,m)
 except ValueError:caught.append(name)
 else:raise AssertionError('control escaped '+name)
P=copy.deepcopy(p);P['checks']['payload_mutant']=0;reject('missing_actual_payload_control',t,v,i,P)
I=copy.deepcopy(i);I['units'][v['leaves'][0]['halves']['b']['vn']]['params']['HW_STAGE']='1';reject('different_VN_write_stage',t,v,I,p)
V=copy.deepcopy(v);V['leaves'][0]['halves']['a']['fields']['hw_d']['age_edges']+=1;reject('incoherent_H_payload_age',t,V,i,p)
P=copy.deepcopy(p);P['source_sha256']['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv']='bad';reject('changed_VN_source',t,v,i,P)
summary=dict(status=a['vn_local_intake']['verdict'],die_sha256=a['die_sha256'],source_asbuilt_sha256=a['source_asbuilt_sha256'],local_HLOAD_pin_to_last_VN_store_commit_edges=sorted(set(r['local_hload_readiness_edges']for r in a['leaves'])),local_GAIN_pin_to_last_VN_store_commit_edges=sorted(set(r['local_gain_readiness_edges']for r in a['leaves'])),from_XR_command_output_to_H_store_range=[min(r['from_xr_command_output_to_vn_h_store_last_commit_edges']for r in a['leaves']),max(r['from_xr_command_output_to_vn_h_store_last_commit_edges']for r in a['leaves'])],from_XR_command_output_to_GAIN_store_range=[min(r['from_xr_command_output_to_vn_gain_store_last_commit_edges']for r in a['leaves']),max(r['from_xr_command_output_to_vn_gain_store_last_commit_edges']for r in a['leaves'])],actual_instances=160,controls_caught=caught,native_job_sealed=False,full_token=False,physical_START_qualified=False)
(R/'vn_intake.json').write_text(json.dumps(summary,indent=2)+'\n');(R/'vp_vn_local_attached.json').write_text(json.dumps(a,indent=1)+'\n');print(summary)
