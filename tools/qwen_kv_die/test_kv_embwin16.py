"""KV-EMBWIN16 10-20: the grown token-run embedding window (d2d_link_calendar --emb-window, OT_KV_EMB_WIN).
  * default (no --emb-window) = the priced 272 window, the committed images reproduce byte for byte (checked by the
    production script elsewhere); 595 moves the header slot 191 -> 514 and L0..L35 / the token period by +323 (the
    768-edge period alignment rounds the period 249,600 -> 250,368);
  * the KV-CAL15 fill law (emb_fill) PASSES on the GEN9 i13a relays + HROOT_LAND + PIPE_JOIN at 595 and FAILS at 594;
  * the committed ew595 pair images equal the compiler output, and only the window-dependent lines differ from the base."""
import gzip
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / 'tools/qwen_split')]
import d2d_link_calendar as L  # noqa: E402
import kv_static_programme as P  # noqa: E402

DIE = dict(down=[82, 24, 71, 15], ret=[66, 20, 76, 31], svc_root=4, svc_join=3, slot=1, source='GEN9 i13a')
CD = dict(P.CAL_DELTAS_ZERO, hroot=dict(chain=1, fan=1, gather=1, embedding=1), emb_join=1)
D = ROOT / 'rtl/qwen_sys/d2d_static_20261015'


def layout(win):
    with tempfile.TemporaryDirectory() as t:
        tp = Path(t) / 'tp.json'
        tp.write_bytes(gzip.decompress((ROOT / P.LINK_TOKEN_PATH).read_bytes()))
        _, lay = L.program_profile(8, 7, str(tp), emb_window=win, host_stages=0, st_ofs=40)
    return lay


class Window(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.w595, cls.w594 = layout(None), layout(595), layout(594)

    def test_shift(self):
        b, w = self.base, self.w595
        self.assertEqual((b['embed']['cycles'], b['emb_header_send']), (272, 191))
        self.assertEqual((w['embed']['cycles'], w['embed']['grown_by'], w['emb_header_send']), (595, 323, 514))
        self.assertEqual([x['start'] - y['start'] for x, y in zip(w['layers'], b['layers'])], [323] * 36)
        self.assertEqual(w['token_period'] - b['token_period'], 323)            # unpadded; 768 alignment in main()
        self.assertEqual(w['windows'], b['windows'])                             # no op window shrinks or moves
        with self.assertRaises(ValueError):
            layout(271)

    def test_fill_passes_at_595_only(self):
        f = P.emb_fill(self.w595, CD, DIE)
        self.assertEqual((f['status'], f['margin'], f['header_slot'], f['last_word']), ('PASS', 0, 514, 514))
        self.assertEqual(P.emb_fill(self.w594, CD, DIE)['status'], 'FAIL')
        self.assertEqual(P.emb_fill(self.base, CD, DIE)['margin'], -323)

    def test_committed_images(self):
        for mu, name in ((0, 'd2d_cal_image'), (1, 'd2d_cal_image_mu')):
            with tempfile.TemporaryDirectory() as t:
                env = dict(__import__('os').environ, D2D_MU=str(mu), D2D_EMB_WINDOW='595')
                subprocess.run(['bash', 'tools/qwen_split/d2d_cal_image_production.sh', t], cwd=ROOT, env=env, check=True,
                               capture_output=True)
                self.assertEqual((Path(t) / 'd2d_cal_image.svh').read_text(), (D / f'{name}_ew595.svh').read_text(), name)
            a, b = (D / f'{name}.svh').read_text(), (D / f'{name}_ew595.svh').read_text()
            names = lambda s: {m.group(1): m.group(0) for m in re.finditer(r'^localparam[^\n]*?\b(\w+) = [^\n]*$', s, re.M)}
            na, nb = names(a), names(b)
            self.assertEqual({k for k in na if na[k] != nb[k]},
                             {'D2D_CAL_C_TX_IMG', 'D2D_CAL_C_RX_IMG', 'D2D_CAL_K_TX_IMG', 'D2D_CAL_K_RX_IMG', 'D2D_CAL_START',
                              'D2D_TOKEN_PERIOD'})
            self.assertIn('D2D_TOKEN_PERIOD = 250368;', b)
            self.assertIn("D2D_TXDP_K = 32'h03030416;", b)                   # TXDP_K 22 seam contract unchanged

    def test_bc4_ew_only_include(self):
        a = (D / 'qkd_d2d_cal_seq_bc4.sv').read_text().splitlines()
        b = (D / 'qkd_d2d_cal_seq_bc4_ew595.sv').read_text().splitlines()[1:]
        d = [(x, y) for x, y in zip(a, b) if x != y]
        self.assertEqual(len(a), len(b))
        self.assertEqual(d, [('    `include "d2d_cal_image_mu.svh"', '    `include "d2d_cal_image_mu_ew595.svh"')])


class Target11(unittest.TestCase):
    """the KV end's boot target 11 compiled under OT_KV_EMB_WIN=595 equals the ew595 image word for word (SU and MU),
    and the base window compile is refused against the ew595 image (a stale boot image fails closed)."""
    def _probe(self, mu, win, img=None):
        import os
        env = dict(os.environ, OT_KV_MU=str(mu), OT_KV_EMB_WIN=win)
        code = ('import json,sys,tempfile; sys.path.insert(0,"tools/qwen_kv_die"); import kv_static_programme as P; '
                'from pathlib import Path; ' + ('P.LINK_ARGS=P.LINK_ARGS[:P.LINK_ARGS.index("--emb-window")]; ' if img else '') +
                'td=tempfile.mkdtemp(); cal=P.link_calendar(td, attn_tx_shift=0); w=P.link_cfg_words(Path(td)/"cal"); '
                'out=dict(image=P.LINK_IMAGE)\ntry: out["check"]=P.link_image_check(w, cal)\nexcept ValueError as e: out["refused"]=str(e)\n'
                'print("PROBE "+json.dumps(out))')
        p = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        line = [x for x in p.stdout.splitlines() if x.startswith('PROBE ')]
        self.assertTrue(p.returncode == 0 and line, p.stderr[-2000:])
        return json.loads(line[-1][6:])

    def test_su_mu_equal(self):
        for mu, name in ((0, 'd2d_cal_image_ew595.svh'), (1, 'd2d_cal_image_mu_ew595.svh')):
            r = self._probe(mu, '595')
            self.assertTrue(r['image'].endswith(name), r)
            self.assertTrue(r.get('check', {}).get('equal') and r['check']['txdp_k_agree'], r)

    def test_stale_window_refused(self):
        r = self._probe(1, '595', img='base-window compile')
        self.assertIn('target 11 differs', r.get('refused', ''))


class WriterDie(unittest.TestCase):
    """writer lanes composed on the die relays: KVN relay depth to the writer + LAND chain on the shared es DOWN path"""
    @staticmethod
    def doc(kvn=(5, 5, 5, 5)):
        b = lambda a, ap, c, cp, n: dict(src=dict(inst=a, port=ap), dst=dict(inst=c, port=cp), stages=n)
        out = [b('d2d_kv', 'svc', 'kvs_ctl', 'd2d__svc', 4), b('d2d_kv', 'svc', 'kvs_emb', 'd2d__svc', 3),
               b('d2d_kv', 'emb_tx_slot', 'kvs_emb', 'd2d__emb_tx_slot', 1)]
        for st, dn, rt in zip(('WS', 'WN', 'ES', 'EN'), DIE['down'], DIE['ret']):
            out += [b('kvs_ctl', f'o_hroot_{st}', f'kvs_hroot_{st}', 'i_ctl', dn - 2), b(f'kvs_hroot_{st}', 'o_pc', f'kvpc_{st}_31', 'i_next', 2),
                    b(f'kvpc_{st}_31', 'o_next', f'kvs_hroot_{st}', 'i_r', 2), b(f'kvs_hroot_{st}', 'o_emb', 'kvs_emb', f'i_hroot_{st}', rt - 2)]
        out += [b('d2d_kv', p, 'kvs_ctl', 'd2d__' + p, n) for p, n in zip(('skw', 'srx', 'kvn_word_generation', 'kvn_word_identity'), kvn)]
        return dict(buses=out)

    def test_ages(self):
        w = P.writer_die(self.doc(), CD)
        self.assertEqual((w['kvn_relays'], w['land_chain']), (5, 1))
        self.assertEqual(w['per_stack']['WS'], dict(down=83, pc31_wes=87, pc0_ctrl_es=120))   # 2 + 83 + 0 hops + 2 / + 31 hops + 2 + 2
        w0 = P.writer_die(self.doc(), P.CAL_DELTAS_ZERO)
        self.assertEqual(w['worst_ctrl_es_age'] - w0['worst_ctrl_es_age'], 1)                    # LAND chain +1 on the writer lanes

    def test_unequal_kvn_refused(self):
        with self.assertRaises(ValueError):
            P.writer_die(self.doc(kvn=(5, 5, 4, 5)), CD)


if __name__ == '__main__':
    unittest.main()
