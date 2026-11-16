import json,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent/'die_plan'))
import final_physical_contract as F
import export_view as E
import die_sta_related as D
from test_export_view import mk_run

DEF='''DESIGN m ;
UNITS DISTANCE MICRONS 1000 ;
DIEAREA ( 0 0 ) ( 12000 8000 ) ;
PINS 2 ;
 - a + NET a + DIRECTION INPUT + USE SIGNAL
 + PORT + LAYER M5 ( -100 -10 ) ( 100 10 ) + FIXED ( 100 1000 ) N ;
 - ck + NET ck + DIRECTION INPUT + USE CLOCK
 + PORT + LAYER M4 ( -10 -100 ) ( 10 100 ) + FIXED ( 5000 100 ) N ;
END PINS
'''
LEF='''MACRO m
 SIZE 12 BY 8 ;
 PIN a
 DIRECTION INPUT ;
 USE SIGNAL ;
 PORT
 LAYER M5 ;
 RECT 0 .99 .2 1.01 ;
 END
 END a
 PIN ck
 DIRECTION INPUT ;
 USE CLOCK ;
 PORT
 LAYER M4 ;
 RECT 4.99 0 5.01 .2 ;
 END
 END ck
END m
'''
class TestFinalPhysicalContract(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
  self.kit,_=mk_run(self.root);self.base=self.root/'arch/base';(self.base/'6_final.def').write_text(DEF);(self.base/'m.lef').write_text(LEF)
 def tearDown(self):self.t.cleanup()
 def test_actual_contract_and_loader_preserve_requested_history(self):
  old=(self.kit/'pins.json').read_bytes();out=self.root/'newview'
  res=E.export(str(self.kit),str(self.kit/'signoff/signoff.json'),str(out),'qwen_kvsys',final_physical_contract=True)
  self.assertTrue(res['complete'],res['problems']);v=out/'m';p=json.loads((v/'provenance.json').read_text())
  self.assertEqual(p['kit']['outline_um'],[10,8]);self.assertEqual(p['final_physical']['outline_um'],[12,8]);self.assertEqual((v/'requested_pins.json').read_bytes(),old)
  self.assertEqual((self.kit/'pins.json').read_bytes(),old)
  with patch.object(D,'parse_etm',return_value=dict(out_max_ps=1,out_min_ps=0,in_setup_ps=1,in_hold_ps=0)):
   meta=D.core_view_model('m',v,'TT',2,0)['meta']
  self.assertEqual(meta['outline_um'],[12,8])
  plan=self.root/'plan.json';plan.write_text(json.dumps(dict(pins=[dict(name='a',layer='M5',x=.1,y=1),dict(name='ck',layer='M4',x=5,y=.1)])))
  self.assertEqual(D.pins_relation(meta,str(plan),None,[12,8]),('canonical',None))
  with self.assertRaisesRegex(ValueError,'NEW view version'):
   E.export(str(self.kit),str(self.kit/'signoff/signoff.json'),str(out),'qwen_kvsys',final_physical_contract=True)
 def test_changed_rect_is_refused(self):
  (self.base/'m.lef').write_text(LEF.replace('RECT 0 .99 .2 1.01','RECT 0 .99 .4 1.01'))
  with self.assertRaisesRegex(ValueError,'rectangle differs'):F.derive(self.base/'6_final.def',self.base/'m.lef','m')
 def test_changed_outline_is_refused(self):
  (self.base/'m.lef').write_text(LEF.replace('SIZE 12','SIZE 10'))
  with self.assertRaisesRegex(ValueError,'outlines differ'):F.derive(self.base/'6_final.def',self.base/'m.lef','m')
 def test_missing_pin_is_refused(self):
  (self.base/'6_final.def').write_text(DEF.replace('PINS 2','PINS 3'))
  with self.assertRaisesRegex(ValueError,'incomplete'):F.derive(self.base/'6_final.def',self.base/'m.lef','m')
if __name__=='__main__':unittest.main()
