import importlib.util
import tempfile
import pathlib
import unittest
spec=importlib.util.spec_from_file_location('clock',pathlib.Path(__file__).with_name('kvspc_core_clock.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class HeadClock(unittest.TestCase):
 def check(self,already):
  with tempfile.TemporaryDirectory() as d:
   k=pathlib.Path(d);(k/'rtl').mkdir()
   decl='parameter integer CORE_CLOCK=0,' if already else ''
   forward='.CORE_CLOCK(CORE_CLOCK),' if already else ''
   (k/'rtl/head.sv').write_text('module qkd_static_kv_pc_path_fan_nc_b_head_p #('+decl+'parameter MU=1)(input ck); qkd_static_kv_pc_path_emb_nc_b #('+forward+'.MU(MU)) u_pce (.ck(ck)); endmodule\nmodule wrapper; qkd_static_kv_pc_path_fan_nc_b #(.MU(1)) u_pc(); endmodule')
   for n in ('qkd_static_kv_pc_path_nc.sv','qkd_ctrl_pc_nc.sv','ot_qkd_static_ctrl_pc_emb.sv','ot_qkd_static_kv_timing.sv'):(k/'rtl'/n).write_text('// CORE_CLOCK')
   m.apply_kit(k)
   text=(k/'rtl/head.sv').read_text()
   self.assertEqual(text.count('parameter integer CORE_CLOCK'),1)
   self.assertEqual(text.count('.CORE_CLOCK(CORE_CLOCK)'),1)
   self.assertEqual(text.count('.CORE_CLOCK(1)'),1)
 def test_old_variant(self):self.check(False)
 def test_current_variant(self):self.check(True)
if __name__=='__main__':unittest.main()
