import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl
import eco_recovery as er


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.j = dict(name='hbglue_cl_8ddc70024', status='NEEDS_RTL', attempt=1, stage_idx=1,
                      commit_full='8ddc7002479798a1e3d5ce5875a163d672973e75', host='host', run=str(self.root),
                      spec=dict(source=dict(commit='8ddc7002479798a1e3d5ce5875a163d672973e75'),
                                block='ot_dsrom_head_bundle_glue', verdict=dict(post_sdc=[], corner_sta='{RUN}/corner_sta.json'),
                                stages=dict(calibrate=dict(enabled=False), route=dict(cmd='true'))),
                      eco=dict(tried=True, rb=str(self.root/'route'), ob=str(self.root/'route'),
                               pre=dict(ss_ps=190.49, ff_ps=-70.99),
                               result=dict(ss_ps=-340500.58, ff_ps=-59.43, drc=0, cells_added=0, errors=[])),
                      metrics=dict(ss_ps=190.49, ff_ps=-70.99, drc=0, corner_sta=[str(self.root/'corner_sta.json')],
                                   post_sdc=['physical/s81_die_views/hbglue/margin/signoff_cl_hbglue_cl_8ddc70024.sdc']))

    def test_guard_rejects_other_jobs_repeated_recovery_and_altered_evidence(self):
        cl.validate_overlay_recovery(self.j)
        mutations = [dict(name='other'), dict(attempt=2), dict(status='CLOSED'), dict(eco_overlay_recovery={'out':'x'}),
                     dict(failed_checks=['failure']), dict(eco=dict(self.j['eco'], installed='now')),
                     dict(eco=dict(self.j['eco'], post_sdc=['already_used.sdc'])),
                     dict(eco=dict(self.j['eco'], result=dict(self.j['eco']['result'], ss_ps=-1))),
                     dict(metrics=dict(self.j['metrics'], ss_ps=190.48))]
        for changes in mutations:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                cl.validate_overlay_recovery(dict(self.j, **changes))

    def test_command_queues_only_verdict_and_preserves_failure(self):
        with patch.object(cl, 'STATE', self.root/'state'):
            cl.save_job(self.j)
            old = copy.deepcopy(self.j)
            info = dict(out=str(self.root/'cl/eco-overlay-recovery-a2/candidate'), guard='/guard')
            with patch.object(cl, 'ssh', return_value=SimpleNamespace(stdout=json.dumps(info))), patch.object(cl, 'ledger'):
                cl.cmd_recover_eco_overlays(SimpleNamespace(name=self.j['name']))
            j = cl.load_job(self.j['name'])
            self.assertEqual(j['spec'], old['spec'])
            self.assertEqual(j['eco_history'], [old['eco']])
            self.assertEqual((j['status'], j['stage_idx'], j['stage_key'], j['attempt']), ('READY',1,'verdict',2))
            with self.assertRaises(ValueError):
                cl.cmd_recover_eco_overlays(SimpleNamespace(name=self.j['name']))

    def test_legacy_auto_requeue_cannot_repeat_explicit_recovery(self):
        self.j['eco_overlay_recovery'] = {'out': '/recovery/candidate'}
        self.j['eco']['result'] = None
        before = copy.deepcopy(self.j)
        with patch.object(cl, 'save_job') as save:
            cl.requeue_hold_only([self.j])
        save.assert_not_called()
        self.assertEqual(self.j, before)

    def test_admission_precedes_attempt_launch(self):
        fleet = Mock()
        fleet.fits.return_value = (False, 'no headroom')
        self.j['eco_overlay_recovery'] = dict(out='/new/candidate', guard='/new/inputs.json')
        with patch.object(cl, 'eco_paths', return_value=('/route','/route')), patch.object(cl,'launch_stage') as launch:
            self.assertTrue(cl.start_hold_eco(self.j, fleet, self.j['metrics']))
        launch.assert_not_called()
        self.assertNotIn('out', self.j['eco'])

    def test_launch_poll_and_install_use_new_output_and_guard(self):
        fleet = Mock()
        fleet.fits.return_value = (True, 'ok')
        self.j['eco_overlay_recovery'] = dict(out='/new/candidate', guard='/new/inputs.json')
        with patch.object(cl,'eco_paths',return_value=('/route','/route')), patch.object(cl,'ship_helpers'), \
                patch.object(cl,'launch_stage') as launch, patch.object(cl,'experiment'):
            cl.start_hold_eco(self.j, fleet, self.j['metrics'])
        cmd=launch.call_args.args[2]
        self.assertIn('ECO_GUARD=/new/inputs.json', cmd)
        self.assertIn('/new/candidate', cmd)
        self.assertEqual(cl.eco_output(self.j), '/new/candidate')
        install=cl.eco_install_cmd(self.j)
        self.assertIn('verify /new/inputs.json', install)
        self.assertIn('/new/candidate/corner_sta.json', install)
        self.assertNotIn('{CL}/eco/', install)
        with patch.object(cl,'poll_stage',return_value=('RC',0)), \
                patch.object(cl,'ssh',return_value=SimpleNamespace(stdout='{}')) as remote, \
                patch.object(cl,'ledger'), patch.object(cl,'summarize_failure',return_value=True):
            cl.step(self.j, fleet)
        self.assertIn('/new/candidate/result.json', remote.call_args.args[1])

    def prepare_fixture(self):
        hashes={}
        route=self.root/'route'; route.mkdir()
        for ext in ('odb','spef','sdc','v'):
            p=route/f'6_final.{ext}';p.write_text('original '+ext)
            if ext != 'v': hashes[ext]=er.digest(p)
        (route/'5_2_route.odb').write_text('pre-fill')
        overlay=self.root/'src'/self.j['metrics']['post_sdc'][0];overlay.parent.mkdir(parents=True);overlay.write_text('overlay')
        measured=dict(setup_ss=dict(worst_slack_ps=190.49, **{f'{k}_sha256':v for k,v in hashes.items()}),
                      hold_ff=dict(worst_slack_ps=-70.99), post_sdc={self.j['metrics']['post_sdc'][0]:er.digest(overlay)})
        (self.root/'corner_sta.json').write_text(json.dumps(measured))
        failed=self.root/'cl/eco';failed.mkdir(parents=True)
        (failed/'result.json').write_text(json.dumps(self.j['eco']['result']))
        for name, text in [('hold_eco.a1.rc','0'),('hold_eco.a1.sh','original wrapper'),('hold_eco.sh','helper'),('hold_eco.tcl','tcl')]:
            (self.root/'cl'/name).write_text(text)
        return dict(job=self.j, original_hashes=hashes, post_sdc_hashes=measured['post_sdc'])

    def test_preflight_preserves_evidence_and_rejects_reuse_or_changed_inputs(self):
        request=self.prepare_fixture()
        info=er.prepare(request)
        manifest=json.loads(Path(info['guard']).read_text())
        er.verify(manifest)
        self.assertFalse(Path(info['out']).exists())
        self.assertEqual(json.loads((Path(info['directory'])/'original_state.json').read_text()), self.j)
        with self.assertRaises(FileExistsError): er.prepare(request)
        (self.root/'cl/eco/result.json').write_text('changed failure')
        with self.assertRaises(ValueError): er.verify(manifest)

    def test_preflight_refuses_changed_original_without_reserving_attempt(self):
        request=self.prepare_fixture()
        (self.root/'route/6_final.odb').write_text('different original')
        with self.assertRaises(ValueError): er.prepare(request)
        self.assertFalse((self.root/'cl/eco-overlay-recovery-a2').exists())


if __name__ == '__main__':
    unittest.main()
