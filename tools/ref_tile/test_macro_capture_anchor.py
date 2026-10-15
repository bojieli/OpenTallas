"""Opt-in macro output anchoring is emitted explicitly and cannot inject Tcl."""
import copy
import json
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import ref_tile as RT

class MacroCaptureAnchor(unittest.TestCase):
    def setUp(self):
        self.spec=RT.load_spec(str(HERE/'examples/nhb_pbst_ref.json'))
        self.spec['io_flop_at_pins']={'cols':4,'allow_none':True}
    def env(self,s):
        return RT.gen_env(s,'kit',220.32,75.6,RT.layer_contract(s,None),[])
    def test_opt_in_reaches_production_route_environment(self):
        s=copy.deepcopy(self.spec);s['io_flop_at_pins']['macro_out_pins']=['rd_out','q']
        e=self.env(s)
        self.assertIn('--orfs-var OT_MPCAP_PINS=rd_out,q',e)
        self.assertIn('physical/qwen_die_masters/io_flop_at_pins.tcl',e)
    def test_default_and_empty_request_are_byte_identical(self):
        original=self.env(self.spec)
        self.assertNotIn('OT_MPCAP_PINS',original)
        empty=copy.deepcopy(self.spec);empty['io_flop_at_pins']['macro_out_pins']=[]
        self.assertEqual(self.env(empty),original)
    def test_invalid_names_and_types_are_refused(self):
        for bad in [['rd_out[0]'],['x;exec'],['x y'],['x,y'],['a.b'],[''],[7],'rd_out',{'rd_out':1}]:
            with self.subTest(bad=bad):
                s=copy.deepcopy(self.spec);s['io_flop_at_pins']['macro_out_pins']=bad
                with self.assertRaises(RT.SpecError):self.env(s)

if __name__=='__main__':unittest.main()
