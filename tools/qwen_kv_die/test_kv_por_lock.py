#!/usr/bin/env python3
"""KDIE5-RTL 10-22: kvs_ctl.por_n is driven on the die (OT_KV_POR_LOCK, default ON) -- never an open input.

On the release point (relm kv_flags.env, results/rtl/qwen_kv_die/kdie5_tv_1022/relm_kv_flags.env):
  * bindings(): qkd_kvs_ctl binds por_n as a real port (no 'package POR pad' class that hides it from the port-bind audit);
  * _clocks_resets(): por_n joins the die pll_lock word (pll.locked -> host.pll_locked + kvs_ctl.por_n);
  * a GEN without a pll_lock bus refuses (no silent open input);
  * OT_KV_POR_LOCK=0 restores the legacy pad class (por_n classed, not a bus load)."""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FLAGS_ENV = ROOT / 'results/rtl/qwen_kv_die/kdie5_tv_1022/relm_kv_flags.env'

CODE = r'''
import sys, json; sys.path[:0] = ["tools/qwen_kv_die", "tools"]
import kv_static_die as K
b = K.bindings()["qkd_kvs_ctl"]
names = ["clk_core_c", "rst_die", "rst_hbm", "pll_lock"] + [f"clk_{d}_{s}" for d in ("core", "hbm") for s in K.STACKS]
B = [(n, "x", 1, [("src", "o")]) for n in names]
if "nolock" in sys.argv:
    B = [x for x in B if x[0] != "pll_lock"]
err = None
try:
    K._clocks_resets(dict(insts=[]), B, B.append, {})
except ValueError as e:
    err = str(e)
lock = next((eps for n, _, _, eps in B if n == "pll_lock"), [])
print(json.dumps(dict(on=K.POR_LOCK, ports="por_n" in b["ports"], classed=b.get("classed", {}),
                      lock=[e for e in lock if e[1] == "por_n"], err=err)))
'''


def flags():
    env = {}
    for line in FLAGS_ENV.read_text().splitlines():
        m = re.match(r"export (\w+)='(.*)'$", line)
        if m:
            env[m.group(1)] = m.group(2)
    return env


def run(extra=None, *args):
    env = dict(os.environ, **flags(), **(extra or {}))
    env.pop('OT_KV_POR_LOCK', None) if not extra or 'OT_KV_POR_LOCK' not in extra else None
    r = subprocess.run([sys.executable, '-c', CODE, *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    if r.returncode:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class T(unittest.TestCase):
    def test_default_on_drives_por_n(self):
        d = run()
        self.assertTrue(d['on'])
        self.assertTrue(d['ports'])
        self.assertNotIn('por_n', d['classed'])
        self.assertEqual(d['lock'], [['kvs_ctl', 'por_n']])
        self.assertIsNone(d['err'])

    def test_no_lock_bus_refuses(self):
        d = run(None, 'nolock')
        self.assertIn('POR_LOCK', d['err'] or '')

    def test_knob_off_legacy_pad(self):
        d = run(dict(OT_KV_POR_LOCK='0'))
        self.assertFalse(d['on'])
        self.assertFalse(d['ports'])
        self.assertIn('por_n', d['classed'])
        self.assertEqual(d['lock'], [])


if __name__ == '__main__':
    unittest.main()
