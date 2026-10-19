"""Real producer/consumer RTL -> proposal CLI -> strict checker; immutable scope mutants."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]


class UnreadManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        (self.root / 'rtl').mkdir()
        for name in ['die_port_bind.py', 'die_bind_unread_manifest.py']:
            shutil.copyfile(TOOLS / name, self.root / 'tools' / name)
        self.source = self.root / 'rtl/producer.sv'
        self.source.write_text('''module producer #(parameter W=4)(input a, output [W-1:0] observation, output fault, output payload);
assign observation = {W{a}}; assign fault = a; assign payload = a;
endmodule
module consumer(input fault, input payload, output result);
assign result = fault ^ payload;
endmodule
''')
        producer, consumer = self.source.read_text().split('module consumer', 1)
        self.source.write_text(producer)
        self.consumer = self.root / 'rtl/consumer.sv'
        self.consumer.write_text('module consumer' + consumer)
        self.die = self.root / 'die.v'
        self.die.write_text('''module die(a, result);
input a;
output result;
wire [3:0] observed; wire fault; wire payload;
producer #(.W(4)) p(.a(a), .observation(observed), .fault(fault), .payload(payload));
consumer c(.fault(fault), .payload(payload), .result(result));
endmodule
''')
        self.contract = self.root / 'contract.json'
        self.contract.write_text('{"instances":{"p":{"master":"producer","params":{"W":4}}}}\n')
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.git('add', 'rtl')
        self.git('commit', '-qm', 'fixture source')
        rev = self.git('rev-parse', 'HEAD').stdout.strip()
        self.review = self.root / 'review.json'
        self.r = {'source_commit': rev, 'source_sha256': {'rtl/producer.sv': self.sha(self.source)},
                  'inputs': {'die_v': {'sha256': self.sha(self.die)},
                             'contract': {'sha256': self.sha(self.contract)}},
                  'approved_bits': 4,
                  'approved_entries': [self.entry([[0, 3]])]}
        self.write_review()
        self.manifest = self.root / 'manifest.json'
        self.report = self.root / 'report.json'

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, check=True, text=True, capture_output=True)

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def entry(self, rs):
        return {'instance': 'p', 'master': 'producer', 'port': 'observation', 'net': 'observed',
                'width': 4, 'unread_ranges': rs, 'bit_count': sum(b-a+1 for a,b in rs),
                'source': 'rtl/producer.sv', 'reason': 'reviewed observation only'}

    def write_review(self):
        self.review.write_text(json.dumps(self.r))

    def run_cli(self, *args):
        return subprocess.run(['python3', str(self.root / 'tools/die_port_bind.py'), str(self.die),
                               '--top', 'die', '--rtl-root', str(self.root / 'rtl'), '--no-macro-dirs',
                               '--out', str(self.report), *args], cwd=self.root, capture_output=True, text=True)

    def proposal(self, *args):
        return self.run_cli('--unread-review', str(self.review), '--unread-contract', str(self.contract),
                            '--unread-proposal-out', str(self.manifest), *args)

    def admitted(self, *args):
        return self.run_cli('--unread-review', str(self.review), '--unread-contract', str(self.contract),
                            '--unread-manifest', str(self.manifest),
                            '--unread-manifest-sha256', self.sha(self.manifest), *args)

    def ready(self):
        p = self.proposal()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('PROPOSAL_ONLY', p.stdout)

    def test_default_strict_and_exact_review(self):
        self.assertNotEqual(self.run_cli().returncode, 0)
        original = json.loads(self.report.read_text())
        self.assertEqual(original['summary']['unread_net_bits'], 4)
        self.assertNotIn('reviewed_unread', original)
        self.ready()
        p = self.admitted()
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        result = json.loads(self.report.read_text())
        self.assertEqual(result['reviewed_unread']['bits'], 4)
        self.assertEqual(result['summary']['unread_net_bits'], 0)

    def test_tuple_build_options_roundtrip(self):
        p = self.proposal('--strap', 'producer:a')
        self.assertEqual(p.returncode, 0, p.stderr)
        p = self.admitted('--strap', 'producer:a')
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertNotEqual(self.admitted().returncode, 0)

    def test_disjoint_ranges_remain_scoped(self):
        self.r['approved_entries'] = [self.entry([[0, 0]]), self.entry([[2, 2]])]
        self.r['approved_bits'] = 2
        self.write_review()
        self.ready()
        self.assertNotEqual(self.admitted().returncode, 0)
        self.assertEqual(json.loads(self.report.read_text())['summary']['unread_net_bits'], 2)

    def test_overlapping_entries_refused(self):
        self.r['approved_entries'] += [self.entry([[3, 3]])]
        self.r['approved_bits'] = 5
        self.write_review()
        self.assertIn('overlapping', self.proposal().stderr)

    def test_bad_ranges_refused(self):
        for rs in [[[0, 4]], [[-1, 2]], [[True, 2]], [[0, 2], [2, 3]], [[3, 1]]]:
            with self.subTest(rs=rs):
                self.r['approved_entries'][0]['unread_ranges'] = rs
                self.write_review()
                self.assertNotEqual(self.proposal().returncode, 0)

    def test_drift_refuses_and_producer_cannot_refresh(self):
        self.ready()
        for path, change in [(self.source, '\n// source drift'), (self.die, '\n// die drift'),
                             (self.contract, ' '), (self.review, ' ')]:
            old = path.read_text()
            path.write_text(old + change)
            with self.subTest(path=path.name):
                self.assertNotEqual(self.admitted().returncode, 0)
                if path != self.review:
                    self.assertNotEqual(self.proposal().returncode, 0)
            path.write_text(old)

    def test_occupied_fault_payload_permissions_refused(self):
        for port in ['fault', 'payload']:
            with self.subTest(port=port):
                e = self.entry([[0, 0]])
                e.update(port=port, net=port, width=1)
                self.r['approved_entries'] = [e]
                self.r['approved_bits'] = 1
                self.write_review()
                self.ready()
                p = self.admitted()
                self.assertNotEqual(p.returncode, 0)
                self.assertIn('occupied/read', p.stderr)

    def test_consumer_removed_refuses_identity(self):
        self.ready()
        self.die.write_text(self.die.read_text().replace('.fault(fault), .payload(payload), .result(result)',
                                                       ".fault(1'b0), .payload(1'b0), .result(result)"))
        self.assertNotEqual(self.admitted().returncode, 0)

    def test_parameter_define_and_missing_digest_refuse(self):
        self.ready()
        self.assertNotEqual(self.admitted('--define', 'CHANGED=1').returncode, 0)
        self.assertNotEqual(self.admitted('--no-child-closure').returncode, 0)
        self.die.write_text(self.die.read_text().replace('.W(4)', '.W(3)'))
        self.assertNotEqual(self.admitted().returncode, 0)

    def test_deep_consumer_source_pinned_and_digest_required(self):
        self.ready()
        self.consumer.write_text(self.consumer.read_text() + '\n// changed consumer')
        self.assertNotEqual(self.admitted().returncode, 0)
        self.assertNotEqual(self.proposal().returncode, 0)
        p = self.run_cli('--unread-review', str(self.review), '--unread-contract', str(self.contract),
                         '--unread-manifest', str(self.manifest))
        self.assertNotEqual(p.returncode, 0)

    def test_tampered_permission_and_pin_refuse(self):
        self.ready()
        obj = json.loads(self.manifest.read_text())
        obj['entries'][0]['instance'] = '*'
        self.manifest.write_text(json.dumps(obj))
        self.assertNotEqual(self.admitted().returncode, 0)
        self.ready()
        obj = json.loads(self.manifest.read_text())
        obj['source_sha256'] = {}
        self.manifest.write_text(json.dumps(obj))
        self.assertNotEqual(self.admitted().returncode, 0)


if __name__ == '__main__':
    unittest.main()
