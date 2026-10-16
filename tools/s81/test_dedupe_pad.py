#!/usr/bin/env python3
"""Generated netlist/binder checks for mixed logical widths of one physical master."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

class DedupePad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.out=Path(cls.tmp.name)
        subprocess.run([sys.executable,str(ROOT/'tools/s81/prove_dedupe_pad.py'),'--prepare','--out',str(cls.out)],check=True,capture_output=True)
        cls.source=(cls.out/'die.v').read_text()
        cls.pads=json.loads((cls.out/'die.v.pads.json').read_text())

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def bind(self,src=None,pads=None):
        (self.out/'die.v').write_text(self.source if src is None else src)
        (self.out/'die.v.pads.json').write_text(json.dumps(self.pads if pads is None else pads))
        p=subprocess.run([sys.executable,str(ROOT/'tools/die_port_bind.py'),str(self.out/'die.v'),'--top','dedupe_die','--rtl-root',str(self.out/'empty'),'--rtl-file',str(self.out/'masters.sv'),'--rtl-file',str(ROOT/'rtl/common/ot_fwd_link_stage.sv'),'--out',str(self.out/'report.json')],capture_output=True,text=True)
        return p,json.loads((self.out/'report.json').read_text())

    def test_all_thirty_actual_rebinds(self):
        p,d=self.bind();self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(d['verdict'],'PASS')
        self.assertEqual(len(self.pads['instances']),30)
        self.assertEqual(self.pads['instances']['u0']['ports']['di']['logical_width'],16)
        self.assertEqual(self.pads['instances']['u1']['ports']['di']['logical_width'],17)

    def test_mixed_width_logical_tie_is_not_padding(self):
        old=".di({3'b0, p1_di})";self.assertIn(old,self.source)
        src=self.source.replace(old,".di({3'b0, {1'b0, p1_di[15:0]}})")
        p,d=self.bind(src);self.assertNotEqual(p.returncode,0);self.assertIn('input_tied',d['failing'])

    def test_spare_tie_one_rejected(self):
        src=self.source.replace(".di({3'b0, p1_di})",".di({3'b1, p1_di})")
        p,d=self.bind(src);self.assertNotEqual(p.returncode,0);self.assertIn('input_tied',d['failing'])

    def test_missing_instance_permission_rejected(self):
        pads=json.loads(json.dumps(self.pads));del pads['instances']['u1']
        p,d=self.bind(pads=pads);self.assertNotEqual(p.returncode,0);self.assertIn('input_tied',d['failing'])

    def test_clock_family_change_rejected(self):
        mapping=json.loads((ROOT/'results/arch/tile_dedupe_1015/s81_pad_map_1016.json').read_text())
        mapping['map']['dsfd_hstnh_16']['to']='dsfd_stnh_566x1'
        p=self.out/'bad_map.json';p.write_text(json.dumps(mapping))
        result=subprocess.run([sys.executable,str(ROOT/'tools/s81/prove_dedupe_pad.py'),'--prepare','--map',str(p),'--out',str(self.out/'bad')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('clock/stage family differs',result.stderr)

    def test_logical_port_omission_rejected(self):
        mapping=json.loads((ROOT/'results/arch/tile_dedupe_1015/s81_pad_map_1016.json').read_text())
        del mapping['map']['dsfd_hstnh_16']['ports']['dq']
        p=self.out/'bad_map2.json';p.write_text(json.dumps(mapping))
        result=subprocess.run([sys.executable,str(ROOT/'tools/s81/prove_dedupe_pad.py'),'--prepare','--map',str(p),'--out',str(self.out/'bad2')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('AssertionError',result.stderr)

if __name__=='__main__':unittest.main()
