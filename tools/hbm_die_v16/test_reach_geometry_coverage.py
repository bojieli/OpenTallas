#!/usr/bin/env python3
"""Causal geometry omissions must not turn an over-reach bus into PASS."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from d4g_reach_check import classify

class GeometryCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'views').mkdir()
        self.lef = self.root / 'views' / 'tile.lef'
        self.lef.write_text("""MACRO tile
 SIZE 10 BY 10 ;
 PIN o
  DIRECTION OUTPUT ;
  USE SIGNAL ;
  PORT
   RECT 1 1 2 2 ;
  END
 END o
 PIN i
  DIRECTION INPUT ;
  USE SIGNAL ;
  PORT
   RECT 1 1 2 2 ;
  END
 END i
END tile
""")
        self.placement = {n:dict(master='tile', x=x, y=0, w=10, h=10, orient='R0')
                          for n,x in [('a',0),('b',500)]}
        self.contract = self.root / 'contract.json'
        self.contract.write_text(json.dumps(dict(instances={n:dict(master='tile',ports={}) for n in self.placement}, edges=[])))
        self.emit()
    def emit(self, parameter=False):
        (self.root/'manifest.json').write_text(json.dumps(dict(placement=self.placement)))
        head = 'tile #(.P(1))' if parameter else 'tile'
        (self.root/'die.v').write_text('module top();\n  '+head+' a (\n    .o(w)\n  );\n  tile b (\n    .i(w)\n  );\nendmodule\n')
    def run_case(self, strict=True):
        return classify(self.root, self.contract, strict_coverage=strict)[0]
    def test_complete_far_bus_fails(self):
        r=self.run_case()
        self.assertEqual(r['geometry_coverage']['verdict'],'PASS')
        self.assertEqual(r['over_buses_by_class'],dict(sync=1))
        self.assertEqual(r['verdict'],'FAIL')
    def test_parameters_cannot_hide_far_bus(self):
        self.emit(parameter=True)
        self.assertEqual(self.run_case()['over_buses_by_class'],dict(sync=1))
        self.assertEqual(self.run_case()['geometry_coverage']['parsed_instances'],2)
    def test_complete_near_bus_passes(self):
        self.placement['b']['x']=100; self.emit()
        self.assertEqual(self.run_case()['verdict'],'PASS')
    def test_missing_lef_false_pass_is_refused(self):
        self.lef.unlink()
        self.assertEqual(self.run_case(False)['verdict'],'PASS')
        r=self.run_case()
        self.assertEqual(r['verdict'],'FAIL')
        self.assertEqual(r['geometry_coverage']['by_reason'],dict(missing_lef=2))
    def test_missing_pin_false_pass_is_refused(self):
        self.lef.write_text(self.lef.read_text().replace('PIN i','PIN absent').replace('END i','END absent'))
        self.assertEqual(self.run_case(False)['verdict'],'PASS')
        self.assertEqual(self.run_case()['geometry_coverage']['by_reason'],dict(missing_pin_geometry=1))
        self.assertEqual(self.run_case()['verdict'],'FAIL')
    def test_missing_placement_is_refused(self):
        del self.placement['b']; self.emit()
        self.assertEqual(self.run_case()['geometry_coverage']['by_reason'],dict(missing_placement=1))
        self.assertEqual(self.run_case()['verdict'],'FAIL')
    def test_unparsed_instance_is_refused(self):
        p=self.root/'die.v';p.write_text(p.read_text().replace('tile b (','tile b( '))
        self.assertEqual(self.run_case()['geometry_coverage']['by_reason'],dict(unparsed_instance=1))
        self.assertEqual(self.run_case()['verdict'],'FAIL')
    def test_missing_contract_port_is_refused(self):
        c=json.loads(self.contract.read_text())
        c['edges']=[dict(source=['a','o',0,1],sink=['b','i',0,1],bits=1)]
        self.contract.write_text(json.dumps(c))
        p=self.root/'die.v';p.write_text(p.read_text().replace('.i(w)', '.i()'))
        self.assertEqual(self.run_case()['geometry_coverage']['by_reason'],dict(missing_contract_port_connection=1))
        self.assertEqual(self.run_case()['verdict'],'FAIL')
    def test_unexpected_connected_instance_preserves_net_and_refuses(self):
        # The extra real sink must participate even in legacy mode. A partial
        # contract must never erase its physical endpoint from the reach scan.
        self.placement['b']['x']=100
        self.placement['extra']=dict(master='tile',x=900,y=0,w=10,h=10,orient='R0')
        self.emit()
        p=self.root/'die.v'
        p.write_text(p.read_text().replace('endmodule', '  tile extra (\n    .i(w)\n  );\nendmodule'))
        self.assertEqual(self.run_case(False)['over_buses_by_class'],dict(sync=1))
        r=self.run_case()
        self.assertEqual(r['geometry_coverage']['by_reason'],dict(unexpected_instance=1))
        self.assertEqual(r['over_buses_by_class'],dict(sync=1))
        self.assertEqual(r['verdict'],'FAIL')
    def test_legacy_parameter_parser_is_unchanged(self):
        self.emit(parameter=True)
        self.assertEqual(self.run_case(False)['buses_checked'],0)
        self.assertEqual(self.run_case()['buses_checked'],1)
    def cli(self,*args):
        out=self.root/'reach.json'
        r=subprocess.run([sys.executable,str(Path(__file__).with_name('d4g_reach_check.py')),
                          str(self.root),str(self.contract),'--out',str(out),*args],capture_output=True,text=True)
        return r,json.loads(out.read_text())
    def test_cli_default_refuses_missing_geometry(self):
        self.lef.unlink()
        r,out=self.cli()
        self.assertEqual(r.returncode,1)
        self.assertIn('REACH_CHECK FAIL',r.stdout)
        self.assertFalse(out['geometry_qualified'])
    def test_cli_diagnostic_optout_cannot_claim_ordinary_pass(self):
        self.lef.unlink()
        r,out=self.cli('--diagnostic-incomplete-coverage')
        self.assertEqual(r.returncode,0)
        self.assertIn('DIAGNOSTIC_REACH_CHECK PASS',r.stdout)
        self.assertFalse(out['geometry_qualified'])
        self.assertFalse(out['native_release_qualified'])
        self.assertIn('DIAGNOSTIC',out['qualification'])
    def test_cli_default_complete_near_bus_is_geometry_only(self):
        self.placement['b']['x']=100;self.emit()
        r,out=self.cli()
        self.assertEqual(r.returncode,0)
        self.assertTrue(out['geometry_qualified'])
        self.assertFalse(out['native_release_qualified'])
    def test_unknown_direction_is_refused(self):
        self.lef.write_text(self.lef.read_text().replace('DIRECTION INPUT','DIRECTION INOUT'))
        self.assertEqual(self.run_case()['geometry_coverage']['by_reason'],dict(unknown_signal_direction=1))
        self.assertEqual(self.run_case()['verdict'],'FAIL')

if __name__=='__main__': unittest.main(verbosity=2)
