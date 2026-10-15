import unittest
from pq_stage import compile_stage,host_word

class PQStageTest(unittest.TestCase):
 def setUp(self):
  self.desc=[dict(ph=514,np=0,xbase=0,xps=0,obase=0,ops=0,fmt=0,observed_end_edges=35,native_tag=2)]
  self.rows=[dict(engine=13,arg=0,issue=0,done=38,pin_to_pin=37,native_tag=2),dict(engine=15,arg=0,issue=40,done=0)]
  self.events=[dict(timestamp=1,action=dict(accept_tag=2)),dict(timestamp=42,action=dict(phase_end=1))]
 def compile(self,**kw):return compile_stage(self.rows,self.desc,self.events,7,0,**kw)
 def test_real_slot_and_boot_interfaces(self):
  x=self.compile(base=17);self.assertEqual(x['engine'],13)
  q=[r for r in x['host_packets']if r['data']&255==0x12]
  self.assertEqual(len(q),9)
  raw=lambda r:((r['data']>>96)&127)<<28|((r['data']>>32)&((1<<28)-1))
  self.assertEqual(raw(q[0]),(6<<25)|(1<<12)|17)
  self.assertEqual(raw(q[-1]),5<<25)
  self.assertEqual([raw(r)for r in q[1:-1]],x['descriptor_words'])
  self.assertFalse(x['dispatch_eligible']);self.assertFalse(x['qualified'])
 def test_legacy_engine_identity_not_reused(self):
  for wrong in [0,8,9,10,11,12]:
   self.rows[0]['engine']=wrong
   with self.assertRaisesRegex(ValueError,'engine13'):self.compile()
 def test_actual_registered_endpoint_edges(self):
  self.rows[0]['pin_to_pin']=36;self.rows[0]['done']=37
  with self.assertRaisesRegex(ValueError,'plus2'):self.compile()
 def test_tag_and_descriptor_bounds(self):
  self.rows[0]['arg']=1
  with self.assertRaisesRegex(ValueError,'descriptor'):self.compile()
  self.rows[0]['arg']=0;self.rows[0]['native_tag']=1
  with self.assertRaisesRegex(ValueError,'PINREG'):self.compile()
 def test_accept_follows_real_issuer_row(self):
  self.events[0]['timestamp']=0
  with self.assertRaisesRegex(ValueError,'align'):self.compile()
 def test_real_rom_capacity(self):
  with self.assertRaisesRegex(ValueError,'capacity'):self.compile(base=4095)
 def test_no_unpaced_host_boot(self):
  x=self.compile();ts=[r['host_stream_cycle']for r in x['host_packets']]
  self.assertTrue(all(b-a>=8 for a,b in zip(ts,ts[1:])))
  self.assertGreaterEqual(ts[-1]-ts[-2],208)
  self.assertGreaterEqual(x['earliest_job_host_stream_cycle']-ts[-1],208)
 def test_payload35_must_not_truncate(self):
  for w in [-1,1<<35]:
   with self.assertRaises(ValueError):host_word(0x12,w)

if __name__=='__main__':unittest.main()
