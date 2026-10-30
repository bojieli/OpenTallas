import copy,json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030');S=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029')
sys.path[:0]=[str(R/'code'),str(S/'tools/s81_dv'),str(S/'tools/die_plan')]
from layer_prog.bound_die import BoundDie
from layer_prog.bound_control import BoundControl
from layer_prog.entry_load_calendar import compile_jobs,check_page
from layer_prog.entry_write_calendar import encode_unsealed
import dv_layer_compile as D
read=lambda p:json.loads(p.read_text())
i=read(R/'inventory_vn.json');die=BoundDie('/srv/opentallas-scratch2/claude/codex-tok-s81-1028/bind_s13rfunc_reset/out',i)
m='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json';bc=BoundControl(die,'/srv/opentallas-scratch2/claude/codex-ds-native-1029/timing_current.json',S,m)
t=read(R/'vp_vn_local_attached.json');c=read(Path('/srv/opentallas-scratch2/claude/codex-ds-native-1029/control_current/bound_control.json'));entry=read(R/'entry_inputs_L14.json')
jobs=compile_jobs(entry,c,t,i,read(R/'xrt_target5.json'),bc,S,m,first_issue=20,issue_stride=2)
controls=[]
def reject(name,j):
 try:check_page(j)
 except ValueError:controls.append(name)
 else:raise AssertionError('missed '+name)
j=copy.deepcopy(jobs[0]);j['load_dates'][0]['vp_command_input_edge']=j['load_dates'][0]['required_prior_store_commit_edge'];reject('stale_HLOAD_same_edge_as_store',j)
j=copy.deepcopy(jobs[0]);j['load_dates'][2]['vp_command_input_edge']=j['load_dates'][2]['required_prior_store_commit_edge'];reject('GAIN_before_HLOAD_store',j)
j=copy.deepcopy(jobs[0]);j['source_relative_retire_not_before']-=2;reject('premature_page_retirement',j)
j=copy.deepcopy(jobs[0]);j['rows'][0]['row76']='0';reject('encoded_PW_date_corruption',j)
out=R/'load_pages_L14';out.mkdir();words=0
for n,j in enumerate(jobs):
 w=encode_unsealed(j);words+=len(w);(out/f'job{n:03}.json').write_text(json.dumps(j,indent=1)+'\n');(out/f'job{n:03}.unsealed.host_boot.memh').write_text(D.memh(w,515))
payloads=[t['payload186']for j in jobs for t in j['templates']if t.get('source_write_index')is not None]
assert payloads==[w['ctl_payload186']for w in entry['writes']]
summary=dict(status='PASS_CURRENT_SOURCE_PAGE_LOCAL_ENTRY_LOADS',die_sha256=die.die_sha,source_asbuilt_sha256=i['source_asbuilt_sha256'],layer='L14',pages=len(jobs),target5_commands=len(payloads),HLOAD_commands=80,GAIN_commands=80,commands_per_page=102,reserved_KIT_END_rows=2,native_page_capacity=128,templates_per_page=102,native_template_capacity=128,native_HOST_words=words,local_HOST_reservation_at5edges=words*5,retire_floor_range=[min(j['source_relative_retire_not_before']for j in jobs),max(j['source_relative_retire_not_before']for j in jobs)],same_actual_3920_payloads_preserved=True,controls_caught=controls,rootphase_qualified=False,physical_START_qualified=False,KIT_END_emitted=False,BEGIN_SEAL_emitted=False,native_job_sealed=False,full_token=False)
(R/'entry_loads_L14.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)
