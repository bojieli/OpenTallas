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
 def test_repeated_exact_row_is_idempotent(self):
  a=Q.publish(self.r/'one','same row','first');b=Q.publish(self.r/'one','same row','repeat')
  self.assertEqual(a,b)

if __name__=='__main__':unittest.main()
