import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dsrom_noECC_production_context import build,cells,actual_wake,protection_tcl
class ProductionContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model=build()
    def test_exact_complete_physical_masters_and_area(self):
        for c in self.model['cases'].values():
            self.assertTrue(c['Liberty_area_match']);self.assertGreater(len(c['named_physical_master_inventory']),40)
            self.assertEqual(len(c['actual_Verilog_ROM']),4)
            self.assertEqual(len(c['actual_Verilog_captureDFF']),1088)
    def test_final_names_differ_from_json_and_are_protected(self):
        for c in self.model['cases'].values():
            names=[w['name'] for w in c['actual_Verilog_WAKEDFF']]
            self.assertEqual(len(set(names)),8)
            self.assertTrue(all(n.startswith('_') for n in names))
            self.assertEqual(c['protection_Tcl'].count('set_dont_touch'),8)
    def test_real_clock_and_power_pins_have_shapes(self):
        for c in self.model['cases'].values():
            m=c['named_physical_master_inventory']['ICGx1_ASAP7_75t_R']
            pins={p['name']:p for p in m['pins']}
            for n in ('CLK','GCLK','ENA','VDD','VSS'):self.assertTrue(pins[n]['rectangles'])
    def test_escaped_rom_instance_is_counted(self):
        self.assertEqual(cells('  ot_rom_4096x274_m8 \\g_mac[0].u_rom  (\n    .clk(clk)\n  );\n')[0]['name'],'\\g_mac[0].u_rom')
    def test_collapsed_wa_ke_cannot_be_protected(self):
        with self.assertRaises(ValueError):protection_tcl(['one']*8)
        with self.assertRaises(ValueError):actual_wake([])
    def test_policy_match_not_library_invalid_or_physical_closure(self):
        self.assertFalse(self.model['G0_physical_implementation_admitted'])
        for c in self.model['cases'].values():
            self.assertGreater(sum(c['default_dont_use_matches_existing_cells'].values()),1000)
            self.assertTrue(c['existing_instances_are_not_library_invalid'])
            self.assertFalse(c['PG_clock_IO_installed'])
if __name__=='__main__':unittest.main()
