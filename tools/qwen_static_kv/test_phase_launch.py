import unittest
from phase_launch import launch

class PhaseLaw(unittest.TestCase):
    def profile(self,c,**kw):
        args=dict(core_origin_u=0,hbm_origin_u=0,ph0=0,safe_low_u=200,safe_high_u=600,meta_hold_core=8,first_active_hbm=0)
        args.update(kw)
        return launch(c,**args)
    def test_full_phase_census(self):
        accepted=0
        for c in range(768):
            toggle=(c+1)*625
            first=toggle//768+1
            gap=first*768-toggle
            if 200<=gap<=600:
                r=self.profile(c);accepted+=1
                self.assertEqual(r['first_hbm'],first)
                self.assertEqual(r['output_u'],(first+2)*768)
                self.assertEqual(r['metadata_consumer_hbm'],first+3)
            else:
                with self.assertRaises(ValueError):self.profile(c)
        self.assertEqual(accepted,401)
    def test_reset_phase_and_budget_rejections(self):
        for kw in (dict(ph0=1),dict(safe_low_u=0),dict(meta_hold_core=0),dict(first_active_hbm=1000)):
            with self.assertRaises(ValueError):self.profile(1,**kw)
    def test_explicit_actual_profile(self):
        with self.assertRaises(TypeError):launch(0)
        with self.assertRaises(ValueError):self.profile(1,core_origin_u=None)

if __name__=='__main__':unittest.main()
