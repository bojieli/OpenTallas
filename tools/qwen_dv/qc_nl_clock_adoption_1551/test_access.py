"""Bounded source witness controls; no routed DRC or parent signoff claim."""
import importlib.util
from pathlib import Path
import unittest
import json
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"tools/die_plan"))
import kit_contract as K
import gen_phys as GP

p=Path(__file__).with_name('prepare_access.py')
s=importlib.util.spec_from_file_location('prepare_access',p)
A=importlib.util.module_from_spec(s);s.loader.exec_module(A)


def fixture(extra=''):
    return '''MACRO core
 SIZE 10 BY 10 ;
 PIN ck
  PORT
   LAYER M5 ;
    RECT 4.9 4.7 5.1 5.3 ;
  END
 END ck
 '''+extra+'''
 OBS
  LAYER M6 ;
   RECT 0 0 4 10 ;
  LAYER M7 ;
   RECT 6 0 10 10 ;
 END
END core
'''

class Access(unittest.TestCase):
    footprints={5:[(4.98,4.98,5.02,5.02)],6:[(4.95,4.98,5.05,5.02)],7:[(4.98,4.616,5.02,5.384)]}
    def check(self,text,fp=None):
        b,t,_=A.G.geometry(text,'core','ck',7,(0,0,'MY'))
        return A.G.entry_clear(fp or self.footprints,b,t,7)
    def test_actual_rectangular_window(self): self.assertTrue(self.check(fixture()))
    def test_pg_is_obstruction(self):
        pg='PIN VDD\n PORT\n LAYER M6 ;\n RECT 4.99 4.99 5.01 5.01 ;\n END\nEND VDD'
        self.assertFalse(self.check(fixture(pg)))
    def test_blanket_obs_blocks(self):
        self.assertFalse(self.check(fixture().replace('RECT 0 0 4 10','RECT 0 0 10 10')))
    def test_wrong_pin_identity_rejected(self):
        with self.assertRaises(ValueError): self.check(fixture().replace('PIN ck','PIN other').replace('END ck','END other'))
    def test_missing_upper_obs_rejected(self):
        with self.assertRaises(ValueError): self.check(fixture().replace('LAYER M7','LAYER M4'))
    def test_missing_conductor_rejected(self):
        self.assertFalse(self.check(fixture(),{5:self.footprints[5],7:self.footprints[7]}))
    def test_lower_pad_must_fit_real_pin(self):
        fp=dict(self.footprints);fp[5]=[(4.8,4.9,5.05,5.1)]
        self.assertFalse(self.check(fixture(),fp))
    def test_unknown_geometry_rejected(self):
        with self.assertRaises(ValueError): self.check(fixture().replace('RECT 0 0 4 10','POLYGON 0 0 4 10'))
    def test_nonzero_origin_rejected(self):
        with self.assertRaises(ValueError): self.check(fixture().replace('SIZE 10','ORIGIN 1 0 ;\n SIZE 10'))
    def test_unsupported_orientation_rejected(self):
        with self.assertRaises(ValueError): A.G.geometry(fixture(),'core','ck',7,(0,0,'R90'))

class KitEntry(unittest.TestCase):
    def test_staged_plan_lef_and_real_emitted_pin(self):
        with tempfile.TemporaryDirectory() as td:
            kd=Path(td); (kd/'macros').mkdir()
            (kd/'macros/core.lef').write_text(fixture())
            access={'pin':'ck','footprints_um':{f'M{k}':v for k,v in Access.footprints.items()}}
            core={'inst':'u_core','module':'core','outline_um':[10,10],'origin_um':[0,0],
                  'orient':'MY','clock_entry_access':access}
            plan={'partition_types':{'type':{'hard_cores':[core]}}}
            (kd/'die_plan.json').write_text(json.dumps(plan))
            (kd/'macro.tcl').write_text('place_macro -macro_name u_core -location {0 0} -orientation MY\n')
            (kd/'config.mk').write_text('export MACRO_PLACEMENT_TCL = /work/macro.tcl\n')
            (kd/'io.tcl').write_text('place_pin -pin_name clk_c0 -layer M7 -location {5 5} -pin_size {0.04 0.768}\n')
            row={'port':'clk_c0','inst':'u_core','pin':'ck','clock_entry_access':access}
            budget={'schema':'opentallas.die_plan.partition_budget.v1','type':'type','signal_max':'M7','clock':{'core_taps':[row]}}
            (kd/'budget.json').write_text(json.dumps(budget))
            entries=[('io.tcl','clk_c0',5.,5.)]
            errors,_=K.clock_entry_clear(kd,kd,entries)
            self.assertEqual(errors,[])
            # Default stays solid even though the LEF contains a real opening.
            row.pop('clock_entry_access')
            (kd/'budget.json').write_text(json.dumps(budget))
            self.assertTrue(K.clock_entry_clear(kd,kd,entries)[0])
            row['clock_entry_access']=dict(access,pin='other')
            (kd/'budget.json').write_text(json.dumps(budget))
            self.assertTrue(K.clock_entry_clear(kd,kd,entries)[0])

class GeneratorEntry(unittest.TestCase):
    def test_only_exact_selected_clock_can_enter(self):
        with tempfile.TemporaryDirectory() as td:
            lef=Path(td)/'core.lef'; lef.write_text(fixture())
            core={'inst':'u_core','module':'core','outline_um':[10,10],
                  'clock_entry_access':{'pin':'ck','footprints_um':{f'M{k}':v for k,v in Access.footprints.items()}}}
            p=SimpleNamespace(types={'type':{'hard_cores':[core]}},
                layer_budget={'partition_signal_max':'M7'},layers={'M7':{'dir':'V','width_um':.04}})
            macro=('u_core','core',str(lef),None,0,0,'MY')
            with patch.object(GP,'type_macros',return_value=[macro]), patch.object(GP,'core_tap_rows',return_value=[('clk_c0','u_core','ck',0,0)]):
                self.assertEqual(GP.entry_block_boxes(p,'type',root=td,port='clk_c0',entry_xy=(5,5)),[])
                self.assertEqual(GP.entry_block_boxes(p,'type',root=td,port='other',entry_xy=(5,5)),[(0.,0.,10.,10.)])
                core.pop('clock_entry_access')
                self.assertEqual(GP.entry_block_boxes(p,'type',root=td,port='clk_c0',entry_xy=(5,5)),[(0.,0.,10.,10.)])

if __name__=='__main__': unittest.main()
