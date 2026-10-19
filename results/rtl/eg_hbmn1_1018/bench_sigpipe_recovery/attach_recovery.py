import sys,json,copy,pathlib,datetime
sys.path.insert(0,'/home/ubuntu/wt-claude-closure-daemon-1010/tools/closure_loop')
import closure_loop as c
name='hcoll_ring_ag_ctln_1018-r5c-4c84aa2ed'
assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
with c.job_lock(name):
 j=c.load_job(name)
 assert j['status']=='NEEDS_RTL' and j['reason']=='bench_ring_ag_n_mut_ttl expected FAIL but rc=141'
 backup=c.STATE/'cancel_recovery'/(name+'.before_sigpipe_recovery.json');backup.parent.mkdir(exist_ok=True);backup.write_text(json.dumps(j,indent=2)+'\n')
 stl=c.stage_list(j['spec'])
 j.setdefault('bench_recovery_history',[]).append(dict(at=c.now_iso(),cause='mut_run display pipe SIGPIPE before FAILED marker',prior=copy.deepcopy(j['benches']),prior_btrack=copy.deepcopy(j['btrack']),backup=str(backup),fix_commit='a3ebe9ca9',replay_unit='oth-ubuntu-3193373-1792391364',replay_rc=0,source_commit=j['commit_full']))
 for n in ['ttl','rrlead','hzrr']:
  k='bench_ring_ag_n_mut_'+n
  st=next(x for x in stl if x['key']==k)
  tag=k+'.recovery1019'
  v=dict(j,stage_tag=tag)
  assert c.bench_outcome(v,st,1), k
  j.setdefault('fail_witnesses',{}).update(v.get('fail_witnesses',{}))
  j['benches'][k]=dict(expect='fail',rc=1,ok=True,track='exact_source_binary_replay',tag=tag,source_commit=j['commit_full'],fix_commit='a3ebe9ca9',replay_unit='oth-ubuntu-3193373-1792391364')
  j['btrack'][k]=dict(state='done',tag=tag,host=j['host'],run=j['run'],n=2,recovered=c.now_iso())
 assert c.benches_done(j,stl)
 j.update(status='READY',stage_idx=next(i for i,s in enumerate(stl) if s['kind']=='verdict'),stage_key='verdict',reason=None,retries_used=0)
 for k in ['wait','finished_at','auto_react_judged']:j.pop(k,None)
 c.event(j,'SIGPIPE harness recovery: original rc141 and route retained, positive + 8 exact-source mutant binaries replayed through ot-run; ttl/rrlead/hzrr actual failing witnesses accepted with unchanged fail_regex; resume original verdict without reroute')
 c.save_job(j)
 print(j['status'],j['stage_idx'],backup)
