"""Static full-source, oracle-separation and pin gates only; never HDL compilation."""
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('join',ROOT/'tools/prepare_dsrom_actual_element_rne_wake.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
MODEL=json.loads((ROOT/G.BASE/'model.json').read_text())
OLD=(ROOT/'rtl/test/tb_dsrom_actual_element_numerical.sv').read_text();BENCH=(ROOT/G.BENCH).read_text()
def task(text,name):return text.split('    task '+name,1)[1].split('    endtask',1)[0]
class JoinTests(unittest.TestCase):
 def test_all_pins_and_exact_composition(self):
  self.assertEqual(MODEL,G.verify())
  for path,text in G.compose_sources().items():self.assertEqual(text,(ROOT/path).read_text())
 def test_fresh_full48file_package_and_caps(self):
  plan=json.loads((ROOT/G.BASE/'sourceplan.json').read_text());files=G.package()
  self.assertEqual(48,len(files));self.assertEqual(MODEL['generated_files_sha256'],{p:G.sha(t.encode()) for p,t in files.items()})
  for case in ('q','bfcolumn'):
   argv=plan['compile_plan_proposed_only'][case]
   self.assertEqual('2',argv[argv.index('-j')+1]);self.assertEqual('tb_'+case,argv[argv.index('--top-module')+1])
   self.assertEqual({p for p in files if p.endswith('.sv')},{p for p in argv if p.endswith('.sv')})
  self.assertEqual(4294967296,MODEL['resources']['aggregate_memory_bytes']);self.assertEqual([0,1],MODEL['resources']['cpu_affinity'])
  self.assertEqual((600,60,660),tuple(MODEL['resources'][k] for k in ('build_summed_seconds','sim_summed_seconds','whole_cgroup_seconds')))
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'fresh';receipt=G.prepare(out);self.assertEqual(48,len(receipt['files_sha256']))
   with self.assertRaises(FileExistsError):G.prepare(out)
 def test_shared_primitive_implementation_only(self):
  pkg=G.package();sources={**G.L.load_sources(),**{p:(ROOT/p).read_text() for p in G.EXTRA}}
  names=set(re.findall(r'^\s*module\s+(\w+)', '\n'.join(sources.values()),re.M))
  for p in G.EXTRA:
   for side in ('ref_','cand_'):
    self.assertEqual(G.L.namespace((ROOT/p).read_text(),names,side),pkg[side+Path(p).name])
  lanes=(ROOT/G.COPIES['rtl/v41rom/ot_v41_bf16_lanes2.sv']).read_text()
  self.assertIn('l < 16',lanes);self.assertIn('ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(GRADUAL_RNE))',lanes)
  self.assertNotIn('ot_v41_bmul2 u_m',lanes)
 def test_defaultoff_threading_and_exact_geometry(self):
  for p in G.COPIES.values():self.assertIn('parameter integer GRADUAL_RNE = 0',(ROOT/p).read_text())
  for p in list(G.COPIES.values())[:2]:self.assertIn('parameter integer WAKE_REG = 0',(ROOT/p).read_text());self.assertIn('parameter integer FIX_SECOND_ROW_INDEX = 0',(ROOT/p).read_text())
  self.assertEqual(2,BENCH.count('.FIX_SECOND_ROW_INDEX(1),.GRADUAL_RNE(1),.WAKE_REG(1)'))
  shape='.NSEG(8),.NCH(16),.XF(XF),.LV(5),.BF16(BF),.MTP(1),.EARLY(1),.FAST(1),.PP(1),.BP(0),.PHW(6)'
  self.assertEqual(2,BENCH.count(shape));self.assertIn('#(.BF(0),.XF(4))',BENCH);self.assertIn('#(.BF(1),.XF(8))',BENCH)
 def test_all72original_DIFF_and_scores_preserved(self):
  old=re.findall(r'"(DIFF [^"]*)"',task(OLD,'compare_all;'))
  new=re.findall(r'"(DIFF [^"]*)"',task(BENCH,'compare_all;'))
  self.assertEqual(72,len(old));self.assertEqual(88,len(new))
  for marker in old:self.assertEqual(old.count(marker),new.count(marker))
  for name in ('check_numerical;','complete_oracle;','clear_oracle;','config_contract_oracle;','load_phase(','start_phase;','stream_phase;','reset_now;'):
   self.assertEqual(task(OLD,name),task(BENCH,name))
  for line in OLD.splitlines():
   if '$fatal' in line and 'gate latch' not in line:self.assertIn(line,BENCH)
 def test_immutable_ROM_inputs_oracle_and_no_injection(self):
  pkg=G.package();oldpkg=G.N.package()
  for p in ('dsrom_actual_element_numerical_rom.cpp','dsrom_actual_element_numerical_stimulus.svh','dsrom_actual_element_numerical_expected.svh'):
   self.assertEqual(oldpkg[p],pkg[p])
  self.assertNotIn('expected',pkg['dsrom_actual_element_numerical_rom.cpp'].lower().split('\n',1)[1])
  self.assertEqual(1,BENCH.count('expected_word=numerical_expected('))
  self.assertIn('r_perr[m] || c_perr[m]',BENCH)
  self.assertIn('oracle_rows!=(BF?456:344)',BENCH);self.assertIn('oracle_configs!=32*(BF?14:11)',BENCH)
 def test_helper_only_namespace_delta_and_CSA(self):
  pkg=G.package()
  for name in [p[len('ref_'):] for p in pkg if p.startswith('ref_')]:
   ref=pkg['ref_'+name];cand=pkg['cand_'+name]
   names=set(re.findall(r'^\s*module\s+(\w+)',ref,re.M))
   # Convert only generated module identifiers, not comments or DPI INSTANCE strings.
   converted=G.L.namespace(ref,names,'unused_') if False else re.sub(r'\bref_(ot_\w+)\b',r'cand_\1',ref)
   if name=='ot_prefix.sv':converted=G.L.replace_helpers(converted.replace('cand_ot_v41_ksadd','ot_v41_ksadd').replace('cand_ot_v41_inc','ot_v41_inc')).replace('module ot_v41_ksadd','module cand_ot_v41_ksadd').replace('module ot_v41_inc','module cand_ot_v41_inc')
   self.assertEqual(converted,cand,name)
 def test_wake_true_source_reset_lookahead_bank_bindings(self):
  e=(ROOT/G.COPIES['rtl/v41rom/ot_v41_rom_elem_w10.sv']).read_text()
  for text in ('wake <= go || go_e || walk_busy || drain != 8\'d0;','wire iclk = WAKE_REG != 0 ? clk : gclk;','if (!rst_n) wake <= 1\'b1;','wg < 8','leaf_clk[4 + 2*mb]','leaf_clk[5 + 2*mb]','leaf_clk[3]'):
   self.assertIn(text,e)
  for leaf in range(8):self.assertIn(f'independent wake lookahead leaf{leaf}',BENCH);self.assertIn(f'low latch settling leaf{leaf}',BENCH)
  self.assertIn('#415;clk=0;#1;cycles=cycles+1;compare_all();',BENCH)
  self.assertIn('capture_wake_contract(); #416; clk=1; #1;',BENCH)
  self.assertIn('root_capture_events',BENCH)
 def test_wake_empty_go_expected_from_immutable_cfg_class_bits(self):
  image=G.N.inputs()
  for phase in range(12):
   active=any(int(image['cfg_words'][str(25*phase+c)],16)&1 for c in range(8,16))
   self.assertEqual(phase!=0,active)
  self.assertIn('wake_next_expected=!rst_n || (go && phase_is_active(ph)) ||',BENCH)
  self.assertIn('independent pair go qualification',BENCH)
  self.assertIn('independent registered element go',BENCH)
 def test_mutated_join_pin_is_rejected_without_file_edit(self):
  path=ROOT/G.COPIES['rtl/v41rom/ot_v41_rom_elem_w10.sv'];read=Path.read_bytes
  def mutant(p):return read(p).replace(b'wake <= go ||',b'wake <= 1\'b0 ||') if p==path else read(p)
  with patch.object(Path,'read_bytes',mutant):
   with self.assertRaisesRegex(ValueError,'new pin changed'):G.verify()
 def test_model_scope_and_open_physical_gate(self):
  self.assertFalse(any(MODEL['claims'].values()));self.assertEqual(8,MODEL['area']['added_register_bits'])
  self.assertEqual(0,MODEL['area']['added_arithmetic_stages']);self.assertIn('OPEN',MODEL['physical_obligations']['fullunit_drain'])
  self.assertEqual(32768,json.loads((ROOT/'results/rtl/dsrom_bmul_rne_primitive_prepare_20261002/model.json').read_text())['replication']['parent_field_BF_multiplier_sites'])
if __name__=='__main__':unittest.main()
