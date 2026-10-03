import tempfile
import unittest
from pathlib import Path
import qwen_rom_fulldie as F
import qwen_rom_fulldie_pg_r3 as R

class PowerPreparation(unittest.TestCase):
    def test_default_off(self):
        with tempfile.TemporaryDirectory() as p:
            with self.assertRaisesRegex(ValueError,'default off'):R.prepare(Path(p)/'out')
    def test_exact_bump_pitch_and_coverage(self):
        for cov in F.REGION_PG.values():
            if not cov:continue
            pitch=R.bump_pitch(cov);n=round(90/pitch)
            self.assertEqual(n%2,1);self.assertAlmostEqual(n*pitch,90)
            self.assertGreaterEqual(.48/pitch,cov)
            self.assertAlmostEqual(pitch*500,round(pitch*500))
            self.assertAlmostEqual((45%pitch),pitch/2)
    def test_off_grid_refused(self):
        with self.assertRaises(ValueError):R.bump_pitch(.04,90.0001)
    def test_all_fullsize_master_power_and_signal_inventory(self):
        model=F.build();ms=F.masters(model,1);pw=F.port_widths(model,1)
        for name,m in ms.items():
            with self.subTest(master=name):
                w={q:pw.get((name,q),0) for q in m.order}
                original,n=F.lef_text(m,1,w);actual,an=R.powered_lef(m,1,w)
                self.assertEqual(n,an)
                for net in ['VDD','VSS']:self.assertEqual(actual.count('  PIN '+net+'\n'),1)
                for net,rects in R.pg_rects(m,1,w).items():
                    for layer,(a,b,c,d) in rects:
                        self.assertTrue(0<=a<c<=m.w and 0<=b<d<=m.h)
                        for _,sl,(x,y,z,t) in F.pin_rects(m,1,w):
                            self.assertFalse(layer==sl and a<z and c>x and b<t and d>y)
    def test_refuse_existing_output(self):
        with tempfile.TemporaryDirectory() as p:
            q=Path(p);(q/'failure.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'existing output'):R.prepare(q,True)
    def test_prepare_price_and_phase_without_qualification(self):
        with tempfile.TemporaryDirectory() as p:
            d=R.prepare(Path(p)/'out',True)
            self.assertEqual(d['hard_reticle_mm2'],858)
            self.assertFalse(d['DSpark_installed'])
            self.assertFalse(any(d['qualification'].values()))
            for r in d['pdn_instances']:
                self.assertGreaterEqual(r['per_net_coverage'],r['requested_per_net_coverage'])
            self.assertEqual(d['original_plan']['link_stages']['per_token_cycles_delta'],432)

if __name__=='__main__':unittest.main()
