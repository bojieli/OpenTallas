#!/usr/bin/env python3
"""kv_misc_unused_roles on the actual GEN7 strict die (fleet only; skipped where the run is absent).
positive: exact class counts; negatives: duplicated ER owner strap, K-tree reading lane 1 valid, drifted pinned source."""
import json, os, shutil, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_misc_unused_roles as M

G = Path(os.environ.get('KV_GEN7_STRICT', '/srv/opentallas-scratch/claude/kv-exact-padgap-1019/gen7_strict'))
R = Path(os.environ.get('KV_GEN7_ROOT', '/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub'))
EXPECT = {'KPV_LOCKSTEP': 1920, 'ECTL_ER_ADDR': 384, 'ER_TAIL_NEXT': 192, 'ER_TAIL_RESP': 192, 'ASTK_LT': 84,
          'EP_ZO_TOK': 4, 'SEQ_HS': 1, 'BRANCH_DUP': 1186}


@unittest.skipUnless((G / 'die_bound.v').is_file() and R.is_dir(), 'GEN7 strict run not on this host')
class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.pads = json.loads((G / 'output_pads.pv.json').read_text())

    def mutated(self, old, new, count=1):
        t = (G / 'die_bound.v').read_text()
        self.assertEqual(t.count(old), count, old)
        d = self.tmp / f'die_{abs(hash(old))}.v'
        d.write_text(t.replace(old, new))
        rec = json.loads((G / 'port_bind_v2.json').read_text()); rec['die_sha256'] = M.sha(d)
        r = self.tmp / f'rec_{abs(hash(old))}.json'; r.write_text(json.dumps(rec))
        return d, r

    def test_positive_exact_classes(self):
        doc = M.derive(G / 'die_bound.v', G / 'port_bind_v2.json', R, self.pads)
        self.assertEqual(doc['misc_unused_contract']['classes'], EXPECT)
        self.assertEqual(doc['misc_unused_contract']['bits'], 3963)

    def test_negative_duplicate_owner_strap(self):
        # owner 7 of the WS chain strapped as 6: responses no longer provably served by exactly one owner
        old = "astk_WS__u_strip_g_er_chain_u_er_g_owner_7__u_owner ("
        t = (G / 'die_bound.v').read_text(); i = t.index(old); j = t.index('.owner_id(', i); k = t.index(')', j)
        d = self.tmp / 'die_strap.v'; d.write_text(t[:j] + ".owner_id({1'b1, 1'b1, 1'b0}" + t[k:])
        rec = json.loads((G / 'port_bind_v2.json').read_text()); rec['die_sha256'] = M.sha(d)
        r = self.tmp / 'rec_strap.json'; r.write_text(json.dumps(rec))
        with self.assertRaisesRegex(ValueError, 'owner_id straps'):
            M.derive(d, r, R, self.pads)

    def test_negative_ktree_reads_other_lane(self):
        d, r = self.mutated('.kpv_in(n_head_WS_0_0__kpv_k[0])', '.kpv_in(n_head_WS_0_0__kpv_k[1])')
        with self.assertRaises(ValueError):
            M.derive(d, r, R, self.pads)

    def test_negative_source_drift(self):
        root = self.tmp / 'root'
        for rel in M.SOURCES:
            (root / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy(R / rel, root / rel)
        p = root / 'rtl/qwen_sys/static_kv_20261014/qkd_ectl_c_st.sv'
        p.write_text(p.read_text().replace('.er_addr(so[12:1])', '.er_addr(so[12:1]) /*drift*/'))
        with self.assertRaisesRegex(ValueError, 'pinned source changed'):
            M.check_sources(root, M.PINNED)


if __name__ == '__main__':
    unittest.main()
