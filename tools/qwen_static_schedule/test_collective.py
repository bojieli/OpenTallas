import unittest
from tools.qwen_static_schedule.collective import pw_image
from tools.qwen_static_schedule.calendar import ScheduleError

class Collective(unittest.TestCase):
 def event(self):
  return dict(rtl_instance='seq_su.u_seq.u_tp',rtl_module='ot_qwen_tp_seq_calendar',core_cmd_cycle=118,words=256,mode=0,tag=2)
 def test_actual_window_and_route(self):
  out=pw_image([self.event()],100,8,20,59)
  self.assertEqual([x['address'] for x in out],[944,945,946,947,960])
  self.assertEqual(int(out[0]['data_hex'],16),(256<<32)|8)
  self.assertEqual(int(out[-1]['data_hex'],16),(0x434c<<48)|(2<<32)|20)
 def test_tag_must_be_segment(self):
  event=self.event();event['tag']=0x12345678
  with self.assertRaises(ScheduleError):pw_image([event],100,8,20,59)
 def test_program_collision(self):
  with self.assertRaises(ScheduleError):pw_image([self.event()],100,8,20,60)
 def test_missing_real_source(self):
  event=self.event();del event['rtl_module']
  with self.assertRaises(ScheduleError):pw_image([event],100,8,20,59)
 def test_negative_route(self):
  with self.assertRaises(ScheduleError):pw_image([self.event()],100,-1,20,59)
 def test_duplicate_edges(self):
  with self.assertRaises(ScheduleError):pw_image([self.event(),self.event()],100,8,20,59)
if __name__=='__main__':unittest.main()
