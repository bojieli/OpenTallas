#!/usr/bin/env python3
"""STEWARD-QKd 10-23: kv_open_tail_roles source pins on the KV release line with OT_KV_CTL_NC32=1.

GEN rtl2 (093f075c5) PREP_FAIL in port_bind_v2: 'open-tail role source changed; re-prove: ..._n32_pj.sv'.  Under CTL_NC32
the die binds the '_nc32' tile file (no ctl body) + CTL_NC32_RTL, so the prover must pin and assert THOSE files:
  * TILES == kv_static_die.RTL_FILE ('_nc32'); CTL_NC32_RTL is pinned; the public _n32_pj file is not;
  * qkd_kvs_ctl ASSERT strings are checked on CTL_NC32_RTL, every other tile module on the nc32 tile file;
  * check_sources (hash pins + ASSERT + GEN_ASSERT chain-end strings) passes."""
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import test_kv_ctl_nc32_binding as B  # noqa: E402  (same release flags + knobs)

CODE = r'''
import sys, json; sys.path[:0] = ["tools/qwen_kv_die", "tools"]
import kv_open_tail_roles as T, kv_static_die as K
T.check_sources(T.ROOT)
mods = sorted({(r, m) for items in T.ASSERT.values() for r, m, _ in items if r in (T.TILES, K.CTL_NC32_RTL)})
print(json.dumps(dict(tiles=T.TILES, rtl=K.RTL_FILE, ctl=K.CTL_NC32_RTL, pinned=sorted(T.SOURCES), mods=mods)))
'''


class T(unittest.TestCase):
    def test_nc32_open_tail_pins(self):
        env = dict(os.environ, **B.flags(), **B.KNOBS)
        r = subprocess.run([sys.executable, '-c', CODE], cwd=B.ROOT, env=env, capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        d = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(d['tiles'], d['rtl'])
        self.assertTrue(d['tiles'].endswith('_n32_pj_nc32.sv'), d['tiles'])
        self.assertIn(d['ctl'], d['pinned'])
        self.assertNotIn('rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj.sv', d['pinned'])
        for r_, m in d['mods']:
            self.assertEqual(r_, d['ctl'] if m == 'qkd_kvs_ctl' else d['tiles'], m)


if __name__ == '__main__':
    unittest.main()
