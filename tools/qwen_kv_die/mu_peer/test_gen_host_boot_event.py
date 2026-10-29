#!/usr/bin/env python3
"""TOK-QWEN-8: the ordered D2D boot event must wait on the LOCAL programme install in every HOST variant.

program_ready needs the peer witness commit, which the d2d calendar carries only after the boot epoch that this
event starts (TOK-QWEN-7 kvl deadlock 10-29). Checks the generator output is the committed bo1 RTL, and that both
bo1 and the C45 bind variant gate the bridge on program_installed_local, exported by the rank services block.
"""
import re, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_host_boot_event as gen  # noqa: E402

D = ROOT / 'rtl/qwen_sys/kv_host_obs_20261019'
BO1 = D / 'qkd_host_root_admission_obsx_bo1.sv'
C45 = ROOT / 'physical/die_plan/qwen_kvsys/bind/kv45/qkd_host_root_admission_obsx_bo1_c45.sv'


def bridge_installed(text):
    m = re.search(r'qkd_d2d_boot_event_bridge\s*#\(\.ENABLE\(D2D_BOOT_ORDER\)\)\s*u_d2d_boot_event\s*\((.*?)\);', text, re.S)
    assert m, 'bridge instance not found'
    return re.search(r'\.installed\((.*?)\),\s*\.boot_begin', m.group(1), re.S).group(1)


class BootEventPredicate(unittest.TestCase):
    def test_generator_reproduces_committed_rtl(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'bo1.sv'
            gen.build(ROOT, out)
            self.assertEqual(out.read_text(), BO1.read_text())

    def check_variant(self, text):
        inst = bridge_installed(text)
        self.assertIn('program_installed_local', inst)
        self.assertNotRegex(inst, r'\bprogram_ready\b')
        self.assertIn('.program_installed_local(program_installed_local)', text)
        self.assertRegex(text, r'assign program_installed_local=program_ready;\s*\nend else begin:g_mu')

    def test_bo1(self):
        self.check_variant(BO1.read_text())

    @unittest.skipUnless(C45.exists(), 'C45 bind variant not checked out')
    def test_c45(self):
        self.check_variant(C45.read_text())

    def test_local_install_excludes_peer_commit(self):
        src = (D / 'qkd_host_root_admission_obsx.sv').read_text()
        m = re.search(r'assign program_installed_local=([^;]*);', src)
        self.assertTrue(m)
        for term in ('committed', 'program_installed_valid', 'commit_fault'):
            self.assertNotRegex(m.group(1), r'\b%s\b' % term)
        ready = re.search(r'assign program_ready=([^;]*);', src).group(1)
        for term in re.findall(r'!?\w+(?:==0)?', m.group(1)):
            self.assertIn(term, ready)  # local install is a strict subset of program_ready


if __name__ == '__main__':
    unittest.main()
