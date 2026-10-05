"""Prelaunch checks of the additive source delta and retained visibility fences."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_rt_core_emit_w12 as retained
import qwen_rom_rt_core_emit_posted_w12 as posted


class PostedSourceTests(unittest.TestCase):
    def test_only_ordinary_issue_changes_and_default_is_off(self):
        baseline = retained.emit(retained.CORE.read_text())
        candidate = posted.emit(posted.CORE.read_text())
        candidate = candidate.removeprefix('// POSTED_KV successor: barriers/END keep real write-done fence.\n')
        candidate = candidate.replace('\n    parameter integer POSTED_KV = 0,', '', 1)
        candidate = candidate.replace('(POSTED_KV || kv_write_drained)', 'kv_write_drained', 1)
        self.assertEqual(candidate, baseline)
        # END and barriers use this actual fence, independent of POSTED_KV.
        self.assertIn('wire drained = me_idle && su_idle && (!KV_VEC_WRITE_BRIDGE || kv_write_drained);', candidate)
        self.assertIn('assign kv_write_flush = su_idle && !(|kv_we);', candidate)

    def test_top_adds_only_parameter_binding_and_counter_qualification(self):
        r = ROOT / 'rtl/test/qwen_rom_runtime'
        baseline = (r / 'ot_qwen_rom_rt_die_w12_rm.sv').read_text()
        candidate = (r / 'ot_qwen_rom_rt_die_w12_posted.sv').read_text()
        candidate = candidate.removeprefix('// Additive POSTED_KV successor; compile separately from retained REAL_MEM top.\n')
        candidate = candidate.replace('\n    parameter integer POSTED_KV = 0,        // default-off; retain barriers/END write-done fence', '', 1)
        candidate = candidate.replace('.POSTED_KV(POSTED_KV),', '', 1)
        candidate = candidate.replace('core.su_idle && !POSTED_KV && !kv_write_drained', 'core.su_idle && !kv_write_drained', 1)
        self.assertEqual(candidate, baseline)


    def test_host_change_only_asserts_real_end_visibility(self):
        r = ROOT / 'rtl/test/qwen_rom_runtime'
        baseline = (r / 'qwen_rom_rt_w12_rm.cpp').read_text()
        candidate = (r / 'qwen_rom_rt_w12_posted.cpp').read_text()
        candidate = candidate.removeprefix('// Posted-write successor: assert real write-done at each stage END.\n')
        begin = candidate.index('                // A posted write may overlap ordinary operations, never terminal')
        end = candidate.index('                stage_done = true;', begin)
        candidate = candidate[:begin] + candidate[end:]
        self.assertEqual(candidate, baseline)


if __name__ == '__main__':
    unittest.main()
