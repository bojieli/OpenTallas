import copy,json,tempfile,unittest
from pathlib import Path
from native_pin_contract import native_rects_match
from compact_coll_form import declare_clock_pin

RECT=['M5',147.924,236.232,147.972,236.760]
PIN=dict(bus='ck',bit=0,layer='M5',x=147.948,y=236.520,face='C',native_rects=[RECT])
class NativePinContractTest(unittest.TestCase):
 def test_exact_approved_metal_retains_offcenter_anchor(self):
  self.assertTrue(native_rects_match(PIN,[RECT],1000))
  self.assertNotEqual(PIN['y'],(RECT[2]+RECT[4])/2)
 def test_wrong_rectangle_layer_anchor_and_multiplicity(self):
  for bad in [['M5',147.924,236.231,147.972,236.760],['M4',*RECT[1:]],RECT+['bad']]:
   self.assertFalse(native_rects_match(PIN,[bad],1000))
  self.assertFalse(native_rects_match(PIN,[RECT,RECT],1000))
  p=dict(PIN,x=148);self.assertFalse(native_rects_match(p,[RECT],1000))
  p=dict(PIN,layer='M4');self.assertFalse(native_rects_match(p,[RECT],1000))
 def test_offgrid_declared_geometry_is_not_rounded_into_approval(self):
  p=copy.deepcopy(PIN);p['native_rects'][0][2]=236.2325
  self.assertFalse(native_rects_match(p,[RECT],1000))
 def test_metadata_emission_preserves_anchor_and_other_pins(self):
  with tempfile.TemporaryDirectory() as tmp:
   k=Path(tmp);other=dict(bus='data',bit=1,layer='M4',x=0,y=4,face='W')
   original=[dict(PIN),other];original[0].pop('native_rects')
   (k/'pins.json').write_text(json.dumps(original));declare_clock_pin(k)
   rows=json.loads((k/'pins.json').read_text());self.assertEqual(rows[1],other)
   self.assertEqual([rows[0]['x'],rows[0]['y']],[147.948,236.520])
   self.assertEqual(rows[0]['native_rects'],[RECT])

if __name__=='__main__':unittest.main()
