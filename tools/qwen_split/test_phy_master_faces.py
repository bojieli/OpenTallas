"""Native KV PHY has N/S faces; malformed physical buses must fail closed."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_split import native_static_io_bind as B

class PhyFaces(unittest.TestCase):
    def parse(self, pins):
        with TemporaryDirectory() as d:
            p=Path(d)/'phy';p.mkdir()
            text='SIZE 10 BY 20 ;\n'
            for n,rect in pins:
                text+=f'PIN {n}\n PORT\n LAYER M5 ;\n RECT {rect} ;\n END\nEND {n}\n'
            (p/'test.lef').write_text(text)
            with patch.object(B,'ROOT',Path(d)):
                return B.phy_master(lambda *a: SimpleNamespace(w=a[1],h=a[2],ports={},order=[]),'test','phy')
    def test_actual_north_south_orientation_preserved(self):
        q=self.parse([('ck','1 0 1.024 .192'),('d[0]','2 19.808 2.024 20'),('d[1]','3 19.808 3.024 20')])
        self.assertEqual(q.ports['ck'][2],'S')
        self.assertEqual(q.ports['d'][2],'N')
        self.assertEqual(q.ports['d'][4],[2.012,3.012])
    def test_missing_bus_bit_refused(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):
            self.parse([('d[1]','2 0 2.024 .192')])
    def test_multiface_bus_refused(self):
        with self.assertRaisesRegex(ValueError,'multi-face'):
            self.parse([('d[0]','2 0 2.024 .192'),('d[1]','3 19.808 3.024 20')])
    def test_interior_pin_refused(self):
        with self.assertRaisesRegex(ValueError,'not on a face'):
            self.parse([('ck','2 2 2.024 2.192')])
if __name__=='__main__':unittest.main()
