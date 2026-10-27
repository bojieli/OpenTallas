import json
import os
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from head_token_sources import prepare

class NativeWeightIdentity(unittest.TestCase):
 def setup_tree(self,r):
  texts={
   'rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_bb.v':'(* blackbox *) module ot_s81hd_elemA_cv(); endmodule',
   'rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv.sv':'module ot_s81hd_elemA_cv(); wire real_model=1; endmodule',
   'rtl/dsrom_sys/s81_head/ot_s81hd_oreg.sv':'module ot_s81hd_oreg(); endmodule',
   'gen/ot_s81hd_tile_p.sv':'module ot_s81hd_tile_p(input clk); ot_s81hd_tile #(.CV(1), .CMP_STAGES(3)) u_core (.ck(clk)); endmodule',
   'gen/s81_head_top.sv':'module s81_head_top; ot_s81hd_tile_p tile0 (.clk(clk)); ot_s81hd_tile_p tile1 (.clk(clk)); endmodule'}
  for s,t in texts.items():(r/s).parent.mkdir(parents=True,exist_ok=True);(r/s).write_text(t)
  p={'partition_types':{'hd_tile':{'module':'ot_s81hd_tile_p'}},'partitions':[{'name':'tile0','type':'hd_tile'},{'name':'tile1','type':'hd_tile'}]}
  (r/'plan.json').write_text(json.dumps(p));(r/'physical.f').write_text('\n'.join([s for s in texts if not(s.endswith('cv.sv') or s.endswith('oreg.sv'))]))
  return texts
 def test_unique_images_and_unchanged_content_parameters(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);original=self.setup_tree(r);res=prepare(r,r/'plan.json',r/'physical.f',r/'native')
   self.assertEqual(res['unique_weight_images'],20)
   self.assertEqual(res['added_cycles'],0)
   self.assertIn('.CV(1), .CMP_STAGES(3)',(r/'native/ot_s81hd_tile_p.sv').read_text())
   self.assertIn('.INSTANCE("tile0")',(r/'native/s81_head_top.sv').read_text())
   self.assertIn('.INSTANCE("tile1")',(r/'native/s81_head_top.sv').read_text())
   for s,t in original.items():self.assertEqual((r/s).read_text(),t)
 def test_repo_relative_cli_paths(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.setup_tree(r);before=Path.cwd()
   try:
    os.chdir(r);res=prepare(r,Path("plan.json"),Path("physical.f"),Path("native"))
   finally:os.chdir(before)
   self.assertEqual(res["unique_weight_images"],20)
 def test_missing_tile_mutant_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.setup_tree(r);p=r/'gen/s81_head_top.sv';p.write_text(p.read_text().replace('tile1','lost_tile'))
   with self.assertRaisesRegex(ValueError,'tile instance tile1'):prepare(r,r/'plan.json',r/'physical.f',r/'native')
if __name__=='__main__':unittest.main()
