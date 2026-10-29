"""TOK-KV-DCAL-1 10-29: every KV dcal fork follows its source (COORD ruling TOK-KV-3-PARK (2)).

The bc4 include forks are generated from qkd_d2d_cal_seq_bc4.sv by gen_dcal_bc4_ew.py, never hand-edited, and no dcal tile
clears the boot base-word record (btx/brx_seen) on a reload: the KV die's reload (HOST program_begin, ISA target 0) always
comes after boot target 11, so such a clear fires EARLY at the first cal_start (TOK-KV-2 die fault @38394).
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'rtl/qwen_sys/d2d_static_20261015'
sys.path.insert(0, str(ROOT / 'tools/qwen_static_kv'))


class DcalForks(unittest.TestCase):
    def test_every_bc4_fork_is_the_generated_include_copy(self):
        import gen_dcal_bc4_ew as G
        tags = G.all_tags()
        self.assertTrue({'r16', '595', '595_r16', '1627_r16_rope'} <= set(tags), tags)
        bc4 = (D / 'qkd_d2d_cal_seq_bc4.sv').read_text()
        for t in tags:
            sfx = G.sfx_of(t)
            f = (D / f'qkd_d2d_cal_seq_bc4_{sfx}.sv').read_text()
            head, body = f.split('\n', 1)
            self.assertIn(f'gen_dcal_bc4_ew.py {t});', head, sfx)
            self.assertEqual(body, bc4.replace(G.INC, f'`include "d2d_cal_image_mu_{sfx}.svh"'), sfx)

    def test_new_fork_still_needs_the_seam_contract(self):
        p = subprocess.run([sys.executable, 'tools/qwen_static_kv/gen_dcal_bc4_ew.py', '1627_r16_rope'], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('D2D_CAL_K_TX_SEG2', p.stderr)

    def test_no_dcal_tile_clears_the_boot_record_on_reload(self):
        files = sorted(D.glob('qkd_d2d_cal_seq_*.sv'))
        seen = [f for f in files if 'btx_seen' in f.read_text()]
        self.assertGreaterEqual(len(seen), 8, [f.name for f in seen])
        clear = re.compile(r'if \((reload_q|rld)\) begin btx_seen\w* (<)?= 1\'b0')
        self.assertEqual([f.name for f in seen if clear.search(f.read_text())], [])


if __name__ == '__main__':
    unittest.main()
