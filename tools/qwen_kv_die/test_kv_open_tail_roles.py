"""KV-FUNC-OPENS: open-tail role contract declares only generator chain ends / pinned duplicate faces."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as P  # noqa: E402
import kv_open_tail_roles as O  # noqa: E402

# the GEN7 source tree (pinned sources); tests skip when it is not on this host
GEN7 = Path(os.environ.get('OT_KV_GEN7_ROOT', '/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub'))


def die(tail_s=31, tail_n=0):
    L = ['module die(ck);', 'input wire ck;']
    for st in ('WS', 'WN', 'ES', 'EN'):
        idx = [30, 31] if st[1] == 'S' else [1, 0]
        L.append(f'wire [32:0] k_{st}_0, k_{st}_1, k_{st}_2;')
        for j, k in enumerate(idx):
            ko = '' if k == (tail_s if st[1] == 'S' else tail_n) else f'k_{st}_{j + 1}'
            L.append(f'qkd_kvs_pc kvpc_{st}_{k} (.pc__ki(k_{st}_{j}), .pc__ko({ko}));')
        L.append(f'sinkm sink_{st} (.i(k_{st}_2));')
    L += ['qkd_d2d_static d2d_kv (.att_rx_slot(), .kvn_word_slot(), .kvn_word_index());', 'endmodule']
    return '\n'.join(L) + '\n'


def copy_root(tmp):
    root = Path(tmp) / 'root'
    for rel in list(O.SOURCES) + [O.GENERATOR[0]]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(GEN7 / rel, root / rel)
    return root


@unittest.skipUnless((GEN7 / O.TILES).is_file(), 'GEN7 source tree not on this host')
class OpenTailRoles(unittest.TestCase):
    def test_positive_chain_tail_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_root(tmp)
            d = Path(tmp) / 'die.v'
            d.write_text(die())
            doc = O.derive(d, root)
            c = doc['open_tail_contract']
            self.assertEqual(sorted(c['ports']['qkd_kvs_pc.pc__ko']['instances']),
                             ['kvpc_EN_0', 'kvpc_ES_31', 'kvpc_WN_0', 'kvpc_WS_31'])
            self.assertEqual(P.pad_bits(doc['instances']['kvpc_WS_31']['ports']['pc__ko'], 33), set(range(33)))
            self.assertEqual(P.pad_bits(doc['instances']['d2d_kv']['ports']['kvn_word_index'], 2), {0, 1})
            self.assertNotIn('pc__ko', doc['instances'].get('kvpc_WS_30', {}).get('ports', {}))

    def test_wrong_chain_end_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_root(tmp)
            d = Path(tmp) / 'die.v'
            d.write_text(die(tail_s=30))          # S chains broken at pc30: pc31's ki is undriven, pc30 ko open
            doc = O.derive(d, root)
            self.assertIn('qkd_kvs_pc.pc__ko', doc['open_tail_contract']['refused'])
            self.assertFalse(any('pc__ko' in e['ports'] for e in doc['instances'].values()))

    def test_source_change_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_root(tmp)
            d = Path(tmp) / 'die.v'
            d.write_text(die())
            p = root / 'rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv'
            p.write_text(p.read_text().replace('o_d <= i_d;', 'o_d <= ~i_d;'))
            with self.assertRaisesRegex(ValueError, 'source changed'):
                O.derive(d, root)


if __name__ == '__main__':
    unittest.main()
