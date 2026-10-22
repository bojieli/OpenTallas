"""KV-PROG17 10-20: production KV programme compile at ATTN_R16=1 (r16 pair image, die retirement contract, r16 MU frame)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/qwen_kv_die')]
D = ROOT / 'rtl/qwen_sys/d2d_static_20261015'
E = ROOT / 'results/arch/kv_prog17_1020'


class Prog17(unittest.TestCase):
    def test_r16_image_reproduces_and_keeps_seam(self):
        import re
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, D2D_MU='1', D2D_EMB_WINDOW='595', D2D_ATTN_TX_SHIFT='1', D2D_STATUS_DELAY='213')
            subprocess.run(['bash', 'tools/qwen_split/d2d_cal_image_production.sh', td], cwd=ROOT, env=env, check=True,
                           capture_output=True)
            self.assertEqual((Path(td) / 'd2d_cal_image.svh').read_text(), (D / 'd2d_cal_image_mu_ew595_r16.svh').read_text())
        a, b = (D / 'd2d_cal_image_mu_ew595.svh').read_text(), (D / 'd2d_cal_image_mu_ew595_r16.svh').read_text()
        ln = lambda t, n: re.search(rf'^localparam[^\n]*\b{n} = [^\n]*$', t, re.M).group(0)
        for n in ('D2D_TXDP_C', 'D2D_TXDP_K', 'D2D_CAL_K_TX_SEG2', 'D2D_CAL_K_RX_SEG2', 'D2D_ADM_OFS', 'D2D_FIRST_TOKEN'):
            self.assertEqual(ln(a, n), ln(b, n), n)
        self.assertIn('D2D_TOKEN_PERIOD = 258048', b)       # 250,368 + 36 x (213 + 1), padded to 768
        self.assertNotEqual(ln(a, 'D2D_CAL_K_TX_IMG'), ln(b, 'D2D_CAL_K_TX_IMG'))

    def test_dcal_r16_tile_is_include_only(self):
        for tag, img in (('595_r16', 'd2d_cal_image_mu_ew595_r16.svh'), ('r16', 'd2d_cal_image_mu_r16.svh')):
            sfx = tag if tag == 'r16' else 'ew' + tag
            t = (D / f'qkd_d2d_cal_seq_bc4_{sfx}.sv').read_text().split('\n', 1)[1]
            self.assertEqual(t, (D / 'qkd_d2d_cal_seq_bc4.sv').read_text().replace('`include "d2d_cal_image_mu.svh"',
                                                                                    f'`include "{img}"'))
        p = subprocess.run([sys.executable, 'tools/qwen_static_kv/gen_dcal_bc4_ew.py', '595_r17'], cwd=ROOT, capture_output=True)
        self.assertNotEqual(p.returncode, 0)

    def test_contract_refuses_source_without_reset_depth(self):
        import kv_retirement_contract as RC
        from kv_retirement import prove
        prog = dict(compiled_rx_cmd=2, compiled_tx_first=1753, compiled_end=2000, service_end=1779, token_period=258048)
        rst = str(ROOT / 'results/arch/kv_fault_reset_1019/gen7_evidence.tar.gz') + ':gen7/reset_branch_candidate.json'
        succ = E / 'd22hl2_health_successor.json'
        with self.assertRaises(ValueError):
            RC.build(succ, rst, prog, 11)                     # 77 GEN9 die sources the GEN7 candidate does not list
        c = RC.build(succ, rst, prog, 11, default_depth=87)
        r = prove(c, 1753, 1999)                               # r16 STATUS age = tx_first + 33 + 213
        self.assertEqual(r['status'], 'LOGICAL_ONLY')
        self.assertEqual(min(x['margin'] for x in r['sources']), 19)
        with self.assertRaises(ValueError):
            prove(c, 1753, 1999 - 20)                          # a STATUS before the worst source's observation
        self.assertEqual(c['reset']['required_sink_release_depth'], 325)   # > HOLD 273: K.STA.RST finding

    def test_r16_frame_f3_one_filler_token(self):
        from tools.qwen_static_schedule import mu_calendar as MC
        rows = json.loads((E / 'rows_r16_ew595.json').read_text())
        keep = MC.KV_ATT_END, dict(MC.KV_PHASE)
        try:
            MC.KV_ATT_END, MC.KV_PHASE['groups'] = 1998, 68
            fs, cal = MC.kv_frame_search(rows, 3, tries=1, filler_tokens=1)
            self.assertEqual(cal['tokens_per_frame'], {0: 3, 1: 1, 2: 1, 3: 1})
            self.assertAlmostEqual(cal['aggregate_tok_s'], 9300.6, places=0)
            MC.kv_frame_of_record(rows, 3, tuple(fs), filler_tokens=1)
            with self.assertRaises(MC.ScheduleError):          # F 2 (the 11,982 tok/s frame): the r16 window does not fit
                MC.kv_frame_search(rows, 2, tries=3)
        finally:
            MC.KV_ATT_END = keep[0]
            MC.KV_PHASE.clear()
            MC.KV_PHASE.update(keep[1])


if __name__ == '__main__':
    unittest.main()
