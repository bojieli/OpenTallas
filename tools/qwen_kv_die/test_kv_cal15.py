"""KV-CAL15 10-20: the admitted cycle deltas (kv_static_programme.cal_deltas / emb_fill / ownership leave lead)."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import kv_static_programme as P  # noqa: E402
import kvjc3_pc_chain as C3  # noqa: E402
import kvcal15_emb_die_model as M  # noqa: E402

LAYOUT = dict(hbm_embedding_budget=dict(result_at_kv_host=21, first_emb_send=192), emb_header_send=191,
              embed=dict(start=0, cycles=272), token_period=249600)
DIE = dict(down=[82, 24, 71, 15], ret=[66, 20, 76, 31], svc_root=4, svc_join=3, slot=1, source='i13a')


class Deltas(unittest.TestCase):
    def _cd(self, **env):
        with mock.patch.dict(os.environ, env, clear=False):
            ksd = mock.Mock(HROOT_LAND=env.get('OT_KV_HROOT_LAND') == '1', HROOT_S32=False,
                            HROOT_ESH_MOD='qkd_kv_es_fan_stack_bl', HROOT_RLY_MOD='qkd_kv_stack_relays_l')
            return P.cal_deltas(ksd)

    def test_registry(self):
        cd = self._cd(OT_KV_HROOT_LAND='1', OT_KV_EMB_PJ='1', OT_KV_CTL_C32='2', OT_KV_AHUB_PAD='1', OT_KV_SEAM_PIN='1')
        self.assertEqual(cd['hroot'], dict(chain=1, fan=1, gather=1, embedding=1))
        self.assertEqual((cd['emb_join'], cd['ctl_own_leave'], cd['ctl_boot_setup_ready']), (1, 2, 2))
        self.assertEqual((cd['ahub']['compiler_edges'], cd['seam']['compiler_edges']), (0, 0))
        cd0 = self._cd(OT_KV_HROOT_LAND='0', OT_KV_EMB_PJ='0', OT_KV_CTL_C32='0')
        self.assertEqual((cd0['hroot']['chain'], cd0['emb_join'], cd0['ctl_own_leave']), (0, 0, 0))
        with self.assertRaises(ValueError):
            self._cd(OT_KV_CTL_C32='3')


class Fill(unittest.TestCase):
    def test_zero_relay_model_already_misses_the_header(self):
        f = P.emb_fill(LAYOUT, P.CAL_DELTAS_ZERO)
        self.assertEqual((f['last_word'], f['row_tx_slot'], f['margin']), (21 + 327, 191, 191 - 349))
        self.assertEqual(f['status'], 'FAIL')

    def test_die_land_pj(self):
        cd = dict(P.CAL_DELTAS_ZERO, hroot=dict(chain=1, fan=1, gather=1, embedding=1), emb_join=1)
        f = P.emb_fill(LAYOUT, cd, DIE)
        self.assertEqual(f['down'], [83, 25, 72, 16])
        self.assertEqual(f['ret'], [68, 22, 78, 33])            # + LAND return + root/join skew 1
        base = P.emb_fill(LAYOUT, P.CAL_DELTAS_ZERO, DIE)
        self.assertEqual(f['last_word'] - base['last_word'], 3)  # LAND +2 (down + return), PIPE_JOIN +1
        self.assertEqual(f['embed_window_needed'] - LAYOUT['embed']['cycles'], -f['margin'])

    def test_model_matches_compiler_law(self):
        cal, words, exp = M.build([83, 25, 72, 16], [67, 21, 77, 32], 1, 1)
        ref = C3.emb_calendar(92, [83, 25, 72, 16], return_relay=[68, 22, 78, 33])
        self.assertEqual(words, C3.boot_words(ref))
        self.assertEqual(exp[-1]['edge'], ref['last_word'] + 1)
        for m in (1, 2, 3, 4):                                    # every mutant changes the bus image or the expectation
            _, w, e = M.build([83, 25, 72, 16], [67, 21, 77, 32], 1, 1, mut=m)
            self.assertTrue(w != words or e != exp, m)


class Ownership(unittest.TestCase):
    def test_mu_lead_order(self):
        own = [3, 100, 200, P.OWN_SEAL]
        with mock.patch('tools.qwen_static_schedule.mu_calendar.kv_rows_from_image', return_value=[]), \
             mock.patch('tools.qwen_static_schedule.mu_calendar.kv_frame_of_record', return_value=(None, [], [], [], [])), \
             mock.patch('tools.qwen_static_schedule.mu_calendar.kv_ownership_roots_mu',
                        return_value=([3, 150, 250, P.OWN_SEAL], dict(leave_per_user=[100], deadline_per_user=[200]))), \
             mock.patch('tools.qwen_static_schedule.mu_calendar.kv_layer_image_mu', return_value=[]):
            out = P.mu_images([], [3, 102, 200, P.OWN_SEAL], lead=2)
            self.assertEqual(out['ownership'][:3], [3, 152, 250])
            with self.assertRaises(ValueError):
                P.mu_images([], own, lead=2)                      # single-user roots must carry the lead


if __name__ == '__main__':
    unittest.main(verbosity=2)
