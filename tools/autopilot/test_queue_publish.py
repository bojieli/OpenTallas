import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import queue_publish as Q

class Publication(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name)
  def run(*a):return subprocess.run(a,check=True,capture_output=True,text=True)
  self.run=run
  run('git','init','--bare','-q',str(self.r/'remote'))
  run('git','clone','-q',str(self.r/'remote'),str(self.r/'one'))
  for n in ('one',):self.config(n)
  p=self.r/'one';(p/'autopilot').mkdir();(p/'autopilot/queue.tsv').write_text('# queue\noriginal\n');(p/'HANDOFF.md').write_text('base\n')
  self.g('one','add','.');self.g('one','commit','-qm','base');self.g('one','branch','-M','coord/state');self.g('one','push','-q','-u','origin','coord/state')
  run('git','clone','-q','-b','coord/state',str(self.r/'remote'),str(self.r/'two'));self.config('two')
 def config(self,n):
  self.g(n,'config','user.name','Test');self.g(n,'config','user.email','test@example.com')
 def g(self,n,*a):return self.run('git','-C',str(self.r/n),*a).stdout
 def tearDown(self):self.tmp.cleanup()
 def test_shared_dirty_checkout_and_index_are_untouched(self):
  p=self.r/'one';(p/'HANDOFF.md').write_text('dirty shared owner text\n');self.g('one','add','HANDOFF.md')
  (p/'autopilot/queue.tsv').write_text('# local draft only\n')
  before=(p/'.git/index').read_bytes()
  Q.publish(p,'new reviewed row','append row')
  self.assertEqual((p/'.git/index').read_bytes(),before)
  self.assertEqual((p/'autopilot/queue.tsv').read_text(),'# local draft only\n')
  self.assertEqual((p/'HANDOFF.md').read_text(),'dirty shared owner text\n')
  remote_sha=self.g('one','ls-remote','origin','refs/heads/coord/state').split()[0]
  self.assertIn('new reviewed row',self.g('one','show',remote_sha+':autopilot/queue.tsv'))
 def test_raced_publisher_retries_preserving_both_rows(self):
  actual=subprocess.run; fired=False
  def racing(cmd,*a,**kw):
   nonlocal fired
   if 'push' in cmd and not fired:
    fired=True;Q.publish(self.r/'two','competing reviewed row','competing append')
   return actual(cmd,*a,**kw)
  with patch.object(Q.subprocess,'run',side_effect=racing):
   Q.publish(self.r/'one','our reviewed row','our append')
  self.g('two','fetch','-q','origin','coord/state')
  text=self.g('two','show','origin/coord/state:autopilot/queue.tsv')
  self.assertIn('competing reviewed row',text);self.assertIn('our reviewed row',text)
 def test_geom_packet_is_append_only_and_idempotent(self):
  text='GEOM REQ exact source\nGEOM REPLY exact source PASS-COND'
  a=Q.publish(self.r/'one',text,'publish reviewed packet',path='lanes/GEOM-REVIEW.md')
  b=Q.publish(self.r/'one',text,'repeat packet',path='lanes/GEOM-REVIEW.md')
  self.assertEqual(a,b)
  self.assertIn(text,self.g('one','show',a+':lanes/GEOM-REVIEW.md'))
  self.assertIn('original',self.g('one','show',a+':autopilot/queue.tsv'))
 def test_distinct_geom_packets_keep_shared_continuation(self):
  first="GEOM REQ first source\n  shared exact physical condition"
  second="GEOM REPLY second source PASS-COND\n  shared exact physical condition"
  a=Q.publish(self.r/"one",first,"first packet",path="lanes/GEOM-REVIEW.md")
  b=Q.publish(self.r/"one",second,"second packet",path="lanes/GEOM-REVIEW.md")
  text=self.g("one","show",b+":lanes/GEOM-REVIEW.md")
  self.assertIn(first+"\n"+second,text)
  self.assertEqual(text.count("  shared exact physical condition"),2)
  self.assertNotEqual(a,b)
  self.assertEqual(b,Q.publish(self.r/"one",second,"repeat packet",path="lanes/GEOM-REVIEW.md"))
 def fault_runner(self,verb,faults):
  actual=subprocess.run; left=list(faults); calls=[]
  def run(cmd,*a,**kw):
   if verb in cmd:
    calls.append(cmd)
    if left:return subprocess.CompletedProcess(cmd,128,'',left.pop(0))
   return actual(cmd,*a,**kw)
  return run,calls
 DENIED='git@github.com: Permission denied (publickey).\nfatal: Could not read from remote repository.'
 def test_fetch_denied_then_ok(self):
  run,calls=self.fault_runner('fetch',[self.DENIED,self.DENIED])
  with patch.object(Q.subprocess,'run',side_effect=run),patch.object(Q,"time") as t:
   sha=Q.publish(self.r/'one','after denial','append')
  self.assertEqual(len(calls),3);self.assertEqual(t.sleep.call_count,2)
  self.assertIn('after denial',self.g('one','show',sha+':autopilot/queue.tsv'))
 def test_push_denied_then_ok(self):
  run,calls=self.fault_runner('push',[self.DENIED])
  with patch.object(Q.subprocess,'run',side_effect=run),patch.object(Q,"time") as t:
   sha=Q.publish(self.r/'one','after push denial','append')
  self.assertEqual((len(calls),t.sleep.call_count),(2,1))
  self.assertIn('after push denial',self.g('one','show',sha+':autopilot/queue.tsv'))
 def test_transport_retries_are_bounded(self):
  run,calls=self.fault_runner('fetch',[self.DENIED]*20)
  with patch.object(Q.subprocess,'run',side_effect=run),patch.object(Q,"time") as t:
   with self.assertRaisesRegex(RuntimeError,'transport error on fetch.*Permission denied'):
    Q.publish(self.r/'one','never','append')
  self.assertEqual(len(calls),len(Q.TRANSPORT_BACKOFF_S)+1);self.assertEqual(t.sleep.call_count,len(Q.TRANSPORT_BACKOFF_S))
 def test_hung_fetch_counts_as_transport(self):
  actual=subprocess.run;n=[0]
  def run(cmd,*a,**kw):
   if 'fetch' in cmd and n[0]==0:
    n[0]+=1;raise subprocess.TimeoutExpired(cmd,kw.get('timeout'))
   return actual(cmd,*a,**kw)
  with patch.object(Q.subprocess,'run',side_effect=run),patch.object(Q,"time"):
   sha=Q.publish(self.r/'one','after hang','append')
  self.assertIn('after hang',self.g('one','show',sha+':autopilot/queue.tsv'))
 def test_push_refused_is_not_called_a_race(self):
  run,calls=self.fault_runner('push',['remote: error: GH006: protected branch\n ! [remote rejected] x -> coord/state (pre-receive hook declined)']*9)
  with patch.object(Q.subprocess,'run',side_effect=run),patch.object(Q,"time") as t:
   with self.assertRaisesRegex(RuntimeError,'not a race.*GH006'):
    Q.publish(self.r/'one','refused','append')
  self.assertEqual((len(calls),t.sleep.call_count),(1,0))
 def test_repeated_races_keep_race_message(self):
  run,calls=self.fault_runner('push',['! [rejected] x -> coord/state (fetch first)']*9)
  with patch.object(Q.subprocess,'run',side_effect=run),patch.object(Q,"time") as t:
   with self.assertRaisesRegex(RuntimeError,'raced repeatedly'):
    Q.publish(self.r/'one','raced','append',attempts=3)
  self.assertEqual((len(calls),t.sleep.call_count),(3,0))
 def test_repeated_exact_row_is_idempotent(self):
  a=Q.publish(self.r/'one','same row','first');b=Q.publish(self.r/'one','same row','repeat')
  self.assertEqual(a,b)

if __name__=='__main__':unittest.main()
