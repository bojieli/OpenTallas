import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.qwen_static_schedule.segments import program_segments,pw_image,MissingPhysicalProfile,physical_profile,requires_constant_rom
from tools.qwen_static_schedule.calendar import ScheduleError
ROOT=Path(__file__).resolve().parents[2]
PLAN=ROOT/'results/arch/qwen_tp8_native_dispatch_1014/token_source_plan'
class Segments(unittest.TestCase):
 def layer(self):
  p=(PLAN/'layer_candidate_program.hex').read_bytes()
  d=[int(w,16)for w in(PLAN/'layer_candidate_segments.hex').read_text().split()]+[0]*5
  return p,d
 def test_actual_all_operations_covered(self):
  p,d=self.layer();segments=program_segments(p,d)
  self.assertEqual([(s['first_pc'],s['end_pc'],s['kind'],s['words'])for s in segments],[(0,13,1,256),(14,21,1,256),(22,24,0,0)])
 def test_actual_resource_use(self):
  p,d=self.layer();self.assertTrue(requires_constant_rom(p))
  self.assertFalse(requires_constant_rom((PLAN/'embedding_program.hex').read_bytes()))
 def test_missing_physical_ages_are_structured(self):
  p,d=self.layer()
  with self.assertRaises(MissingPhysicalProfile)as err:pw_image(p,d,1,{})
  self.assertIn('VM_response_edges',err.exception.missing_fields)
  self.assertIn('receipt_sha256',err.exception.missing_fields)
 def test_null_ages_are_structured_missing(self):
  p,d=self.layer()
  with self.assertRaises(MissingPhysicalProfile)as err:pw_image(p,d,1,dict(period_fs=None,physical_profile_status='MEASURED'))
  self.assertIn('period_fs',err.exception.missing_fields)
 def test_label_is_not_a_measurement(self):
  p,_=self.layer()
  with self.assertRaises(MissingPhysicalProfile):physical_profile(dict(physical_profile_status='MEASURED'),p)
 def test_omitted_real_operations_reject(self):
  p,d=self.layer();d[0]=0
  with self.assertRaises(ScheduleError):program_segments(p,d)
 def test_descriptor_must_cover_next_pc(self):
  p,d=self.layer();d[1]^=1<<32
  with self.assertRaises(ScheduleError):program_segments(p,d)
if __name__=='__main__':unittest.main()
