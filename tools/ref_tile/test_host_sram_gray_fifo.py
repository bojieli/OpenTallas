#!/usr/bin/env python3
"""Actual host SRAM interface and source-closure negative controls; heavy elaboration runs on fleet."""
import copy,json,re,shutil,tempfile,unittest
from pathlib import Path
import gray_fifo_cdc_constraints as G
ROOT=Path(__file__).resolve().parents[2]
MASTER='ot_sram_1r1w2c_32x546_m1_p192_mir'
VIEW=ROOT/'physical/asap7_memory_macros'/MASTER

class HostSramTests(unittest.TestCase):
 def test_actual_corner_roles(self):
  for corner in ('tt','ff','ss'):
   r=dict(G._liberty_dual_sram((VIEW/(MASTER+'_'+corner+'.lib')).read_text(),MASTER))
   self.assertEqual(r['wd_in'],'wclk');self.assertEqual(r['rd_out'],'rclk')
 def test_wrong_related_clock(self):
  s=(VIEW/(MASTER+'_tt.lib')).read_text().replace('related_pin : "wclk"','related_pin : "rclk"',1)
  with self.assertRaisesRegex(G.GrayFifoError,'arcs must relate'):
   G._liberty_dual_sram(s,MASTER)
 def test_missing_clock(self):
  s=(VIEW/(MASTER+'_tt.lib')).read_text().replace('clock : true','clock : false',1)
  with self.assertRaisesRegex(G.GrayFifoError,'clock/port directions'):
   G._liberty_dual_sram(s,MASTER)
 def test_wrong_bus_width(self):
  s=(VIEW/(MASTER+'_tt.lib')).read_text().replace('bit_width : 546','bit_width : 545',1)
  with self.assertRaisesRegex(G.GrayFifoError,'wrong Liberty width'):
   G._liberty_dual_sram(s,MASTER)
 def test_actual_source_and_model_fingerprints(self):
  import ref_tile
  spec=ref_tile.load_spec(ROOT/'rtl/test/host_cdc_safe_1020/pc_sram1.json')
  self.assertIsInstance(G._macro_clock_pins(spec,ROOT)[MASTER],dict)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);target=root/'physical/asap7_memory_macros'/MASTER
   shutil.copytree(VIEW,target)
   # Listed sources/ports remain identical; changing the behavioral source alone must still refuse.
   p=target/(MASTER+'.v');p.write_text(p.read_text()+'\n// unexpected source replacement\n')
   s=copy.deepcopy(spec);s['macros']=[m for m in spec['macros'] if Path(m['view']).name==MASTER]
   with self.assertRaisesRegex(G.GrayFifoError,'source/view changed'):
    G._macro_clock_pins(s,root)
 def test_no_implicit_dual_clock_admission(self):
  import ref_tile
  spec=ref_tile.load_spec(ROOT/'rtl/test/host_cdc_safe_1020/pc_sram1.json')
  spec['reviewed_gray_fifo_extensions'].pop('dual_clock_srams')
  with self.assertRaisesRegex(G.GrayFifoError,'exactly one Liberty clock'):
   G._macro_clock_pins(spec,ROOT)

if __name__=='__main__':unittest.main()
