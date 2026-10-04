import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('hook',ROOT/'tools/w17_current_fastpp_owner_safe_die_rt.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class RuntimeHookTests(unittest.TestCase):
    def test_four_runtime_copies_exact_archived_sources(self):
        names=['ot_chip_v41x_window_kv_prefetch_owner_safe','ot_chip_v41x_window_attn_source_owner_safe','ot_chip_v41x_die_owner_safe','ot_v41_rt_die_l20_owner_safe']
        for name in names:
            with self.subTest(name=name):self.assertEqual((ROOT/'rtl/chip/window_owner_safe'/f'{name}.sv').read_bytes(),(ROOT/'results/rtl/dsrom_window_owner_tag_gate_20261003/owner_safe'/f'{name}.sv').read_bytes())
    def test_full125_list_exact_four_substitutions(self):
        orig=(ROOT/'tools/w17_current_fastpp_l20_sources.txt').read_text().split();new=[str(p.relative_to(ROOT)) for p in m.l20_sources()]
        self.assertEqual(len(orig),125);self.assertEqual(len(new),125);self.assertEqual(len(set(new)),125)
        changes=[(a,b) for a,b in zip(orig,new) if a!=b];self.assertEqual(len(changes),4)
        self.assertTrue(all(b.startswith('rtl/chip/window_owner_safe/') for a,b in changes))
        for p in m.l20_sources():self.assertTrue(p.is_file(),str(p))
    def test_actual_four_die_commands_no_frontend_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured=[];saved=m.run
            try:
                m.run=lambda cmd,log,cwd=None:captured.append([str(x) for x in cmd]) or dict(dry=True)
                m.build(SimpleNamespace(work=Path(tmp),l20=True,only='die0,die1,die2,die3',jobs=1,fast=1,pp=1))
            finally:m.run=saved
            self.assertEqual(len(captured),8)
            for r,cmd in enumerate(captured[::2]):
                self.assertEqual(cmd[cmd.index('--top-module')+1],'ot_v41_rt_die_l20_owner_safe')
                self.assertEqual(cmd[cmd.index('--prefix')+1],f'Vdie{r}')
                for flag in [f'-GRANK={r}','-GWINDOW_REFILL_CREDITS=8','-GWINDOW_REFILL_OWNER_SAFE=1','-DV41_ATT_CUT','-GROM_PHW=6','-GX_IDX=2','-GSUN=256','-GSUM=64']:self.assertIn(flag,cmd)
                self.assertTrue(all(str(p) in cmd for p in m.l20_sources()))
            self.assertFalse(any(Path(tmp).rglob('*.a')))
    def test_old_die_archive_refused_no_silent_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'die0';path.mkdir();(path/'Vdie0__ALL.a').write_bytes(b'old')
            with self.assertRaisesRegex(ValueError,'existing die archive'):m.build(SimpleNamespace(work=Path(tmp),l20=True,only='die0'))
    def test_matching_safe_archive_reused_without_duplicate_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls=[];saved=m.run
            args=SimpleNamespace(work=Path(tmp),l20=True,only='die0',jobs=1,fast=1,pp=1)
            try:
                m.run=lambda cmd,log,cwd=None:calls.append(cmd) or dict(dry=True)
                m.build(args);self.assertEqual(len(calls),2)
                d=Path(tmp)/'die0';d.mkdir();(d/'Vdie0__ALL.a').write_bytes(b'completed source-bound archive')
                calls.clear();m.build(args);self.assertEqual(calls,[])
            finally:m.run=saved
    def test_full_chain_and_default_off(self):
        d=ROOT/'rtl/chip/window_owner_safe'
        self.assertIn('parameter bit REFILL_OWNER_SAFE = 0',(d/'ot_chip_v41x_window_kv_prefetch_owner_safe.sv').read_text())
        self.assertIn('.REFILL_OWNER_SAFE(REFILL_OWNER_SAFE)',(d/'ot_chip_v41x_window_attn_source_owner_safe.sv').read_text())
        self.assertIn('.REFILL_OWNER_SAFE(WINDOW_REFILL_OWNER_SAFE)',(d/'ot_chip_v41x_die_owner_safe.sv').read_text())
        self.assertIn('.WINDOW_REFILL_OWNER_SAFE(WINDOW_REFILL_OWNER_SAFE)',(d/'ot_v41_rt_die_l20_owner_safe.sv').read_text())
    def test_CXX_prefix_and_dynamic_DPI_scope_unchanged(self):
        cpp=(ROOT/'rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp').read_text()
        for r in range(4):self.assertIn(f'#include "Vdie{r}.h"',cpp)
        self.assertIn('svGetScope()',cpp);self.assertNotIn('svGetScopeFromName',cpp)
    def test_owners_and_no_runtime_credit(self):
        rec=json.loads((ROOT/'results/rtl/window_owner_safe_runtime_hook_20261003/binding.json').read_text())
        self.assertEqual(rec['full_parent_owner'],'Archimedes');self.assertEqual(rec['systemstream_owner'],'Claude')
        self.assertTrue(rec['no_new_gate_simulation']);self.assertFalse(rec['full_parent_runtime']);self.assertFalse(rec['physical_credit'])
if __name__=='__main__':unittest.main(verbosity=2)
