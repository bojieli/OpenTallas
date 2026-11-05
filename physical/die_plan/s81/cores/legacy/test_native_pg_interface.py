"""Native M5 hard children need real transverse PG metal, under the plan's obstruction grant."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_core_kit_legacy as G

class NativePG(unittest.TestCase):
    def lef(self,d,name,vdd='M4',vss='M4'):
        s=f'MACRO {name}\n SIZE 64.8 BY 54 ;\n'
        for pin,layer in (('VDD',vdd),('VSS',vss)):
            if layer:s+=f' PIN {pin}\n USE POWER ;\n PORT\n LAYER {layer} ;\n RECT 6 4 6.12 49 ;\n END\n END {pin}\n'
        (d/(name+'.lef')).write_text(s+f'END {name}\n')
    def test_existing_no_macro_and_m4_only_bytes(self):
        self.assertEqual(G.macro_pdn({},None),(G.PDN,None))
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);self.lef(d,'sram')
            self.assertEqual(G.macro_pdn({'sram':[]},d),(G.PDN+G.PDN_MACRO,None))
    def test_mixed_native_real_bridge_and_preserved_sram(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);self.lef(d,'sram');self.lef(d,'hist','M5','M5')
            out,info=G.macro_pdn({'sram':[],'hist':[]},d,'M7')
            self.assertIn('add_pdn_stripe -grid {top} -layer {M6}',out)
            self.assertIn('add_pdn_connect -grid {top} -layers {M5 M6}',out)
            self.assertIn('-grid {native_pg_M5} -layers {M5 M6}',out)
            self.assertIn('-grid {native_pg_M4} -layers {M4 M5}',out)
            self.assertIn('-name {native_pg_M4} -cells {{^sram$}} -voltage_domains {CORE} -halo {2.0 2.0}',out)
            self.assertIn('-name {native_pg_M5} -cells {{^hist$}} -voltage_domains {CORE} -halo {2.0 2.0}',out)
            self.assertEqual(info['added_signal_routing_layers'],[])
            self.assertEqual(info['declared_parent_obs_max'],'M7')
            for cap in (None,'M4','M5'):
                with self.assertRaisesRegex(ValueError,'obs_max'):G.macro_pdn({'hist':[]},d,cap)
    def test_invalid_pg_interface_fails(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            for a,b in (('M5','M4'),('M4',None),('M7','M7')):
                self.lef(d,'bad',a,b)
                with self.assertRaises(ValueError):G.macro_pdn({'bad':[]},d,'M7')

if __name__=='__main__':unittest.main()
