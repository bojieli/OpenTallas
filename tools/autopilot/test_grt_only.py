"""GRT review scopes must stay GRT and never produce release sign-offs."""
import json
from pathlib import Path
import subprocess
import sys
from test_autopilot import Base, ROW


class TestGrtOnly(Base):
    def test_explicit_runner_and_submission_never_promotes_to_route(self):
        (j,) = self.ap.parse_queue('\t'.join(ROW + ['grt'])).values()
        self.assertIn('explicit GRT-only runner', j['error'])
        (j,) = self.ap.parse_queue('\t'.join(ROW + ['grt', '/srv/opentallas-scratch2/claude/grt_only.sh'])).values()
        self.assertEqual(j['error'], '')
        self.assertEqual(self.ap.runner_goal('grt', {'signoff_goals': ['finish', 'route']}), 'grt')
        calls = []
        self.ap.launch_unit = lambda unit, logfile, argv: calls.append(argv) or True
        self.ap.submit({}, j)
        pos = calls[0].index('--')
        self.assertEqual(calls[0][pos + 4], 'grt')

    def test_success_keeps_checkpoint_in_trial_table_without_archive(self):
        probe = {'goal': 'grt', 'grt_odb': '/k/5_1_grt.odb', 'grt_overflow': 0}
        cls, kind, why = self.ap.classify(probe, {'exit': 0})
        self.assertEqual((cls, kind), ('GRT-DONE', 'grt-only'))
        self.ap.archive = lambda *args: self.fail('GRT diagnostic must never archive SIGNED')
        j = dict(id='g1', die='s81', type='x', src='b@0123456789ab', host='epyc2',
                 kit='epyc2:/srv/opentallas-scratch2/claude/g/k', status=cls, reasons=why)
        self.ap.after_class({}, j)
        self.assertFalse(j['delete_pending'])
        self.assertIn('GRT-DONE', (Path(self.tmp.name) / 'trial.tsv').read_text())
        self.assertFalse((Path(self.tmp.name) / 'signed.tsv').exists())

    def test_probe_and_classification_reject_detailed_route_or_stale_signoff(self):
        kit = Path(self.tmp.name) / 'kit'
        base = kit / 'run/results/asap7/x/base'
        base.mkdir(parents=True)
        (base / '5_1_grt.odb').write_text('checkpoint')
        (base / '5_2_route.odb').write_text('scope overrun')
        out = subprocess.run([sys.executable, '-c', self.ap.PROBE_CLASSIFY,
                              json.dumps({'kit': str(kit), 'goal': 'grt'})],
                             capture_output=True, text=True, check=True).stdout
        c = json.loads(out.split('AP_JSON ', 1)[1])
        self.assertTrue(c['grt_odb'].endswith('5_1_grt.odb'))
        self.assertTrue(c['route_odb'].endswith('5_2_route.odb'))
        self.assertEqual(self.ap.classify(c, {'exit': 0})[:2], ('STRUCTURAL', 'diagnostic-overrun'))
        c.pop('route_odb')
        c['signoff'] = {'verdict': 'SIGNED'}
        self.assertEqual(self.ap.classify(c, {'exit': 0})[:2], ('STRUCTURAL', 'diagnostic-overrun'))
        self.assertEqual(self.ap.classify({'goal': 'grt', 'grt_odb': '/k/grt', 'grt_overflow': 7},
                                         {'exit': 0})[:2], ('STRUCTURAL', 'grt-overflow'))
        self.assertEqual(self.ap.classify({'goal': 'grt'}, {'exit': 0})[:2], ('CRASH', 'no-signoff'))
