import unittest
from parent_alias_binding import bind
class BindingTests(unittest.TestCase):
 def fixture(self):return dict(verdict='PASS',gold_source_sha256='abc',parent_public_ports={'input':[2,3]},parent_alias_bits={'cut':[2,7,'0'],'internal':[7]})
 def test_external_and_shared_private(self):
  p,e=bind(self.fixture(),'parent',{'input':[('net',0),('net',1)]})
  self.assertFalse(e);self.assertEqual(p['cut'],[('net',0),('parent::alias::abc',7),None]);self.assertEqual(p['internal'][0],p['cut'][1])
 def test_missing_public_is_not_internal(self):
  p,e=bind(self.fixture(),'parent',{});self.assertNotIn('cut',p);self.assertIn('cut',e);self.assertIn('internal',p)
 def test_conflicting_alias_refused(self):
  m=self.fixture();m['parent_public_ports']['other']=[2]
  p,e=bind(m,'parent',{'input':[('a',0),('a',1)],'other':[('b',0)]});self.assertNotIn('cut',p)
 def test_native_parent_domains_distinct(self):
  m=self.fixture();self.assertNotEqual(bind(m,'one',{})[0]['internal'],bind(m,'two',{})[0]['internal'])
if __name__=='__main__':unittest.main()
