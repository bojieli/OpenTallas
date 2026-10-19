"""Golden checks of the KV static programme compiler against the existing bench-fed programmes and calendars."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_static_programme as C
import kv_static_ages as A_  # noqa: E402

ROOT = C.ROOT


class Programme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.comp = C.compile_all(C.profile('component'))
        cls.die = C.compile_all(C.profile('die', json.loads((ROOT / C.AGES).read_text())))

    def test_component_layer_image_is_the_committed_image(self):
        svh = (ROOT / 'rtl/qwen_sys/static_kv_20261014/layer_programme_image.svh').read_text()
        roots = int(re.search(r"LP_ROOTS = \d+'h([0-9a-f]+);", svh).group(1), 16)
        words = self.comp['layer']['words']
        self.assertEqual(roots, sum(w << (32 * i) for i, w in enumerate(words[:324])))
        self.assertEqual(int(re.search(r"LP_DIGEST = 64'h([0-9a-f]+);", svh).group(1), 16), words[324])
        self.assertEqual(int(re.search(r"LP_EPOCH = 16'd(\d+);", svh).group(1)), words[325])

    def test_attention_calendar_matches_the_native_endpoint_compiler(self):
        pr = C.profile('component')
        for T in (1, 2, 77, 128, 129, 1000, 2048, 4097, 6144, 8191, 8192):
            c = C.attention_calendar(T, pr)
            self.assertEqual(c, C.AC.calendar(T, pv='w16', head_g3s2=True))
            ep = C.CNE.compile_programme(1, 2, T - 1, 0, 2)
            self.assertEqual(C.AC.hexcal(c), ep['calendar_hex'])

    def test_attention_words_follow_the_link_slot(self):
        for r in (self.comp, self.die):
            a = r['attention']
            self.assertEqual(a['compiled_end'], a['compiled_tx_first'] + 34)
            self.assertGreater(a['compiled_tx_first'], a['compiled_rx_cmd'] + 34)
            for T, s in a['samples'].items():
                self.assertEqual(C.AC.service_cycles(s['fields']), a['service_end'], T)
            # the minimal endpoint service of the longest context fits inside the link's RESULT slot
            ep = C.CNE.compile_programme(1, 2, 8191, 0, a['compiled_rx_cmd'])
            if r is self.comp:
                self.assertLessEqual(ep['compiled_tx_first'], a['compiled_tx_first'])

    def test_calendar_pacing_is_the_kv_calendar_prefix(self):
        from tools.qwen_static_kv import landing_cal_golden as G
        from tools.qwen_static_schedule import kv_calendar as K
        ks, vs = K.k_streams(8192, G.P), K.pv16_v_streams(8192)
        for name, g in self.comp['groups'].items():
            pc = g['pcs'][0]
            kp = K.pc_schedule(ks[pc], G.P, 0)['put']
            vp = K.pc_schedule_paced(vs[pc], G.P, K._layer_pc_paced(vs[pc], G.P)[0])['put']
            self.assertEqual((g['K']['P0'], g['K']['GAP']), G.pacing([x - kp[0] for x in kp]))
            self.assertEqual((g['V']['P0'], g['V']['GAP']), G.pacing([x - vp[0] for x in vp]))
        self.assertEqual({(g['V']['P0'], g['V']['GAP']) for g in self.comp['groups'].values()}, {(160, 5)})
        # die: the JEDEC-bench RD bursts (K 8 / 2, V 8 / 3) set the put law; law_check proved it at every checked T
        self.assertEqual({(g['K']['P0'], g['K']['GAP'], g['V']['P0'], g['V']['GAP']) for g in self.die['groups'].values()},
                         {(8, 2, 8, 3)})
        self.assertFalse(C.law_check(C.profile('die', json.loads((ROOT / C.AGES).read_text())), C.pc_plans(self.die['profile'])[0],
                                     Ts=[1, 77, 1000, 4097, 8192])[2])

    def test_boot_bundle_matches_the_dispatcher(self):
        rtl = (ROOT / 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_dispatch.sv').read_text()
        body = re.search(r'case\(t\)(.*?)endcase', rtl, re.S).group(1)
        want = {}
        for keys, n in re.findall(r'([\d,]+):word_count=(\d+);', body):
            for k in keys.split(','):
                want[int(k)] = int(n)
        # KVJ-G2b: the DIECFG / LINKCFG / ESCFG targets (conditional word counts in the dispatcher)
        want.update({10: 32 + 43 + 2, 11: 66, 12: 1024, 13: 8})
        import program_target_frames as PTF
        self.assertEqual({t: PTF.TARGET_WORDS[t] for t in range(10, 14)}, {t: want[t] for t in range(10, 14)})
        for r in (self.comp, self.die):
            b = r['bundle']
            self.assertEqual(b['target_order'], list(range(1, 10)) + [11, 12, 13, 0])
            for im in b['images'][:-1]:
                self.assertEqual(im['program_words'], want[im['target']])
            self.assertEqual(int(b['images'][-1]['digest'], 16), r['layer']['digest'])

    def test_link_cfg_target_is_the_kv_sequencer_init_image(self):
        # KVJ-SMALL 10-17: target 11 (dispatcher LINKCFG=1) = the qkd_d2d_cal_seq init stream from d2d_cal_image.svh
        import re
        svh = (ROOT / 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh').read_text()
        val = lambda n: int(re.search(rf"{n} = \d+'h([0-9a-f]+);", svh).group(1), 16)
        tx, rx = val('D2D_CAL_K_TX_IMG'), val('D2D_CAL_K_RX_IMG')
        want = [w for i in range(32) for w in ((tx >> 32 * i) & 0xffffffff, (rx >> 32 * i) & 0xffffffff)]
        want += [val('D2D_CAL_K_TX_SEG2'), val('D2D_CAL_K_RX_SEG2')]
        for r in (self.comp, self.die):
            self.assertEqual(r['link_cfg']['target'], 11)
            self.assertEqual(r['link_cfg']['program'], want)

    def test_es_cfg_targets_are_the_kvjc3_boot_words(self):
        # KVJ-SMALL b2 10-17: targets 12 / 13 (dispatcher ESCFG=1) replay kvjc3_pc_chain.boot_words on the shared bus
        import kvjc3_pc_chain as C3
        bw = C3.boot_words(C3.emb_calendar(C.ES_CFG_CTRL_LAT, [0, 0, 0, 0]))
        for r in (self.comp, self.die):
            e = r['es_cfg']
            self.assertEqual(e['targets'], [12, 13])
            self.assertEqual((len(e['pc']), len(e['beat'])), (1024, 8))
            got = [(a & 0xff, d) for a, d in enumerate(e['pc'])] + [(a, d) for a, d in enumerate(e['beat'])]
            want = sorted(w for w in bw if w[1] >> 62 == 0) == sorted(got[:1024])
            self.assertTrue(want)
            self.assertEqual(got[1024:1024 + 2], [w for w in bw if w[1] >> 62 == 1])
            self.assertTrue(all(d == 1 << 62 for d in e['beat'][2:]))     # unused segments: len 0 = never a slot

    def test_writer_and_ownership_follow_their_boot_checks(self):
        for r in (self.comp, self.die):
            w = r['writer']['words']
            self.assertEqual(len(w), 181)
            self.assertEqual(w[-1], C.FOOTER_WRITER)
            for s in range(36):
                t0, t1, t2, t3, stop = w[5 * s:5 * s + 5]
                self.assertTrue(t0 >= 4 and t0 < t1 < t2 < t3 and stop > t3 and stop - t3 >= 3)
            o = r['ownership']['words']
            self.assertTrue(3 <= o[0] < o[1] < o[2] and o[3] == C.OWN_SEAL)

    def test_controller_images_hold_the_kv_calendar_reads(self):
        for r in (self.comp, self.die):
            for pc, c in r['controller'].items():
                self.assertLessEqual(c['runs'], 16)
                self.assertEqual(len(c['words']), 32)
            self.assertEqual({len(v) for v in r['controller_targets'].values()}, {1024})

    def test_die_roots_carry_the_die_ages(self):
        a, b = self.comp['layer']['rows'][1]['roots'], self.die['layer']['rows'][1]['roots']
        self.assertEqual(b['attention_run'], a['attention_run'] - 3 - 3)      # programme start relays 3 + lprg -> attention 3
        self.assertLess(b['kgo'], a['kgo'])
        self.assertEqual(b['ctrl_go'], b['kgo'])

    def test_token_period_is_padded_and_every_launch_is_legal(self):
        ph = self.die['phase']
        self.assertEqual(ph['token_period_core'] % 768, 0)
        # ROOT-QLINE 10-18: production calendar (die stages + LAYERBENCH compiled token path) = unpadded 249,389 -> 249,600;
        # QLB-C4 10-18: SC_TX 2 (dv2f14bq) -> attn_kv X 5 -> 7 on L1..L35 + L0 -215 (was -217): +72 -> 249,461 -> 249,600
        self.assertEqual(ph['token_period_core'], 249600)
        self.assertEqual(self.die['link']['token_period_unpadded'], 249461)
        self.assertEqual(ph['token_period_core'] - self.die['link']['token_period_unpadded'], 139)
        self.assertEqual((ph['token_phases'], ph['launches'], ph['outside_window'], ph['hold_conflicts']), (1, 108, [], []))
        # the unpadded period visits all 768 phases: no compiled launch holds at every one of them
        self.assertEqual(ph['unpadded_counterfactual']['token_phases'], 768)
        self.assertEqual(len(ph['unpadded_counterfactual']['outside_window']), 108)
        al = ph['alignment']
        self.assertLessEqual(al['v_early_used'], al['v_ring_room_core'])
        rows = self.die['layer']['rows']
        for r in rows:
            self.assertEqual(r['roots']['ctrl_go'], r['roots']['kgo'])
        self.assertEqual(self.die['leads']['vgo_minus_kgo'], rows[1]['roots']['vgo'] - rows[1]['roots']['kgo'] + al['stage_advance'][1] - al['stage_advance'][1])

    def test_ectla_qk_issue_age_and_attention_control(self):
        pt = C.priced_template(self.die['profile'])
        self.assertEqual((pt['ectla'], pt['QK_ISSUE_AGE'], pt['unpriced_left']), (32, A_.K_RT_BUDGET + 11, []))
        ctl = self.die['attention']['control']
        self.assertGreaterEqual(ctl['cal_gen']['first_issue_token_cycle'] - ctl['cal_gen']['go_token_cycle'], C.CAL_GEN_LAT)
        self.assertGreater(ctl['service_root']['pv_start_min'], 0)

    def test_operations_bind_actual_ports(self):
        ops = C.operations(self.die)
        self.assertEqual(C.check_ports(ops), len(ops))
        self.assertEqual(len({o['id'] for o in ops}), len(ops))


if __name__ == '__main__':
    unittest.main()
