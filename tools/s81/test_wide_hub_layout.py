"""Check the adopted capacity point and its executable side-by-side hub geometry."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CAP = 'results/physical/die_iter_1012/s81/canonical_widehub_1015/rm5_p1973.json'

class WideHubLayout(unittest.TestCase):
    def test_adopted_hub_preserves_geometry_and_facing_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'layout.json'
            subprocess.run([sys.executable, str(ROOT / 'tools/s81/wide_hub_layout.py'),
                            '--canonical', CAP, '--out', str(out)], check=True, capture_output=True)
            rec = json.loads(out.read_text())
        recorded = json.loads((ROOT / 'results/physical/die_iter_1012/s81/canonical_widehub_1015/hub_layout_rm5.json').read_text())
        self.assertEqual(rec, recorded)
        boxes = dict(rec['blocks'])
        boxes['mix4'] = rec['mix4_slot']
        for name, (x, y, w, h, *_) in boxes.items():
            self.assertGreater(w, 0, name)
            self.assertGreater(h, 0, name)
            self.assertGreaterEqual(min(x, y), 0, name)
            self.assertLessEqual(x + w, 33000, name)
            self.assertLessEqual(y + h, 26000, name)
        for na, a in boxes.items():
            for nb, b in boxes.items():
                if na >= nb:
                    continue
                overlap = min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0]) > 0.001 and min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1]) > 0.001
                self.assertFalse(overlap, (na,nb))
        su, vm, cap = (boxes[n] for n in ('sp_su_s','sp_vm','sp_capture'))
        self.assertGreaterEqual(vm[0]-(su[0]+su[2]),0)
        self.assertLessEqual(vm[0]-(su[0]+su[2]),0.432)
        self.assertAlmostEqual(vm[0]+vm[2], cap[0], places=3)
        self.assertGreaterEqual(boxes['mix4'][1],vm[1]+vm[3])
        self.assertGreaterEqual(rec['checks']['s14e_um'],399)
        for k in ('strip_w','hub_w','capfree','above_su','vm_s','su_under'):
            x0,y0,x1,y1=rec['wide'][k]
            self.assertLess(x0,x1,k)
            self.assertLess(y0,y1,k)
    def test_road_capacity_refuses_overwide_hub(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=subprocess.run([sys.executable,str(ROOT/'tools/s81/wide_hub_layout.py'),'--canonical',CAP,
                              '--vch','4000','--out',str(Path(tmp)/'bad.json')],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('S14E below',p.stderr)

if __name__ == '__main__':
    unittest.main()
