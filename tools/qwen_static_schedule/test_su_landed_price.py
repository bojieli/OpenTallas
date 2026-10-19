import json,tempfile,unittest
from pathlib import Path
from . import su_landed_price as S
from .calendar import ScheduleError
RECEIPT=Path(__file__).resolve().parents[2]/'results/rtl/mu_qwen_1018/admission/su_landed_price/source_su8_timing.json'
class SULandedPrice(unittest.TestCase):
 def test_default_unchanged(self):
  c=S.load();self.assertEqual(c['capture_edges'],0);self.assertFalse(c['enabled'])
 def test_five_measured_capture_windows(self):
  c=S.load(variant=S.VARIANT,receipt=RECEIPT)
  for old,span,new in [(183,96,189),(134,86,140),(104,16,110),(64,16,70),(190,16,196)]:
   w=S.capture_window(issue=1000,baseline_last=old,span=span,contract=c)
   self.assertEqual(w['last']-1000,new);self.assertEqual(w['last']-w['first']+1,span)
  self.assertFalse(c['production_bound']);self.assertFalse(c['apply_to_public_F16'])
 def test_foreign_variant_rejected(self):
  with self.assertRaises(ScheduleError):S.load(variant='other',receipt=RECEIPT)
 def test_missing_receipt_rejected(self):
  with self.assertRaises(ScheduleError):S.load(variant=S.VARIANT)
 def test_unmeasured_zero_delta_rejected(self):
  r=json.loads(RECEIPT.read_text());r['ports']['S0DD']['delta_edges']=0
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'mut.json';p.write_text(json.dumps(r))
   with self.assertRaisesRegex(ScheduleError,'receipt hash mismatch'):S.load(variant=S.VARIANT,receipt=p)
if __name__=='__main__':unittest.main()
