import unittest
import bound_from_plan as B

class ClockExtra(unittest.TestCase):
    def test_unknown_clock_extra_keeps_side_leg_missing(self):
        side = {'plan_sha256':'p','provider_legs':{'host_to_provider':{'cycles':31,'clock_extra_required':True,'clock_extra_cycles':None}}}
        self.assertNotIn('host_to_provider',B.side_legs(side,'side','p'))
    def test_known_extra_is_priced(self):
        leg={'cycles':31,'clock_extra_required':True,'clock_extra_cycles':3}
        side={'plan_sha256':'p','provider_legs':{'host_to_provider':leg}}
        self.assertEqual(B.side_legs(side,'side','p')['host_to_provider']['cycles'],34)
        self.assertEqual(B.clock_qualified_cycles(dict(leg, source='plan')),34)
    def test_legacy_and_invalid_extra(self):
        self.assertEqual(B.clock_qualified_cycles({'cycles':4}),4)
        for value in (True,-1,1.5):
            with self.assertRaises(SystemExit): B.clock_qualified_cycles({'cycles':31,'clock_extra_required':True,'clock_extra_cycles':value})

if __name__=='__main__':unittest.main()
