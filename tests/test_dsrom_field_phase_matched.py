"""Lightweight checker controls; no HDL or numerical workload."""
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1] / 'tools/dsrom_field_phase_matched.py'
s = importlib.util.spec_from_file_location('matched', P)
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)

LOG = '''A 0 1
G 35 0
XR 36 0
E 292 0
W 434 98304 3f800000
VMW 435 98304 3f800000
VMS 435 98304 3f800000
NODE go=1 first_w=434 last_w=434 idle=436 fault=0
PROFILE serial_offer=0 input_read_beats=1 input_bytes=256 last_write=434 idle=436 drain_after_write=2 last_vm_commit=435 drain_after_vm_commit=1
PASS cycles=452
'''

class Checks(unittest.TestCase):
    def check(self, log): return m.parse(log, {98304:0x3f800000}, 1, False)['pass_']
    def test_valid(self): self.assertTrue(self.check(LOG))
    def test_actual_storage_wrong(self): self.assertFalse(self.check(LOG.replace('VMS 435 98304 3f800000','VMS 435 98304 00000000')))
    def test_duplicate_write(self): self.assertFalse(self.check(LOG.replace('NODE ', 'VMS 435 98304 3f800000\nNODE ')))
    def test_terminal_duplicate(self): self.assertFalse(self.check(LOG+'PASS cycles=452\n'))
    def test_commit_edge(self): self.assertFalse(self.check(LOG.replace('VMW 435','VMW 434')))
    def test_fault(self): self.assertFalse(self.check(LOG.replace('fault=0','fault=1')))
    def test_early_retire(self): self.assertFalse(self.check(LOG.replace('idle=436','idle=434')))
    def test_wrong_tag(self): self.assertFalse(self.check(LOG.replace('G 35 0','G 35 1')))
    def test_wrong_mode(self): self.assertFalse(self.check(LOG.replace('serial_offer=0','serial_offer=1')))
    def test_missing_stored(self): self.assertFalse(self.check(LOG.replace('VMS 435 98304 3f800000\n','')))
    def test_extra_address(self): self.assertFalse(self.check(LOG.replace('NODE ', 'VMS 435 98305 3f800000\nNODE ')))

if __name__ == '__main__': unittest.main()
