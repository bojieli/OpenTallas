import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from kv_gen_source_ports import export


class SourcePortsTests(unittest.TestCase):
    def fixture(self, p):
        (p / 'die.v').write_text('module die;\n  wire [1:0] data;\n  frame u (.bus(data));\nendmodule\n')
        (p / 'actual.sv').write_text('module actual(output wire [1:0] b); assign b=2\'b01; endmodule\n')
        sha = hashlib.sha256((p / 'die.v').read_bytes()).hexdigest()
        bound = dict(die_sha256=sha, masters={'frame': dict(module='actual', bundles={
            'bus': dict(die_ports=['bus'], rtl_ports=['b'], die_bits=2, rtl_bits=2)})})
        bind = dict(verdict='PASS', failing=0, masters={'actual': dict(verdict='PASS', rtl='actual.sv', param_sets={'{}': 1})})
        (p / 'bound_netlist.json').write_text(json.dumps(bound))
        (p / 'port_bind_v2.json').write_text(json.dumps(bind))

    def test_exact_source_direction_and_identity(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.fixture(p)
            f = export(p, p, p)
            self.assertEqual(f['masters']['frame']['ports']['bus'], ['OUTPUT', 'OUTPUT'])
            self.assertEqual(f['source_sha256'][str(p/'actual.sv')], hashlib.sha256((p/'actual.sv').read_bytes()).hexdigest())

    def test_other_die_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.fixture(p)
            (p / 'die.v').write_text((p/'die.v').read_text()+'// changed\n')
            with self.assertRaisesRegex(ValueError, 'another die'):
                export(p, p, p)

    def test_source_width_change_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.fixture(p)
            (p / 'actual.sv').write_text('module actual(output wire [2:0] b); assign b=3\'b001; endmodule\n')
            with self.assertRaisesRegex(ValueError, 'bit count differs'):
                export(p, p, p)

    def test_snapshot_manifest_must_be_complete(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.fixture(p)
            with self.assertRaisesRegex(ValueError, 'manifest is incomplete'):
                export(p, p, p, {})

    def test_snapshot_hash_change_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.fixture(p)
            snapshots = {str(p/'actual.sv'): dict(path=str(p/'actual.sv'), sha256='0'*64)}
            with self.assertRaisesRegex(ValueError, 'snapshot hash mismatch'):
                export(p, p, p, snapshots)

    def test_snapshot_source_has_same_exact_direction(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.fixture(p)
            q = p/'snapshot.sv'
            q.write_bytes((p/'actual.sv').read_bytes())
            snapshots = {str(p/'actual.sv'): dict(path=str(q), sha256=hashlib.sha256(q.read_bytes()).hexdigest())}
            f = export(p, p, p, snapshots)
            self.assertEqual(f['masters']['frame']['ports']['bus'], ['OUTPUT', 'OUTPUT'])


if __name__ == '__main__':
    unittest.main()
