"""Measured KV START source-root fall entry must not suppress unrelated CPPR."""
import unittest
import die_sta_related as D

class FallCpprPartial(unittest.TestCase):
    def setUp(self):
        self.a=dict(port='A',cppr_node='h',late_ps=1000.,early_ps=900.)
        self.b=dict(port='B',cppr_node='h',late_ps=1050.,early_ps=950.,fall_late_ps=1090.,fall_early_ps=990.)
    def iv(self,rng):return D.ca_pair_interval(self.a,self.b,'A','B',rng,edge='fall')[:2]
    def test_partial_other_node_keeps_documented_fallback(self):
        self.assertEqual(self.iv({'h':100.,'__source__@fall':0.}),self.iv({'h':100.}))
        self.assertEqual(self.iv({'h':100.,'__source__@fall':0.}),(90.,90.))
    def test_measured_smaller_fall_range_caps_credit(self):
        self.assertEqual(self.iv({'h':100.,'h@fall':80.,'__source__@fall':0.}),(70.,110.))
    def test_real_zero_common_fall_range_stays_zero(self):
        self.assertEqual(self.iv({'h':100.,'h@fall':0.}),(-10.,190.))
    def test_calibrated_fall_range_uses_scaled_arrivals(self):
        meta=dict(cppr_node_range_ps={'h':100.,'__source__@fall':0.},node_late_ps={'h':1000.},node_early_ps={'h':900.},node_fall_late_ps={'h':1020.},node_fall_early_ps={'h':910.})
        m,_=D.apply_clock_cal(meta,{},'TT','inv','spice_edge')
        self.assertAlmostEqual(D.clock_cppr_ranges(m)['h@fall'],19.117,places=3)
        self.assertEqual(m['cppr_node_range_ps']['__source__@fall'],0.)
        self.assertNotIn('h@fall',meta['cppr_node_range_ps'])
    def test_none_calibration_still_publishes_actual_fall(self):
        meta=dict(cppr_node_range_ps={'h':100.},node_fall_late_ps={'h':1020.},node_fall_early_ps={'h':910.})
        m,_=D.apply_clock_cal(meta,{},'TT','inv','none')
        self.assertEqual(D.clock_cppr_ranges(m)['h@fall'],110.)
    def test_no_fall_default_identity(self):
        meta={'cppr_node_range_ps':{'h':100.}};taps={'A':self.a}
        m,t=D.apply_clock_cal(meta,taps,'TT','inv','none')
        self.assertIs(m,meta);self.assertIs(t,taps)

if __name__=='__main__':unittest.main()
