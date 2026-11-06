import copy
import tempfile
import unittest
from pathlib import Path
from kit_dead_inputs import refresh

class WrapperAudit(unittest.TestCase):
    def test_literal_receipt_and_mutants(self):
        row=dict(port='bus_i',bound=2,plan=4)
        man=dict(narrow_buses=[row],dead_inputs=dict(bits=['bus_i[2]','bus_i[3]'],proof=dict(verdict='PASS',receipt=dict(wrapper='old',sha256='old',narrow_buses=[row]))))
        source='module m(input wire [4:0] bus_i); c u(.bus_i({bus_i[4],bus_i[1:0]})); endmodule'
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'wrapper.sv';p.write_text(source)
            good=copy.deepcopy(man);refresh(good,p)
            self.assertEqual(good['dead_inputs']['proof']['receipt']['wrapper'],str(p))
            self.assertEqual(man['dead_inputs']['proof']['receipt']['sha256'],'old')
            for bad in ['bus_i[2:0]','bus_i','bus_i[idx]']:
                p.write_text(source.replace('bus_i[1:0]',bad))
                with self.assertRaises(ValueError):refresh(copy.deepcopy(man),p)
            p.write_text(source.replace('.bus_i({bus_i[4],bus_i[1:0]})','.*'))
            with self.assertRaises(ValueError):refresh(copy.deepcopy(man),p)

if __name__=='__main__':unittest.main()
