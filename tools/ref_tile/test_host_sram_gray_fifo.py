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

 def test_actual_top_proof_and_wrong_writer_clock(self):
  import ref_tile
  spec=ref_tile.load_spec(ROOT/'rtl/test/host_cdc_safe_1020/pc_sram1.json')
  proof=G.lint(spec,ROOT)
  self.assertEqual(len(proof['fifos']),2)
  self.assertEqual(len(proof['macros']),4)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   files=set(spec['sources'])|{'physical/common_flow/ot_keep_regs.tcl'}
   for item in spec['macros']:
    files.update(str(p.relative_to(ROOT)) for p in (ROOT/item['view']).iterdir() if p.suffix in ('.v','.lib'))
   for f in files:
    dest=root/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/f,dest)
   p=root/'rtl/qwen_sys/host_cluster_20261017/qkd_hr_cdc_pc_sram.v'
   text=p.read_text();assert text.count('.wclk(ck_phy_fam)')==1
   p.write_text(text.replace('.wclk(ck_phy_fam)','.wclk(ck_core)'))
   with self.assertRaisesRegex(G.GrayFifoError,'wrong family|one family|writer and reader'):
    G.lint(spec,root)

if __name__=='__main__':unittest.main()
