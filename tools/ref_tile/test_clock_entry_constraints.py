"""Missing data and ambiguous multiple clock pins must fail before job creation."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import clock_entry_constraints as C


class BoundData(unittest.TestCase):
    def test_reject_missing_corner_and_ambiguous_association(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); v = root/'view'; v.mkdir()
            lib = 'library(x){time_unit:"1ps";cell(view){pin(clk){clock:true;}}}'
            for c in C.CORNERS: (v/f'view_{c}.lib').write_text(lib)
            record = {'clock':'ck','lib_clock_pin':'clk'}
            for c in C.CORNERS: record[c]={'boundary':{'n':5,'min':90,'mean':100,'max':110}}
            spec = {'clock':'entries','clock_ports':['ck'],'children':[{'view':'view'}]}
            (v/'insertion.json').write_text(json.dumps(record)); C.generate(spec,root)
            broken=copy.deepcopy(record);del broken['ss']
            (v/'insertion.json').write_text(json.dumps(broken))
            with self.assertRaises((ValueError,KeyError)):C.generate(spec,root)
            broken=copy.deepcopy(record);del broken['lib_clock_pin']
            for c in C.CORNERS: (v/f'view_{c}.lib').write_text(lib.replace('pin(clk)', 'pin(clk2){clock:true;}pin(clk)'))
            (v/'insertion.json').write_text(json.dumps(broken))
            with self.assertRaisesRegex(ValueError,'ambiguous'):C.generate(spec,root)

    def test_related_domain_mapping_is_mandatory_and_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); v = root/'view'; v.mkdir()
            lib = 'library(x){time_unit:"1ps";cell(view){pin(ck){clock:true;}pin(ckv){clock:true;}}}'
            for c in C.CORNERS: (v/f'view_{c}.lib').write_text(lib)
            measured = {c: {'boundary': {'n': 7, 'min': 80, 'mean': 90, 'max': 100}} for c in C.CORNERS}
            (v/'insertion.json').write_text(json.dumps({'clock_measurements': {'ck': measured, 'ckv': measured}}))
            spec = {'clock': 'entries', 'clock_port': 'ck', 'clock_ports': ['ck', 'ckv'], 'children': [{'view': 'view'}]}
            with self.assertRaisesRegex(ValueError, 'multi-clock child requires explicit'):
                C.generate(spec, root)
            spec['clock_entry_domains'] = {
                'core': {'ratio': [1, 1], 'ports': ['ck'], 'inputs': ['rst'], 'outputs': []},
                'serial': {'ratio': [4, 3], 'ports': ['ckv'], 'inputs': ['rsv'], 'outputs': []}}
            generated = C.generate(spec, root)
            self.assertIn('io_budget_ps 222.222', generated)
            self.assertIn('io_budget_ps 166.667 inputs', generated)
            # composition-derived output budget: tightening only, emitted per domain, consumed by the output -max delay
            tight = copy.deepcopy(spec); tight['clock_entry_domains']['core']['io_budget'] = {'out': 0.6}
            g2 = C.generate(tight, root)
            self.assertIn('io_budget_ps 166.667 io_budget_out_ps 500.0', g2)
            self.assertIn('$budget_out-$dlmax+$sk', g2)
            for bad in ({'out': 0.1}, {'in': 0.9}, {'max': 0.3}):
                loose = copy.deepcopy(spec); loose['clock_entry_domains']['core']['io_budget'] = bad
                with self.assertRaises(ValueError):
                    C.generate(loose, root)
            self.assertIn('incomplete actual IO domain coverage', generated)
            clock = C.clocks(spec, 833.333)
            self.assertIn('ot_io_serial -period 1111.110666667', clock)
            broken = copy.deepcopy(spec); broken['clock_entry_domains']['serial']['ports'] = ['ck']
            with self.assertRaisesRegex(ValueError, 'duplicate domain clock port'):
                C.generate(broken, root)
            broken = copy.deepcopy(spec); broken['clock_entry_domains']['serial']['ratio'] = [2, 1]
            with self.assertRaisesRegex(ValueError, 'only related'):
                C.clocks(broken, 833.333)
            broken = copy.deepcopy(spec); broken['clock_entry_domains']['serial']['asynchronous'] = True
            with self.assertRaisesRegex(ValueError, 'no clock exceptions'):
                C.generate(broken, root)


if __name__=='__main__':unittest.main()
