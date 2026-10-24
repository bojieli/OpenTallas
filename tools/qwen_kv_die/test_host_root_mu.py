#!/usr/bin/env python3
"""KV-BIND4-GUARD 10-19: the KV die HOST frame binds the MU 1 release host root under OT_KV_MU=1 (gen_host_root_mu.py).

  * the committed qkd_host_root_admission_mu.sv is exactly the generator's output (no hand edit);
  * its port list + parameters equal the MU 0 root's (drop-in: every die pin keeps its producer / reader);
  * the MU 1 branch binds exactly the CLOSED mu1s guard core RTL (endpoint_cancel_mu, SRAM guard FIFO) + the MU 1 peer
    core children (tp8_coordinator_mu POST_UID_SLOT 1, ctrl_token_service_packet_collected_mu);
  * kv_die selects it only under OT_KV_MU=1 (OT_KV_HOST_MU=0 keeps the MU 0 root).
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / 'mu_peer'))
import gen_host_root_mu as G  # noqa: E402
from mkmu import parse, port_list  # noqa: E402


def ports_params(rel, mod):
    params, ports, _ = parse(G.one_module((ROOT / rel).read_text(), mod), mod)
    return [p[3] for p in port_list(ports)], re.findall(r'(\w+)\s*=', re.sub(r'\[[^\]]*\]', '', params))


class HostRootMu(unittest.TestCase):
    def test_generated_current(self):
        self.assertEqual((ROOT / G.OUT_REL).read_text(), G.generate(ROOT))

    def test_drop_in_ports(self):
        for rel, mod, _ in G.SPECS:
            p0, a0 = ports_params(rel, mod)
            p1, a1 = ports_params(G.OUT_REL, mod + '_mu')
            self.assertEqual(p0, p1, mod)
            self.assertEqual(a0 + re.findall(r'(\w+)\s*=', G.POST.get(mod, ('MU=1',))[0]), a1, mod)  # + MU (+ HCW)

    def test_mu1_children(self):
        t = (ROOT / G.OUT_REL).read_text()
        for s in ('qkd_host_native_token_endpoint_cancel_mu #(.ENABLE_NATIVE(ENABLE_NATIVE),.MU(1))u_native(',
                  'qkd_host_guard_fifo #(.W(64),.SRAM_FIFO(1))markers(',
                  'qkd_host_tp8_coordinator_mu #(.MU(1),.POST_UID_SLOT(1))u_coordinator(',
                  'qkd_host_ctrl_token_service_packet_collected_mu #(.MU(1),.HCW(HCW),.STRAPPED(1),'):
            self.assertEqual(t.count(s), 1, s)
        co = (ROOT / 'rtl/qwen_sys/mu_qwen_20261018/qkd_host_tp8_coordinator_mu.sv').read_text()
        self.assertIn('parameter integer POST_UID_SLOT=0', co)
        self.assertIn('qkd_host_coordinator_services_mu #(.MU(1),.POST_UID_SLOT(POST_UID_SLOT)) u_lifecycle(', co)
        fifo = (ROOT / 'rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv').read_text()
        self.assertIn('ot_sram_1r1w_128x64_m1_p192 u_storage(', fifo)

    def test_kv_die_selection(self):
        code = ('import kv_die as K; b = K.BINDINGS["qkd_host_rt"]; '
                'print(b["module"], K.RTL["qkd_host_rt"], sorted(b["ports"]) == sorted(K.host_rt_binding()["ports"]))')
        got = {}
        for mu, hm in (('1', '1'), ('1', '0'), ('0', '1')):
            env = dict(os.environ, OT_KV_MU=mu, OT_KV_HOST_MU=hm)
            r = subprocess.run([sys.executable, '-c', code], cwd=HERE, env=env, capture_output=True, text=True,
                               timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            got[(mu, hm)] = r.stdout.split()
        self.assertEqual(got[('1', '1')][:2], ['qkd_host_root_admission_mu', G.OUT_REL])
        self.assertEqual(got[('1', '0')][0], 'qkd_host_root_admission')
        self.assertEqual(got[('0', '1')][0], 'qkd_host_root_admission')


if __name__ == '__main__':
    unittest.main()
