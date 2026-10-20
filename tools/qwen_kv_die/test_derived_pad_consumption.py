"""Consume generated role proofs through the real strict binder CLI."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import kv_output_pads as O

ROOT = Path(__file__).resolve().parents[2]


class ActualConsumption(unittest.TestCase):
    def fixture(self, tmp):
        die = tmp/'die.v'
        die.write_text("module die(ck);\ninput ck;\nwire n_lane__spare;\n"
                       "qkd_rlys_1 lane(.ck(ck), .a(1'b0), .b(n_lane__spare));\nendmodule\n")
        pad = tmp/'pads.json'
        pad.write_text(json.dumps(O.derive(die)))
        return die, pad

    def run_cli(self, die, pad, *extra):
        return subprocess.run([sys.executable, str(ROOT/'tools/die_port_bind.py'), str(die),
                               '--rtl-root', str(die.parent/'empty'), '--no-macro-dirs',
                               '--rtl-file', str(ROOT/O.RTL), '--pad-file', str(pad), *extra],
                              text=True, capture_output=True)

    def test_exact_generated_receipt_is_consumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            die, pad = self.fixture(Path(tmp));p = self.run_cli(die, pad)
            self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
            self.assertIn('PASS', p.stdout)

    def test_stale_die_receipt_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            die, pad = self.fixture(Path(tmp));die.write_text(die.read_text()+'// changed actual bound die\n')
            p = self.run_cli(die, pad)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn('contract die SHA mismatch', p.stderr)

    def test_each_role_contract_is_checked_at_consumption(self):
        for name in ('static_head_unused_contract', 'pvw_padding_contract'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                die, pad = self.fixture(Path(tmp));doc = json.loads(pad.read_text())
                doc[name] = dict(die_sha256='0'*64, source_sha256={O.RTL:O.RTL_SHA})
                pad.write_text(json.dumps(doc));p = self.run_cli(die, pad)
                self.assertNotEqual(p.returncode, 0);self.assertIn(name, p.stderr)

    def test_changed_role_source_is_not_descriptive_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp);die, pad = self.fixture(tmp);src = tmp/'parent.sv';src.write_text('module parent; endmodule\n')
            doc = json.loads(pad.read_text());doc['static_head_unused_contract'] = dict(
                die_sha256=hashlib.sha256(die.read_bytes()).hexdigest(),
                source_sha256={str(src):hashlib.sha256(src.read_bytes()).hexdigest()})
            pad.write_text(json.dumps(doc));src.write_text('module parent; wire mutation; endmodule\n')
            p = self.run_cli(die, pad);self.assertNotEqual(p.returncode, 0)
            self.assertIn('source SHA mismatch', p.stderr)

    def test_actual_selected_payload_source_must_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp);die, pad = self.fixture(tmp);foreign = tmp/'foreign.sv'
            foreign.write_text("module qkd_rlys_1(input ck,a, output b); assign b=~a; endmodule\n")
            p = self.run_cli(die, pad, '--rtl-file', str(foreign), '--prefer', str(foreign))
            self.assertNotEqual(p.returncode, 0)
            self.assertIn('selected RTL differs from pinned source: qkd_rlys_1', p.stderr)

    def test_external_master_parameter_change_requires_rederivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp);die, pad = self.fixture(tmp);params = tmp/'params.json'
            params.write_text(json.dumps(dict(masters=dict(qkd_rlys_1=dict(MUT=1)))))
            p = self.run_cli(die, pad, '--params', str(params))
            self.assertNotEqual(p.returncode, 0)
            self.assertIn('do not bind external parameter overrides', p.stderr)

    def test_plain_declared_pad_schema_remains_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            die, pad = self.fixture(Path(tmp));doc = json.loads(pad.read_text());del doc['source_contract']
            pad.write_text(json.dumps(doc));p = self.run_cli(die, pad)
            self.assertEqual(p.returncode, 0, p.stdout+p.stderr)


if __name__ == '__main__':
    unittest.main()
