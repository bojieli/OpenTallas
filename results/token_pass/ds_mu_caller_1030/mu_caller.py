import copy,hashlib,json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030');S=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029');D0=Path('/srv/opentallas-scratch2/claude/codex-ds-native-1029');F=Path('/srv/opentallas-scratch2/claude/codex-entry-reload-1030')
sys.path[:0]=[str(R/'code'),str(R/'code/layer_prog'),str(S/'tools/s81_dv'),str(S/'tools/die_plan')]
from layer_prog.native_mu_calendar import bind_contract,check_job
from layer_prog.pipeline_boot import native_job
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=R/'mu_caller';out.mkdir();j=read(R/'shared_pages_L14/job002.json');rows=[dict(engine=r['eng'],**{k:v for k,v in r.items()if k!='eng'})for r in j['rows']]
p=out/'native_entry';(p/'prog').mkdir(parents=True)
(p/'prog/host_boot.memh').write_text((F/'page0.host.memh').read_text())
(p/'prog/calendar.json').write_text(json.dumps(dict(job=[dict(rows=rows,sealed_programme_held=True)]))+'\n')
(p/'lowering.json').write_text(json.dumps(dict(ops=[],die_gaps=['entry_only_not_full_math_stage']))+'\n')
manifest=dict(die_v_sha256=j['die_sha256'],files={n:sha(p/n)for n in['prog/host_boot.memh','prog/calendar.json','lowering.json']})
(p/'manifest.json').write_text(json.dumps(manifest)+'\n')
words=(F/'page0.host.memh').read_text().split();(out/'mux.host.memh').write_text('\n'.join(words[:35])+'\n')
binding=dict(schema='opentallas.s81.native_mu_return_calendar.v1',local_timing_receipt=str(D0/'timing_current.json'),seqhost_phase_receipt=str(D0/'seqhost_current.json'),initialization_host_file='mux.host.memh',bound_inventory=str(R/'inventory_vn.json'),source_root=str(S),asbuilt_manifest='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json',clock_reset_identity='LOCAL_SOURCE_FIXTURE_ONLY_NOT_GLOBAL_BOOKING',initialization_last_seq_capture=315,first_KS_seq_capture=2424)
mu=bind_contract(binding,out);actual=native_job(p,allow_mu_initialization=True)
receiver=dict(selected_parameters=mu['selected_params'],clock_reset_identity=binding['clock_reset_identity'])
assert actual['KIT_issues']==[482]and len(actual['native_mu_initialization_words'])==35
assert not check_job(actual,receiver,mu,2424)
assert not check_job(actual,receiver,mu,2424+2596)
caught=[]
def reject(name,job,rec,m,ks):
 result=check_job(job,rec,m,ks)
 if not result:raise AssertionError('missed '+name)
 caught.append(dict(name=name,causes=[r['cause']for r in result]))
q=copy.deepcopy(actual);next(r for r in q['rows']if r['engine']==14)['issue']=789;reject('actual_A_KIT789_under_entry_RL489',q,receiver,mu,2424)
q=copy.deepcopy(actual);q['rows']=[r for r in q['rows']if r['engine']!=14];reject('missing_KIT_return',q,receiver,mu,2424)
q=copy.deepcopy(actual);q['native_die_sha256']='86dd02b2269e8ff96789db513ad4f93b501891c1e029436a9fe8cafa7d2f1718';reject('stale_math_source_identity',q,receiver,mu,2424)
reject('off_static_slot',actual,receiver,mu,2425)
r=copy.deepcopy(receiver);r['selected_parameters']['HOSTB_ENABLE']=1;reject('unqualified_receiver_variant',actual,r,mu,2424)
r=copy.deepcopy(receiver);r['clock_reset_identity']='OTHER';reject('different_clock_reset_epoch',actual,r,mu,2424)
try:native_job(p)
except ValueError:caught.append(dict(name='old_native_parser_default_does_not_silently_accept_MU',causes=['unsupported_MU_CSR']))
else:raise AssertionError('default parser must remain strict')
result=dict(status='PASS_ACTUAL_NATIVE_BOOT_PREFIX_AND_SELECTED_MU_CALLER_GUARD',actual_native_rows=actual['nops'],actual_MU_prefix_words=len(actual['native_mu_initialization_words']),actual_KIT=actual['KIT_issues'],local_source_contract=mu,controls=caught,scope='actual sealed/reloaded component fixture data and source-relative local KS sampling edges only; not global ROOT/HOST bookings',global_adoption=False,full_token=False)
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(caught))
