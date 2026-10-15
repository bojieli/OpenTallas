import unittest
from pq_descriptors import encode_descriptors
from pq_calendar import compile_events,viamap,validate_tag_lifetimes,validate_boot_start

class NativePQImageTest(unittest.TestCase):
 def test_single_position_native_zero_np_roundtrip_all_pages(self):
  fields=dict(ph=511,np=0,xbase=524287,xps=5120,obase=4096,ops=320,fmt=2,observed_end_edges=12345,native_tag=0)
  w=encode_descriptors([fields]);self.assertEqual(len(w),7)
  native=sum((x&0xffffff)<<(24*p)for p,x in enumerate(w[1:6]))
  self.assertEqual(native>>90,12345);self.assertEqual(native&511,511);self.assertEqual((native>>9)&7,0)
 def test_canonical_phw10_preserves_high_phase_and_tag(self):
  fields=dict(ph=1023,np=7,xbase=524287,xps=5120,obase=4096,ops=320,fmt=2,observed_end_edges=12345,native_tag=3)
  words=encode_descriptors([fields],phase_width=10)
  value=sum((x&0xffffff)<<(24*p) for p,x in enumerate(words[1:6]))
  self.assertEqual(value&1023,1023);self.assertEqual((value>>10)&7,7)
  self.assertEqual((value>>91)&0xffffff,12345);self.assertEqual(value>>115,3)
  with self.assertRaises(ValueError):encode_descriptors([fields])
 def test_missing_duration_and_out_of_range_refuse(self):
  with self.assertRaises(ValueError):encode_descriptors([{}])
 def test_real_issuer_to_native_GO_calendar_edges(self):
  cmd=[dict(engine=0,issue=3,done=400,native_tag=2)]
  events=[dict(timestamp=4,action=dict(accept_tag=2)),dict(timestamp=20,action=dict(vm_req=1,vm_addr=8192)),dict(timestamp=500,action=dict(phase_end=1))]
  rows=compile_events(events,cmd);self.assertEqual(rows[0],(4<<72)|2)
  events[0]['timestamp']=3
  with self.assertRaisesRegex(ValueError,'align'):compile_events(events,cmd)
 def test_canonical_calendar_action75_bank_and_end(self):
  rows=compile_events([dict(timestamp=1,action=dict(stream_addr=16383,launch=1)),dict(timestamp=9,action=dict(phase_end=1))],[dict(engine=0,issue=0,done=20,native_tag=0)],action_bits=75)
  self.assertEqual((rows[0]>>40)&16383,16383);self.assertEqual((rows[0]>>65)&1,1)
  self.assertEqual(rows[1],(9<<75)|(1<<72))
 def test_real_macro_via_bit_order(self):
  rows=viamap([1,1<<71]);first=int(rows.splitlines()[0],16)
  self.assertEqual(first,1|(1<<(71*8+1)));self.assertEqual(len(rows.splitlines()),512)
 def test_fill_drain_and_tag_reuse(self):
  profile=dict(source_bound=True,live_pin_to_farthest_leaf_edges=12,root_pin_to_last_consumed_count_edges=9)
  life=[dict(tag=2,live_set=0,first_root=12,last_root=300,live_clear=309),dict(tag=2,live_set=321,first_root=333,last_root=400,live_clear=409)]
  self.assertTrue(validate_tag_lifetimes(life,profile));life[1]['live_set']=320
  with self.assertRaisesRegex(ValueError,'reused'):validate_tag_lifetimes(life,profile)
 def test_incap_count_chain_and_boot_release(self):
  # pre-INCAP drain 8 and a clear one edge early are both rejected
  with self.assertRaisesRegex(ValueError,'drain'):validate_tag_lifetimes([],dict(source_bound=True,live_pin_to_farthest_leaf_edges=12,root_pin_to_last_consumed_count_edges=8))
  p=dict(source_bound=True,live_pin_to_farthest_leaf_edges=12,root_pin_to_last_consumed_count_edges=9)
  with self.assertRaisesRegex(ValueError,'fill/drain'):validate_tag_lifetimes([dict(tag=0,live_set=0,first_root=12,last_root=300,live_clear=308)],p)
  self.assertTrue(validate_boot_start(100,103))
  with self.assertRaisesRegex(ValueError,'reset-relay'):validate_boot_start(100,102)
 def test_no_fabricated_internal_profile(self):
  with self.assertRaisesRegex(ValueError,'source profile'):validate_tag_lifetimes([],dict(source_bound=False))

if __name__=='__main__':unittest.main()
