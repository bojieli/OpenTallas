"""Check the new source join preserves Euclid's authority and actual clock."""
import json,re,tempfile,unittest
from pathlib import Path
from tools.hbm_accel.install_capture_join import install,ROOT
BASE=ROOT/'rtl/model/qwen_hbm_integrated_20261003/ranked'

class CaptureInstallation(unittest.TestCase):
 def test_actual_body_and_taps(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=install(BASE,Path(tmp));s=(out/'ot_gpu_qwen_hbm_integrated_ranked_ha1.sv').read_text()
   old=(BASE/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
   # Original hardware, all ready/ACK/retirement/grant wiring remain exactly intact.
   body=s[s.index(');')+2:s.index('assign ha1_enabled=')].rstrip()
   oldbody=old[old.index(');')+2:old.rindex('endmodule')].rstrip()
   self.assertEqual(body,oldbody)
   for wire in ('issuer_backend_go_valid[h] && issuer_backend_go_ready[h]',
    'sm_rf_ack_accept[h]','issuer_producer_visible_valid[h] && issuer_producer_visible_ready[h]',
    'issuer_frame_retire_valid[h] && issuer_frame_retire_ready[h]',
    'ha1_w6_visible_valid[h] && ha1_w6_visible_ready[h]'):
    self.assertIn(wire,s)
   self.assertIn('.clk(stream_clk)',s);self.assertIn('HA1_ENABLE=0',s)
   book=json.loads((out/'ports.json').read_text())
   self.assertEqual(book['inventory']['HA1_capture_join_count'],64)
   for name,width in [('dependency_tuple',239),('dependency_owner55',55),('dependency_page_mask',32),('w6_visible_owner55',55)]:
    self.assertEqual(book['pins']['ha1_'+name]['leaf_bits'],width)
   sources=(out/'sources.f').read_text()
   self.assertNotIn('ranked/ot_gpu_qwen_hbm_integrated_ranked.sv',sources)
   self.assertIn('ot_hbm_w6_source_select.sv',sources)
   driver=(out/'pin_driver.cpp').read_text()
   self.assertEqual(driver.count('else if(op=="EDGE")'),1)
   self.assertIn('if(name=="ha1_w6_visible_owner55")',driver)
   self.assertIn('if(name=="ha1_dependency_tuple")',driver)
 def test_baseline_fence_is_selected_by_default(self):
  s=(ROOT/'rtl/hbm_accel/txcount/ot_hbm_w6_source_select.sv').read_text()
  self.assertIn("LIVE_STATE=1'b0",s)
  self.assertIn('ot_gpu_rf_visibility_fence_w6 #(.ENABLE(ENABLE)) actual',s)
  self.assertNotIn('.input(input)',s)
  self.assertNotIn('.output(output)',s)

if __name__=='__main__':unittest.main()
