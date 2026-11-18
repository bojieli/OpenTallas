import os,pathlib,subprocess,unittest
SOURCE=pathlib.Path(__file__).with_name('ot-heavy')
class OwnerThreadPolicy(unittest.TestCase):
 def policy(self,env=None,tail='ot_heavy_thread_cap_factor'):
  s=SOURCE.read_text();start=s.index('ot_heavy_thread_cap_factor() {');f=s[start:s.index('\n}\n',start)+3]
  e={k:v for k,v in os.environ.items() if k not in ['THREAD_CAP_FACTOR','LOAD_GATE_FACTOR','LOAD_CAP_FACTOR','LOAD_FRESH_S','OT_HEAVY_SHORT_POOL']};e.update(env or {})
  return subprocess.check_output(['bash','-c',f+'\n'+tail],env=e,text=True).strip()
 def owner(self,**kw):return dict(LOAD_GATE_FACTOR='0',LOAD_CAP_FACTOR='0',LOAD_FRESH_S='0',OT_HEAVY_SHORT_POOL='0',**kw)
 def test_unconfigured_host_retains_default(self):self.assertEqual(self.policy(),'1.0')
 def test_explicit_owner_cpu_off(self):self.assertEqual(self.policy(self.owner()),'0')
 def test_later_explicit_limit_wins(self):self.assertEqual(self.policy(self.owner(THREAD_CAP_FACTOR='1.5')),'1.5')
 def test_explicit_zero_wins(self):self.assertEqual(self.policy(self.owner(THREAD_CAP_FACTOR='0')),'0')
 def test_zero_without_owner_marker(self):self.assertEqual(self.policy({'THREAD_CAP_FACTOR':'0'}),'0')
 def test_preserve_later_load_policy(self):e=self.owner();e['LOAD_CAP_FACTOR']='3';self.assertEqual(self.policy(e),'1.0')
 def test_preserve_short_pool_policy(self):e=self.owner();e['OT_HEAVY_SHORT_POOL']='1';self.assertEqual(self.policy(e),'1.0')
 def test_partial_off_is_not_complete_intent(self):self.assertEqual(self.policy({'LOAD_CAP_FACTOR':'0'}),'1.0')
 def test_numeric_explicit_zero_disables(self):self.assertEqual(self.policy({'THREAD_CAP_FACTOR':'0.0'}),'0')
 def test_new_attempt_rechecks_host_policy(self):self.assertEqual(self.policy(self.owner(),"ot_heavy_thread_cap_factor; LOAD_CAP_FACTOR=3; ot_heavy_thread_cap_factor"),'0\n1.0')
if __name__=='__main__':unittest.main()
