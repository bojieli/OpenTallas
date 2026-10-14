import copy
import datetime as dt
import json
from pathlib import Path
import random
import tempfile
import unittest
from monitor import Monitor, capacity, lock_valid, RPC

ROOT='root';CHILD='child';NOW=2_000_000_000
OVERLOAD={'message':'model is at capacity','codexErrorInfo':'serverOverloaded'}

def thread(tid=CHILD,status='idle',direct=False,parent=ROOT):
 return {'id':tid,'sessionId':ROOT,'parentThreadId':parent,'status':{'type':status},'canAcceptDirectInput':direct}

class FakeRPC:
 def __init__(self):
  self.threads={ROOT:thread(ROOT,'active',True,None),CHILD:thread()}
  self.turns={ROOT:[{'id':'root-active','status':'inProgress'}],CHILD:[{'id':'failed','status':'failed','error':OVERLOAD}]}
  self.goals={ROOT:None,CHILD:None};self.queues={ROOT:[],CHILD:[]};self.calls=[];self.before_call=None
 def call(self,method,params):
  self.calls.append((method,copy.deepcopy(params)))
  if self.before_call:self.before_call(method,params)
  tid=params.get('threadId')
  if method=='thread/read':return {'thread':copy.deepcopy(self.threads[tid])}
  if method=='thread/list':return {'data':[copy.deepcopy(t) for i,t in self.threads.items() if i!=ROOT],'nextCursor':None}
  if method=='thread/turns/list':return {'data':copy.deepcopy(self.turns[tid])}
  if method=='thread/goal/get':return {'goal':copy.deepcopy(self.goals[tid])}
  if method=='thread/queue/list':return {'data':copy.deepcopy(self.queues[tid]),'nextCursor':None}
  if method=='thread/resume':return {'thread':copy.deepcopy(self.threads[tid])}
  if method=='turn/steer':
   if params['expectedTurnId']!=self.turns[ROOT][0]['id']:raise RuntimeError('expected turn mismatch')
   return {'turnId':params['expectedTurnId']}
  raise AssertionError('Unexpected RPC '+method)

class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.directory=Path(self.temp.name)
  self.lock=self.directory/'coordinator.lock'
  self.lock.write_text(json.dumps({'owner':'codex','since':'generation','until':dt.datetime.fromtimestamp(NOW+10000,dt.timezone.utc).isoformat()}))
  self.rpc=FakeRPC();self.now=NOW
  self.monitor=Monitor(self.rpc,ROOT,self.directory,self.lock,'generation',clock=lambda:self.now,rng=random.Random(1),notify=True)
  self.monitor.refresh_scope()
 def tearDown(self):self.temp.cleanup()
 def failure(self,tid=CHILD,will_retry=False,error=None,status='failed'):
  error=error or OVERLOAD
  self.monitor.process_event({'method':'error','params':{'threadId':tid,'turnId':'failed','willRetry':will_retry,'error':error}})
  self.monitor.process_event({'method':'turn/completed','params':{'threadId':tid,'turn':{'id':'failed','status':status,'error':error}}})
  self.now+=40
 def writes(self):return [c for c in self.rpc.calls if c[0]=='turn/steer']
 def test_terminal_child_failure_notifies_existing_coordinator_once(self):
  self.failure();self.monitor.tick();self.monitor.tick()
  self.assertEqual(len(self.writes()),1)
  method,params=self.writes()[0]
  self.assertEqual(params['threadId'],ROOT);self.assertEqual(params['expectedTurnId'],'root-active')
  self.assertIn('Continue from preserved state; do not duplicate live jobs.',params['input'][0]['text'])
  self.assertIn('followup_task',params['input'][0]['text'])
  self.assertEqual(set(params),{'threadId','expectedTurnId','clientUserMessageId','input'})
  self.assertFalse(any(m in ('turn/start','thread/start','thread/fork') for m,p in self.rpc.calls))
 def test_persisted_dedup_across_restart(self):
  self.failure();self.monitor.tick()
  again=Monitor(self.rpc,ROOT,self.directory,self.lock,'generation',clock=lambda:self.now,rng=random.Random(1),notify=True)
  again.refresh_scope();again.tick()
  self.assertEqual(len(self.writes()),1)
 def test_noncapacity_and_internal_retries_never_act(self):
  for code in ('usageLimitExceeded','rateLimitExceeded','contextWindowExceeded','unauthorized','sandboxError'):
   self.assertFalse(capacity({'message':'model at capacity','codexErrorInfo':code}))
  self.assertFalse(capacity({'message':'HTTP503','codexErrorInfo':{'httpConnectionFailed':{'httpStatusCode':503}}}))
  self.failure(will_retry=True);self.monitor.tick();self.assertEqual(self.writes(),[])
  self.assertEqual(self.monitor.state['failures'],{})
 def test_failed_turn_without_will_retry_false_proof_not_recovered(self):
  self.monitor.process_event({'method':'turn/completed','params':{'threadId':CHILD,'turn':self.rpc.turns[CHILD][0]}})
  self.monitor.tick();self.assertEqual(self.writes(),[])
  self.failure(will_retry=None);self.monitor.tick();self.assertEqual(self.writes(),[])
 def test_completed_and_interrupted_turns_not_recovered(self):
  for status in ('completed','interrupted'):
   self.monitor.state['failures']={};self.failure(status=status);self.monitor.tick();self.assertEqual(self.writes(),[])
 def test_queued_input_pause_active_unloaded_and_newer_turn_guards(self):
  cases=[('paused',lambda:self.rpc.goals.update({CHILD:{'status':'paused'}})),
   ('blocked',lambda:self.rpc.goals.update({CHILD:{'status':'blocked'}})),
   ('queued_input',lambda:self.rpc.queues.update({CHILD:[{'id':'user-input'}]})),
   ('active',lambda:self.rpc.threads[CHILD].update(status={'type':'active','activeFlags':[]})),
   ('userinput',lambda:self.rpc.threads[CHILD].update(status={'type':'active','activeFlags':['waitingOnUserInput']})),
   ('unloaded',lambda:self.rpc.threads[CHILD].update(status={'type':'notLoaded'})),
   ('new_success',lambda:self.rpc.turns.update({CHILD:[{'id':'newer','status':'completed'}]}))]
  for name,change in cases:
   with self.subTest(name=name):
    self.rpc=FakeRPC();self.monitor.rpc=self.rpc;self.monitor.state['failures']={}
    self.monitor.refresh_scope();self.failure();change();self.monitor.tick();self.assertEqual(self.writes(),[])
 def test_lock_transfer_or_generation_change_stops_action(self):
  for value in ({'owner':'claude','since':'generation','until':'2099-01-01T00:00:00Z'},
                {'owner':'codex','since':'new-generation','until':'2099-01-01T00:00:00Z'}):
   self.lock.write_text(json.dumps(value));self.assertFalse(lock_valid(self.lock,'generation',self.now))
   self.failure();self.monitor.tick();self.assertEqual(self.writes(),[])
 def test_unrelated_thread_or_session_rejected(self):
  self.rpc.threads['other']=thread('other',parent='unrelated')
  self.rpc.threads['cross-session']=dict(thread('cross-session'),sessionId='other-session')
  self.monitor.refresh_scope()
  self.assertNotIn('other',self.monitor.scope);self.assertNotIn('cross-session',self.monitor.scope)
  self.failure('other');self.monitor.tick();self.assertEqual(self.writes(),[])
 def test_child_pending_approval_or_input_request_not_answered(self):
  self.failure();self.monitor.process_event({'id':51,'method':'item/tool/requestUserInput','params':{'threadId':CHILD}})
  self.monitor.tick();self.assertEqual(self.writes(),[])
  self.monitor.process_event({'method':'serverRequest/resolved','params':{'threadId':CHILD,'requestId':51}})
  self.now+=40;self.monitor.tick();self.assertEqual(len(self.writes()),1)
 def test_change_between_two_reads_rejected(self):
  self.failure();count=[0]
  def mutate(method,params):
   if method=='thread/read' and params.get('threadId')==CHILD:
    count[0]+=1
    if count[0]==2:self.rpc.turns[CHILD]=[{'id':'newer','status':'inProgress'}]
  self.rpc.before_call=mutate;self.monitor.tick();self.assertEqual(self.writes(),[])
 def test_coordinator_turn_race_has_no_unguarded_retry(self):
  self.failure()
  def mutate(method,params):
   if method=='turn/steer':self.rpc.turns[ROOT]=[{'id':'new-coordinator-turn','status':'inProgress'}]
  self.rpc.before_call=mutate;self.monitor.tick();self.monitor.tick()
  self.assertEqual(len(self.writes()),1)
  self.assertEqual(next(iter(self.monitor.state['failures'].values()))['action'],'notification_outcome_unknown')
 def test_retry_cap_and_backoff_with_jitter(self):
  for count in range(5):
   self.monitor.state['failures']={};self.monitor.state['attempts'][CHILD]=count
   self.failure();failure=next(iter(self.monitor.state['failures'].values()))
   elapsed=failure['due']-(self.now-40);expected=min(600,30*2**count)
   self.assertGreaterEqual(elapsed,expected*.8);self.assertLessEqual(elapsed,expected*1.2)
   self.now=max(self.now,failure['due']+1);self.monitor.tick()
  self.assertEqual(len(self.writes()),4)
  self.assertEqual(next(iter(self.monitor.state['failures'].values()))['action'],'retry_cap')
 def test_loaded_direct_capability_required_for_subscription(self):
  self.rpc.threads['unloaded']=thread('unloaded','notLoaded',True)
  self.monitor.refresh_scope();self.monitor.attach_loaded()
  resumes=[p['threadId'] for m,p in self.rpc.calls if m=='thread/resume']
  self.assertEqual(resumes,[ROOT])
 def test_notify_disabled_or_idle_coordinator_leaves_structured_file(self):
  self.monitor.notify=False;self.failure();self.monitor.tick()
  self.assertEqual(self.writes(),[]);self.assertEqual(len(list(self.directory.glob('notification-*.json'))),1)
  content=json.loads(next(self.directory.glob('notification-*.json')).read_text())
  self.assertTrue(content['requiresCoordinatorFollowup'])
 def test_coordinator_user_queue_and_pause_prevent_notification(self):
  for change in (lambda:self.rpc.queues.update({ROOT:[{'id':'pending-root-input'}]}),
                 lambda:self.rpc.goals.update({ROOT:{'status':'paused'}})):
   self.rpc=FakeRPC();self.monitor.rpc=self.rpc;self.monitor.state['failures']={}
   self.monitor.refresh_scope();self.failure();change();self.monitor.tick();self.assertEqual(self.writes(),[])
 def test_transport_whitelist_denies_direct_starts_and_model_changes(self):
  rpc=RPC.__new__(RPC)
  for method in ('turn/start','thread/start','thread/fork','thread/settings/update','account/read'):
   with self.assertRaisesRegex(ValueError,'unsupported monitor RPC'):rpc.call(method,{})

if __name__=='__main__':unittest.main()
