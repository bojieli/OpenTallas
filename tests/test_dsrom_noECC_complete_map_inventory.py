import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dsrom_noECC_complete_element_map import inventory

class InventoryTests(unittest.TestCase):
    def fixture(self):
        return {'modules':{'ot_v41_rom_elem_w10':{'netnames':{
            'g_wake.g_leaf[0].wake':{'bits':[20]},
            'g_wake.g_leaf[1].wake':{'bits':[20]},
            'leafclock':{'bits':[10]}},'cells':{
            'metadata':{'type':'$scopeinfo','connections':{},'attributes':{}},
            'gate':{'type':'ICG','connections':{'CLK':[2],'GCLK':[10]},'attributes':{}},
            'ff':{'type':'DFF','connections':{'CLK':[10],'D':[30],'QN':[31]},'attributes':{'src':'literal/ot_v41_rom_elem_w10.sv:746.9-749.12'}},
            'macro':{'type':'ot_rom_4096x274_m8','connections':{'clk':[10]},'attributes':{}}}}}}

    def measure(self,net,corner='ss'):
        cells={'DFF':'cell(DFF){area:2; pin(CLK){clock:true; capacitance:0.5;} pin(D){capacitance:0.3;} pin(QN){}}',
            'ICG':'cell(ICG){area:3; pin(CLK){clock:true; capacitance:1;} pin(GCLK){}}'}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'mapped.json';p.write_text(json.dumps(net));return inventory(p,cells,corner)

    def test_metadata_not_hardware_and_macro_clock_included(self):
        m=self.measure(self.fixture())
        self.assertEqual(m['cells'],3)
        self.assertEqual(m['Yosys_scopeinfo_metadata_not_hardware'],1)
        self.assertEqual(m['unmapped_nonmacro_types'],{})
        self.assertEqual(m['stdcell_area_um2'],5)
        self.assertAlmostEqual(m['clock_nets']['10']['pin_cap_fF'],9.1838)
        self.assertEqual(m['clock_nets']['10']['sinks'],2)
        self.assertEqual(m['capture_flops_identified'],1)

    def test_merged_wake_cannot_pass_replica_gate(self):
        m=self.measure(self.fixture())
        self.assertEqual(m['distinct_WAKE_FF_output_nets'],1)
        self.assertFalse(m['source_8leaf_WAKE_replica_retention_pass'])

    def test_unknown_real_cell_stays_rejection(self):
        n=self.fixture();n['modules']['ot_v41_rom_elem_w10']['cells']['unknown']={'type':'$unmapped_real','connections':{},'attributes':{}}
        m=self.measure(n)
        self.assertEqual(m['unmapped_nonmacro_types'],{'$unmapped_real':1})

    def test_corner_pin_values_do_not_share_or_doublecount_aliases(self):
        n=self.fixture();n['modules']['ot_v41_rom_elem_w10']['netnames']['secondalias']={'bits':[10]}
        m=self.measure(n,'ff')
        self.assertAlmostEqual(m['clock_nets']['10']['pin_cap_fF'],10.8732)
        self.assertEqual(m['clock_nets']['10']['sinks'],2)

if __name__=='__main__':unittest.main()
