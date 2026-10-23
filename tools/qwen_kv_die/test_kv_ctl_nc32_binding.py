#!/usr/bin/env python3
"""KDIE5-RTL2 10-23: under OT_KV_CTL_NC32=1 the static-die bindings keep ONE source of qkd_kvs_ctl in the active readset.

GEN pceast_deps2 (128b91501) PREP_FAIL in kv_bound_netlist: 'qkd_kvs_ctl: indexed module qkd_kvs_ctl does not come from
selected source .../qkd_kvs_ctl_nc32.sv' -- bindings() bound every non-ctl tile to PUBLIC_RTL_FILE (which still declares
qkd_kvs_ctl) instead of the '_nc32' tile file, so die_port_bind.rtl_index (later prefer entry wins) took the public copy.
On the release flags (relm kv_flags.env + the GEN's grp r2 native32 / ctl nc32 / por_lock knobs):
  * qkd_kvs_ctl binds CTL_NC32_RTL; every other kvs tile binds RTL_FILE ('_nc32' suffix, no ctl body);
  * no active binding file other than CTL_NC32_RTL declares module qkd_kvs_ctl;
  * rtl_index over the binding files (prefer = binding files, as kv_bound_netlist) resolves qkd_kvs_ctl to CTL_NC32_RTL;
  * knob off: the tiles bind PUBLIC_RTL_FILE as before."""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FLAGS_ENV = ROOT / 'results/rtl/qwen_kv_die/kdie5_tv_1022/relm_kv_flags.env'
KNOBS = dict(OT_KV_GRP_R2='1', OT_KV_GRP_R2_NATIVE32='1', OT_KV_CTL_NC32='1', OT_KV_CTL_C32='2', OT_KV_POR_LOCK='1')

CODE = r'''
import sys, json; sys.path[:0] = ["tools/qwen_kv_die", "tools"]
from pathlib import Path
import kv_static_die as K
import die_port_bind as PB
b = K.bindings()
kv = {m: v["file"] for m, v in b.items() if m.startswith("qkd_kvs_")}
files = sorted({str(Path(v["file"]).resolve()) for v in b.values() if Path(v["file"]).exists()})
decl = [f for f in files if any(m.name == "qkd_kvs_ctl" for m in
        PB.parse_modules(PB.preprocess(PB.strip_comments(Path(f).read_text()), {}), f))]
order = [str(Path(v["file"]).resolve()) for v in b.values() if Path(v["file"]).exists()]
idx, _ = PB.rtl_index([], order, {}, order)
print(json.dumps(dict(kv=kv, decl=[str(Path(f).relative_to(Path.cwd().resolve())) for f in decl],
                      picked=str(Path(idx["qkd_kvs_ctl"].path).resolve().relative_to(Path.cwd().resolve())),
                      rtl=K.RTL_FILE, public=K.PUBLIC_RTL_FILE, nc32=getattr(K, "CTL_NC32_RTL", None))))
'''


def flags():
    env = {}
    for line in FLAGS_ENV.read_text().splitlines():
        m = re.match(r"export (\w+)='(.*)'$", line)
        if m:
            env[m.group(1)] = m.group(2)
    return env


def run(extra):
    env = dict(os.environ, **flags(), **extra)
    for k, v in extra.items():
        if v is None:
            env.pop(k, None)
    r = subprocess.run([sys.executable, '-c', CODE], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    if r.returncode:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class T(unittest.TestCase):
    def test_nc32_single_ctl_source(self):
        d = run(KNOBS)
        self.assertEqual(d['kv']['qkd_kvs_ctl'], d['nc32'])
        self.assertTrue(d['rtl'].endswith('_nc32.sv'), d['rtl'])
        for m, f in d['kv'].items():
            if m in ('qkd_kvs_ctl', 'qkd_kvs_grp_r2c', 'qkd_kvs_grp_h_r2c'):
                continue
            if f.startswith('rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles'):
                self.assertEqual(f, d['rtl'], m)
        self.assertEqual(d['decl'], [d['nc32']])
        self.assertEqual(d['picked'], d['nc32'])

    def test_knob_off_public_file(self):
        d = run(dict(KNOBS, OT_KV_CTL_NC32=None, OT_KV_CTL_C32=None))
        self.assertEqual(d['kv']['qkd_kvs_ctl'], d['public'])


if __name__ == '__main__':
    unittest.main()
