"""Bounded metadata/refusal checks; no numerical prefix or HDL build."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import qwen_rom_runtime_pc_context as C


class RuntimeContext(unittest.TestCase):
    def test_selected_source_and_clock(self):
        x = C.compose()
        self.assertEqual(x['controller']['PCs'], 128)
        self.assertEqual(x['clock']['observed_source_interval_fs'], [833333, 1666666])
        self.assertEqual(x['clock']['minimum_controller_setup_interval_ps'], 833.333)
        self.assertFalse(x['physical_build_admitted'])
        self.assertFalse(x['runtime_changed'])

    def test_old_pc_cannot_be_selected(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(C.BASE / 'inputs', Path(d) / 'inputs')
            p = Path(d) / 'inputs' / 'ot_hbm_r14_stream_pc.sv'
            p.write_bytes((C.ROOT / 'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv').read_bytes())
            with self.assertRaisesRegex(ValueError, 'no controller substitution'):
                C.compose(p.parent)

    def test_wrong_rank_count_refused(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(C.BASE / 'inputs', Path(d) / 'inputs')
            p = Path(d) / 'inputs' / 'source_program_counts.json'
            x = json.loads(p.read_text())
            x['stages'][0]['ranks'][1]['source_reachable_ME_pcs'] = []
            p.write_text(json.dumps(x))
            with self.assertRaisesRegex(ValueError, 'rank instruction mismatch'):
                C.compose(p.parent)

    def test_service_price_is_not_token_measurement(self):
        p = C.compose()['slab_price']
        self.assertEqual(p['source_reachable_ME_commands_per_rank'], 220)
        self.assertEqual(p['source_HEAD_ME_PCs'], [3, 4, 5, 6])
        self.assertEqual(p['gross_service_extra_cycles_LAT6'], 220)
        self.assertEqual(p['gross_service_extra_cycles_LAT7_historical'], 440)
        self.assertIsNone(p['whole_token_critical_path_extra_cycles'])
        self.assertFalse(p['candidate_enrolled'])

    def test_retained_macro_pin_units_and_once_only_cost(self):
        p = C.macro_binding()
        self.assertEqual(p['macro_count'], 624)
        self.assertAlmostEqual(p['total_macro_clock_pin_cap_fF'], 6472.8768)
        self.assertAlmostEqual(p['scale_port_address_per_bit_cap_fF'], 8.8881)
        self.assertEqual(p['corners']['ss']['output_per_bit_max_load_fF'], 46.08)
        self.assertFalse(p['aligned_successor']['selected'])
        self.assertGreater(p['aligned_successor']['extra_area_um2_for_624'], 0)
        self.assertFalse(p['contextual_SS_FF_qualified'])

    def test_context_reuses_literal_stack_and_clock_blocks(self):
        parent = (C.BASE / 'inputs/ot_qwen_hbm_stream4_tagged.sv').read_text()
        cut = (C.BASE / 'ot_qwen_stream4_runtime_controller_context.sv').read_text()
        start = parent.index('    for (genvar sk = 0; sk < NSTK;')
        end = parent.index('    // ----', start)
        self.assertIn(parent[start:end], cut)
        start = parent.index('    reg [31:0] acc = 0;')
        end = parent.index('    // ---- the streaming controller', start)
        self.assertIn(parent[start:end].replace('wire hclk =', 'assign hclk ='), cut)
        self.assertIn('NSTK=4, NPC=128', cut)
        self.assertEqual(cut.count('ot_hbm_r14_stream_stack #('), 1)

    def test_frozen_record_cold_equal(self):
        frozen = json.loads((C.BASE / 'model_with_retained_macro_binding_r2.json').read_text())
        self.assertEqual(C.compose(), frozen)


if __name__ == '__main__':
    unittest.main()
