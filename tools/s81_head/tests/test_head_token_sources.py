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
   'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v':'(* blackbox *) module ot_rom_4096x274_m8(); endmodule',
   'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v':'''module ot_rom_4096x274_m8;
    initial begin
        for (init_i = 0; init_i < PR; init_i = init_i + 1) arr[init_i] = 0;
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir) && INSTANCE != "") $readmemh(rom_dir, arr);
    end
endmodule''',
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
 def test_scope_loader_preserves_shared_tile_parameters(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.setup_tree(r);p=r/'gen/s81_head_top.sv';p.write_text(p.read_text().replace('endmodule','endmodule : s81_head_top'))
   res=prepare(r,r/'plan.json',r/'physical.f',r/'native','scope')
   text=(r/'native/s81_head_top.sv').read_text()
   self.assertNotIn('#(.INSTANCE(',text)
   self.assertIn('s81_head_top.tile0.u_core.u_b.g_cv.u_eA0.u_m.u_rom0.viamap.hex',res['required_scope_images'])
   self.assertIn('s81_head_top.tile1.u_core.u_b.g_cvb.u_eB.u_m.u_rom1.viamap.hex',res['required_scope_images'])
   self.assertIn('HEAD missing scope image',(r/'native/ot_rom_4096x274_m8_scope.sv').read_text())
   self.assertEqual(res['unique_weight_images'],20)
 def test_shared_hierarchical_type_uses_actual_runtime_scope(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.setup_tree(r)
   res=prepare(r,r/'plan.json',r/'physical.f',r/'native','scope',True)
   self.assertIn('/*verilator hier_block*/',(r/'native/ot_s81hd_tile_p.sv').read_text())
   self.assertIn('s81_head_top.tile1.ot_s81hd_tile_p.u_core.u_b.g_cvb.u_eB.u_m.u_rom1.viamap.hex',res['required_scope_images'])
   self.assertEqual(res['added_cycles'],0)
 def test_native_declared_ports_use_native_functional_model(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.setup_tree(r)
   legacy='rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_bb.v'
   native='rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_bb_native.v'
   model='rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_native.sv'
   (r/native).write_text((r/legacy).read_text());(r/model).write_text('module ot_s81hd_elemA_cv(input ft_mstrap_i); endmodule')
   f=r/'physical.f';f.write_text(f.read_text().replace(legacy,native))
   wrapper=r/'gen/ot_s81hd_tile_p.sv';wrapper.write_text(wrapper.read_text().replace('ot_s81hd_tile #','ot_s81hd_tile_native #'))
   p=r/'plan.json';plan=json.loads(p.read_text());t=plan['partition_types']['hd_tile']
   t.update(contents=[{'module':'ot_s81hd_tile_native'}],simulation_substitutions={native:model},infra_ports=[{'name':str(i)} for i in range(40)])
   p.write_text(json.dumps(plan));res=prepare(r,p,f,r/'native')
   self.assertEqual(res['replacements'][native],model)
   self.assertEqual(res['tile_content'],'ot_s81hd_tile_native');self.assertEqual(res['infra_ports_per_tile'],40)
   self.assertIn('ot_s81hd_tile_native #(.INSTANCE(INSTANCE), .CV(1)',(r/'native/ot_s81hd_tile_p.sv').read_text())
   del t['simulation_substitutions'];p.write_text(json.dumps(plan))
   with self.assertRaisesRegex(ValueError,'explicit functional substitution'):prepare(r,p,f,r/'mut_missing_native_model')
 def test_partition_only_never_manufactures_a_die_provider(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.setup_tree(r);f=r/'physical.f'
   f.write_text('\n'.join(line for line in f.read_text().splitlines() if not line.endswith('s81_head_top.sv')))
   res=prepare(r,r/'plan.json',f,r/'partition',partition_only=True)
   self.assertFalse(res['generated_die_top'])
   self.assertFalse((r/'partition/s81_head_top.sv').exists())
   self.assertIn('parameter INSTANCE',(r/'partition/ot_s81hd_tile_p.sv').read_text())
   with self.assertRaisesRegex(ValueError,'exactly one generated die top'):prepare(r,r/'plan.json',f,r/'mut_no_provider')
 def test_infrastructure_functional_substitution_is_explicit(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.setup_tree(r)
   physical='gen/clock_physical.v';functional='gen/clock_functional.v'
   (r/physical).write_text('(* blackbox *) module CLKBUF(input A,output Y); endmodule')
   (r/functional).write_text('module CLKBUF(input A,output Y);assign Y=A;endmodule')
   f=r/'physical.f';f.write_text(f.read_text()+'\n'+physical)
   p=r/'plan.json';plan=json.loads(p.read_text());plan['infrastructure']={'sources':[physical],'simulation_substitutions':{physical:functional}};p.write_text(json.dumps(plan))
   res=prepare(r,p,f,r/'native')
   self.assertEqual(res['replacements'][physical],functional)
   del plan['infrastructure']['simulation_substitutions'];p.write_text(json.dumps(plan))
   with self.assertRaisesRegex(ValueError,'still contains blackbox'):prepare(r,p,f,r/'mut_unqualified_clock_model')
 def test_missing_tile_mutant_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.setup_tree(r);p=r/'gen/s81_head_top.sv';p.write_text(p.read_text().replace('tile1','lost_tile'))
   with self.assertRaisesRegex(ValueError,'tile instance tile1'):prepare(r,r/'plan.json',r/'physical.f',r/'native')
if __name__=='__main__':unittest.main()
