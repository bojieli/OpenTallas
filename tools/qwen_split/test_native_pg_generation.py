import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import qwen_rom_fulldie_b3r2 as B


class NativePgGeneration(unittest.TestCase):
    def test_regrouped_r5_keeps_literal_rails_and_all_upconnects(self):
        v=SimpleNamespace(dn=lambda x,g:math.floor(x/g)*g,region_at=lambda m,x,y:'tile_field')
        i=SimpleNamespace(name='real_hard',master='real_hard',x=0.,y=0.,w=10.,h=10.,cx=5.,cy=5.)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'pdn.tcl'
            B.write_pdn_r5(v,dict(insts=[i]),p,63.64)
            s=p.read_text()
        self.assertEqual(s.count('-layer M1 -width .018 -followpins'),1)
        self.assertEqual(s.count('-layer M2 -width .018 -followpins'),1)
        for n in range(1,9):
            self.assertIn(f'add_pdn_connect -grid core -layers {{M{n} M{n+1}}}',s)
        self.assertIn('define_pdn_grid -macro',s)
        self.assertIn('-instances {^real_hard$}',s)


if __name__=='__main__':unittest.main()
