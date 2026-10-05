import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dsrom_noECC_WAKE_physical_prepare import annotation_only,restore_signed_labels
class Annotation(unittest.TestCase):
    def pair(self):
        cells={str(i):{'type':'DFFASRHQNx1_ASAP7_75t_R','attributes':{'src':'literal/ot_v41_rom_elem_w10.sv:191.13-193.71'},'connections':{'QN':[100+i],'D':[1]},'parameters':{}} for i in range(8)}
        a={'modules':{'ot_v41_rom_elem_w10':{'cells':cells,'ports':{'clk':{'bits':[2]}}}}};b=copy.deepcopy(a)
        for c in b['modules']['ot_v41_rom_elem_w10']['cells'].values():c['attributes'].update(keep='1',dont_touch='1')
        return a,b
    def test_only_eight_attributes_allowed(self):
        a,b=self.pair();self.assertTrue(annotation_only(a,b))
    def test_payload_connection_change_rejected(self):
        a,b=self.pair();b['modules']['ot_v41_rom_elem_w10']['cells']['0']['connections']['D']=[3];self.assertFalse(annotation_only(a,b))
    def test_port_change_rejected(self):
        a,b=self.pair();b['modules']['ot_v41_rom_elem_w10']['ports']['clk']['bits']=[3];self.assertFalse(annotation_only(a,b))
    def test_unrelated_cell_attribute_change_rejected(self):
        a,b=self.pair();b['modules']['ot_v41_rom_elem_w10']['cells']['0']['attributes']['new_policy']='1';self.assertFalse(annotation_only(a,b))
    def test_signed_label_restore_preserves_exact_bits(self):
        a,b=self.pair();a['modules']['ot_v41_rom_elem_w10']['netnames']={'internal':{'bits':[7],'signed':1}}
        b['modules']['ot_v41_rom_elem_w10']['netnames']={'internal':{'bits':[7]}}
        self.assertEqual(restore_signed_labels(a,b),1)
        self.assertTrue(annotation_only(a,b))
    def test_signed_restore_rejects_connectivity_change(self):
        a,b=self.pair();a['modules']['ot_v41_rom_elem_w10']['netnames']={'internal':{'bits':[7],'signed':1}}
        b['modules']['ot_v41_rom_elem_w10']['netnames']={'internal':{'bits':[8]}}
        with self.assertRaises(ValueError):restore_signed_labels(a,b)
if __name__=='__main__':unittest.main()
