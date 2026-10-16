import unittest
from tools.s81.engram_static_calendar import Lookup, compile_calendar

class Calendar(unittest.TestCase):
    def test_source_slots(self):
        e=compile_calendar([Lookup('real.lookup.0',20,0,128)])[0]
        self.assertEqual(e['request_cycles'],list(range(40,46)))
        self.assertEqual(e['output_cycles'],list(range(153,201)))
        self.assertEqual(e['external_service_qualification'],'UNBOUND')
    def test_collision_is_not_rescheduled(self):
        with self.assertRaisesRegex(ValueError,'overlap'):
            compile_calendar([Lookup('a',20,0,128),Lookup('b',100,1,128)])
    def test_literal_source_required(self):
        with self.assertRaises(ValueError):compile_calendar([Lookup('',20,0,128)])
    def test_bad_slot_or_age(self):
        for slot,age in [(8,128),(-1,128),(0,0),(0,65001),(0,True)]:
            with self.subTest(slot=slot,age=age),self.assertRaises(ValueError):
                compile_calendar([Lookup('a',20,slot,age)])
    def test_drain_then_next_launch(self):
        e=compile_calendar([Lookup('a',20,0,128),Lookup('b',213,1,128)])
        self.assertEqual(e[1]['launch'],213)

if __name__=='__main__':unittest.main()
