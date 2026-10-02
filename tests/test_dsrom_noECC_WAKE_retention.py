import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dsrom_noECC_wake_retained_map import wake_cells

class Retention(unittest.TestCase):
    def net(self):
        n={'cells':{},'netnames':{}}
        for i in range(8):
            n['netnames'][f'g_wake.g_leaf[{i}].wake']={'bits':[100+i]}
            n['cells'][f'ff{i}']={'type':'DFFASRHQNx1_ASAP7_75t_R','attributes':{'src':'literal/ot_v41_rom_elem_w10.sv:191.13-193.71','keep':'1','dont_touch':'1'},'port_directions':{'QN':'output','CLK':'input'},'connections':{'QN':[200+i],'CLK':[2]}}
        return n
    def check(self,n):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'map.json';p.write_text(json.dumps({'modules':{'ot_v41_rom_elem_w10':n}}));return wake_cells(p)
    def test_real_eight_inverted_QN_outputs_pass(self):
        self.assertTrue(self.check(self.net())['passed'])
    def test_eight_aliases_one_driver_rejected(self):
        n=self.net();n['cells']={'ff0':n['cells']['ff0']}
        for w in n['netnames'].values():w['bits']=[100]
        self.assertFalse(self.check(n)['passed'])
    def test_wires_only_keep_does_not_qualify_cells(self):
        n=self.net()
        for c in n['cells'].values():c['attributes'].pop('keep')
        self.assertFalse(self.check(n)['passed'])
    def test_eight_cells_shared_output_rejected(self):
        n=self.net()
        for c in n['cells'].values():c['connections']['QN']=[200]
        self.assertFalse(self.check(n)['passed'])
if __name__=='__main__':unittest.main()
