import unittest
from pq_descriptors import encode_descriptors
from pq_calendar import compile_events,viamap,validate_tag_lifetimes

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
 def test_real_macro_via_bit_order(self):
  rows=viamap([1,1<<71]);first=int(rows.splitlines()[0],16)
  self.assertEqual(first,1|(1<<(71*8+1)));self.assertEqual(len(rows.splitlines()),512)
 def test_fill_drain_and_tag_reuse(self):
  profile=dict(source_bound=True,live_pin_to_farthest_leaf_edges=12,root_pin_to_last_consumed_count_edges=8)
  life=[dict(tag=2,live_set=0,first_root=12,last_root=300,live_clear=308),dict(tag=2,live_set=320,first_root=332,last_root=400,live_clear=408)]
  self.assertTrue(validate_tag_lifetimes(life,profile));life[1]['live_set']=319
  with self.assertRaisesRegex(ValueError,'reused'):validate_tag_lifetimes(life,profile)
 def test_no_fabricated_internal_profile(self):
  with self.assertRaisesRegex(ValueError,'source profile'):validate_tag_lifetimes([],dict(source_bound=False))

if __name__=='__main__':unittest.main()
