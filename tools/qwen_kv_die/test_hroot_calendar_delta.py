"""Executable HROOT calendar delta checks; absolute die qualification is separate."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
import kvjc3_pc_chain as C


def programme_functions():
    # Load the production image functions without unrelated link-image imports.
    tree = ast.parse(Path(__file__).with_name('kv_static_programme.py').read_text())
    tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and
                 n.name in ('es_cfg_words', 'hroot_landing')]
    ns = dict(ES_CFG_CTRL_LAT=92, ES_CFG_WORDS=(1024, 8))
    exec(compile(tree, 'kv_static_programme.py', 'exec'), ns)
    return ns


class HrootDelta(unittest.TestCase):
    def test_selected_implementation(self):
        f = programme_functions()['hroot_landing']
        k = SimpleNamespace(HROOT_LAND=True, HROOT_S32=False,
                            HROOT_ESH_MOD='qkd_kv_es_fan_stack_bl',
                            HROOT_RLY_MOD='qkd_kv_stack_relays_l')
        self.assertEqual(f(k), dict(chain=1, fan=1, gather=1, embedding=1))
        k.HROOT_S32 = True
        with self.assertRaises(ValueError):
            f(k)
        k.HROOT_S32 = False
        k.HROOT_ESH_MOD = 'missing_landing'
        with self.assertRaises(ValueError):
            f(k)

    def test_player_and_join_images_price_both_directions(self):
        old = C.emb_calendar(92, [0]*4)
        new = C.emb_calendar(92, [1]*4, return_relay=[1]*4)
        self.assertEqual(new['issue'], old['issue'] + 1)
        self.assertEqual(new['last_word'], old['last_word'] + 2)
        for key, pc in new['pcs'].items():
            base = old['pcs'][key]
            # Down +1 shifts issue/return/capture; return +1 is compensated
            # in per-PC transfer offsets while the join calendar waits +2.
            self.assertEqual(pc['chain_in'], base['chain_in'] + 1)
            self.assertEqual(pc['absolute']['TRN'], base['absolute']['TRN'] + 1)
            self.assertEqual(pc['offsets'], base['offsets'])
        f = programme_functions()['es_cfg_words']
        oldpc, oldbeat = f()
        pc, beat = f(relay=[1]*4, return_relay=[1]*4)
        self.assertEqual(pc, oldpc)
        self.assertNotEqual(beat, oldbeat)
        self.assertEqual((beat[0] & 65535), (oldbeat[0] & 65535) + 2)

    def test_causal_wrong_age_and_missing_return_landing(self):
        good = C.emb_calendar(92, [1]*4, return_relay=[1]*4)
        # Evaluate arrivals independently from the actual transfer schedule.
        for mut_down, mut_return in ((0, 1), (1, 0), (0, 0)):
            wrong = C.emb_calendar(92, [mut_down]*4, return_relay=[mut_return]*4)
            mismatches = 0
            for key, pc in wrong['pcs'].items():
                s, p = pc['stack'], pc['pc']
                arrival = (C.chain_in(s, p, [1]*4) + C.PLAYER + pc['offsets']['TRN']
                           + C.TRAIN_HOP*(C.N-p) + 1)
                want = next(b['u'] for b in [dict(u=good['first_root_beat'] + s*C.N+p)])
                mismatches += arrival != (wrong['first_root_beat'] + s*C.N+p)
                self.assertEqual(want, good['first_root_beat'] + s*C.N+p)
            self.assertEqual(mismatches, 128)


if __name__ == '__main__':
    unittest.main(verbosity=2)
