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


if __name__=='__main__':unittest.main()
