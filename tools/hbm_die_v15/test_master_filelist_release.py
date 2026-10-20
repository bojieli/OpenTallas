import tempfile,unittest
from pathlib import Path
import master_filelist as m

class ReleaseFilelist(unittest.TestCase):
 def test_testbench_never_overrides_analog_interface(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);d=r/'rtl/hbm_accel/control';d.mkdir(parents=True)
   (d/'pll.sv').write_text('module pll(input a, output b); endmodule')
   (d/'tb_ck.sv').write_text('module pll(input a, output b); initial $fatal; endmodule')
   self.assertEqual(m.index(r)['pll'],['rtl/hbm_accel/control/pll.sv'])
 def test_explicit_release_dependency_maps_v1_sram(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);p=r/'rtl/model_ready_hbm_r14';p.mkdir(parents=True)
   f='rtl/model_ready_hbm_r14/release.sv'
   (r/f).write_text('module release; ot_sram_x u(); endmodule')
   q=r/'physical/asap7_memory_macros/ot_sram_x';q.mkdir(parents=True)
   (q/'ot_sram_x_bb.v').write_text('module ot_sram_x; endmodule')
   (q/'ot_sram_x.v').write_text('module ot_sram_x; reg [63:0] arr[0:127]; endmodule')
   self.assertNotIn('release',m.index(r))
   self.assertIn('release',m.index(r,[f]))
   result=m.resolve(r,'release',prefer=[f])
   self.assertEqual(result['unresolved'],[])
   self.assertEqual(result['macros'],[dict(module='ot_sram_x',file='physical/asap7_memory_macros/ot_sram_x/ot_sram_x_bb.v')])
   self.assertNotIn('physical/asap7_memory_macros/ot_sram_x/ot_sram_x.v',result['files'])

if __name__=='__main__':unittest.main()
