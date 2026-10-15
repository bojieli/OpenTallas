import unittest
from static_cdc_window import check_window


class Capacity(unittest.TestCase):
    def base(self, **kw):
        args=dict(words=2048,write_period_ps='833.334',read_period_ps='833.334',write_first_ps=0,read_first_ps='3333.336',depth=16)
        args.update(kw)
        return check_window(**args)

    def test_same_clock_and_bounded_epoch(self):
        self.assertTrue(self.base()['capacity_pass'])
        self.assertTrue(self.base(write_period_ps='833.084')['capacity_pass'])
        self.assertTrue(self.base(write_period_ps='833.584')['capacity_pass'])

    def test_unbounded_drift_cannot_inherit_finite_window_proof(self):
        self.assertFalse(self.base(words=60000,write_period_ps='833.084')['capacity_pass'])
        self.assertFalse(self.base(words=60000,write_period_ps='833.584')['capacity_pass'])

    def test_initial_read_phase_and_depth_must_be_reserved(self):
        self.assertFalse(self.base(read_first_ps=0)['capacity_pass'])
        self.assertFalse(self.base(depth=2)['capacity_pass'])


if __name__=='__main__':unittest.main()
