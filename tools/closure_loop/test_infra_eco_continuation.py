import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch,Mock

import closure_loop as cl
import infra_eco_continuation as ie


class LinkedECOTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.runtime=self.root/'new-linked';self.runtime.mkdir()
        self.parent=dict(name='old-parent',run=str(self.root/'old-parent'),host='retired',
            status='CANCELLED',cancelled_at='2026-10-21',reason='EPYC6-RETIRE scheduled infrastructure',
            commit_full='f'*40,attempt=3,freeze_helper_overlay=True,
            route_overlay_plan=dict(files=[dict(path='tools/closure_loop/helper.py',sha256='1'*64)]),
            benches={'bench:positive':dict(ok=True,rc=0)},metrics=dict(ss_ps=82.85,ff_ps=-15.07,drc=0),
            eco=dict(started='before-retirement',pre=dict(ss_ps=82.85,ff_ps=-15.07)),
            spec=dict(name='old-parent',block='actual_block',source=dict(commit='f'*40,branch='source'),
                stages=dict(bench=[dict(name='positive',cmd='positive',expect='pass')],
                    route=dict(cmd='MUST NEVER RUN',peak_ram_gb=32),
                    collect=dict(cmd='collect {RUN}/routes/{LABEL}')),
                verdict=dict(corner_sta='{RUN}/routes/{LABEL}/corner_sta.json'),hold_eco=dict(enabled=True)))
        base='routes/old_parent/work/orfs/results/asap7/design/base'
        self.manifest=dict(schema=ie.SCHEMA,operation='lost_hold_eco',infrastructure_cause='scheduled_retirement',
            parent=dict(name='old-parent',state_sha256=ie.canonical_sha(self.parent),source_commit='f'*40),
            physical_disposition=dict(kind='hold_only',source_structural_required=False,setup_tt_ps=82.85,hold_ff_ps=-15.07,drc=0),
            interrupted_eco_checkpoint='none',source_completeness=dict(known_required_source_bytes_missing=[]),
            runtime=dict(host='live',run=str(self.runtime),image='sha256:'+'a'*64,ram_gb=64,
                         library_hashes={'/OpenROAD-flow-scripts/lib.lib':'2'*64}),
            checkpoint=dict(kind='5_2_route',route_base=base,eco_odb=base+'/5_2_route.odb',
                config='routes/old_parent/work/orfs/config.mk',corner_sta='routes/old_parent/corner_sta.json'),
            post_sdc_files=['src/physical/signoff.sdc'],file_hashes={})
        files=[base+'/'+x for x in ['5_2_route.odb','6_final.odb','6_final.spef','6_final.sdc']]
        files+=['routes/old_parent/work/orfs/config.mk','routes/old_parent/corner_sta.json',
                'src/physical/signoff.sdc','src/rtl/actual.sv','cl/helper.py']
        for rel in files:
            p=self.runtime/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(rel)
            self.manifest['file_hashes'][rel]=ie.file_sha(p)
        corner=self.runtime/self.manifest['checkpoint']['corner_sta']
        corner.write_text(json.dumps(dict(orfs_dir=str(self.runtime/Path(base).parents[3]))))
        self.manifest['file_hashes'][self.manifest['checkpoint']['corner_sta']]=ie.file_sha(corner)
        self.parent['route_overlay_plan']['files'][0]['sha256']=self.manifest['file_hashes']['cl/helper.py']
        self.manifest['parent']['state_sha256']=ie.canonical_sha(self.parent)
        (self.runtime/'cl/SRC_DIR').write_text(str(self.runtime/'src')+'\n')

    def test_new_record_has_only_postroute_stages_and_parent_unchanged(self):
        before=copy.deepcopy(self.parent);j=ie.build(self.parent,self.manifest,'new-linked')
        self.assertEqual(self.parent,before)
        self.assertEqual([x['kind'] for x in cl.stage_list(j['spec'])],['bench','route','verdict','collect','commit'])
        self.assertEqual(j['attempt'],4)
        self.assertEqual(j['spec']['source'],before['spec']['source'])
        self.assertIn('/routes/old_parent',j['spec']['stages']['collect']['cmd'])
        self.assertEqual(j['benches']['bench:positive']['inherited_from'],'old-parent')
        self.assertEqual(j['linked_infra_eco']['inherited_benches'],before['benches'])
        self.assertFalse(j['spec']['hold_eco']['allow_fresh_grt'])
        self.assertFalse(j['spec']['hold_eco']['vtswap']);self.assertFalse(j['spec']['auto_react'])

    def test_actual_source_or_hold_ineligible_dispositions_fail_closed(self):
        cases=[lambda p,m:p.update(status='NEEDS_RTL'),lambda p,m:p.update(reason='user cancelled'),
            lambda p,m:m['parent'].update(source_commit='0'*40),
            lambda p,m:m['checkpoint'].update(kind='6_final'),
            lambda p,m:m['source_completeness'].update(known_required_source_bytes_missing=['rtl/missing']),
            lambda p,m:p['eco'].update(installed='yes'),lambda p,m:p['eco'].update(result={'errors':['DUTFAIL']}),
            lambda p,m:p['benches']['bench:positive'].update(ok=False),
            lambda p,m:m['file_hashes'].pop('cl/helper.py'),
            lambda p,m:m['runtime'].update(image='openroad/orfs:latest')]
        for mutate in cases:
            p=copy.deepcopy(self.parent);m=copy.deepcopy(self.manifest);mutate(p,m)
            # Seal the supplied state to distinguish eligibility checks from stale-parent guard.
            m['parent']['state_sha256']=ie.canonical_sha(p)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):ie.build(p,m,'new-linked')
        p=copy.deepcopy(self.parent);m=copy.deepcopy(self.manifest)
        p['eco']['pre']['ss_ps']=-30.32;m['physical_disposition'].update(setup_tt_ps=-30.32)
        m['parent']['state_sha256']=ie.canonical_sha(p)
        with self.assertRaisesRegex(ValueError,'measured source/setup'):ie.build(p,m,'new-linked')

    def test_verification_rejects_changed_checkpoint_before_reserving_output(self):
        p=self.runtime/self.manifest['checkpoint']['eco_odb'];p.write_text('different ODB')
        with self.assertRaisesRegex(ValueError,'restored input differs'):ie.prepare_runtime(self.manifest,self.parent)
        self.assertFalse((self.runtime/'cl/linked_infra_eco').exists())

    def test_successful_preparation_seals_existing_guard_and_is_exclusive(self):
        with patch.object(ie.subprocess,'check_output',return_value=self.manifest['runtime']['image']+'\n'), \
             patch.object(ie.subprocess,'run'):
            got=ie.prepare_runtime(self.manifest,self.parent)
            with self.assertRaises(FileExistsError):ie.prepare_runtime(self.manifest,self.parent)
        self.assertTrue(got['verified'])
        guard=json.loads((self.runtime/'cl/linked_infra_eco/inputs.json').read_text())
        self.assertEqual(guard['hashes'][str(self.runtime/self.manifest['checkpoint']['eco_odb'])],
                         self.manifest['file_hashes'][self.manifest['checkpoint']['eco_odb']])
        self.assertEqual(json.loads((self.runtime/'cl/linked_infra_eco/parent_state.json').read_text()),self.parent)

    def test_changed_image_or_stale_route_path_cannot_create_guard(self):
        with patch.object(ie.subprocess,'check_output',return_value='sha256:'+'b'*64+'\n'):
            with self.assertRaisesRegex(ValueError,'image differs'):ie.prepare_runtime(self.manifest,self.parent)
        self.assertFalse((self.runtime/'cl/linked_infra_eco').exists())
        corner=self.runtime/self.manifest['checkpoint']['corner_sta']
        corner.write_text(json.dumps(dict(orfs_dir=self.parent['run']+'/old-route')))
        self.manifest['file_hashes'][self.manifest['checkpoint']['corner_sta']]=ie.file_sha(corner)
        with self.assertRaisesRegex(ValueError,'path-only rebase'):ie.prepare_runtime(self.manifest,self.parent)
        self.assertFalse((self.runtime/'cl/linked_infra_eco').exists())

    def test_production_launch_refuses_route_and_default_image_env_unchanged(self):
        j=ie.build(self.parent,self.manifest,'new-linked')
        for kind in ('bench','route','calibrate','signoff'):
            with self.subTest(kind=kind),self.assertRaises(ValueError):cl.launch_stage(j,dict(kind=kind), 'unsafe')
        self.assertEqual(ie.pinned_env({}),'')
        env=ie.pinned_env(j);self.assertIn('export ORFS_IMAGE=sha256:',env)
        self.assertIn('openroad/orfs:latest',env);self.assertIn('exit 86',env)
        with patch.object(cl,'ssh',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')) as ssh:
            cl.remote_ok(j,'check')
        self.assertIn(self.manifest['runtime']['image'],ssh.call_args.args[1])

    def test_existing_eco_launcher_and_installer_keep_new_guarded_output(self):
        j=ie.build(self.parent,self.manifest,'new-linked');j['stage_idx']=2;fleet=Mock();fleet.fits.return_value=(True,'fits')
        with patch.object(cl,'eco_paths',return_value=('/new/route','/new/route')), \
                patch.object(cl,'ship_helpers'),patch.object(cl,'launch_stage') as launch,patch.object(cl,'experiment'):
            cl.start_hold_eco(j,fleet,j['metrics'])
        cmd=launch.call_args.args[2]
        self.assertIn('ECO_GUARD=',cmd);self.assertIn('ALLOW_FRESH_GRT=0',cmd)
        self.assertIn('/cl/linked_infra_eco/candidate',cmd)
        install=cl.eco_install_cmd(j)
        self.assertIn('eco_recovery.py verify',install)
        self.assertIn('/cl/linked_infra_eco/candidate',install)
        self.assertNotIn('MUST NEVER RUN',install)

    def test_apply_writes_only_new_record_dry_run_has_no_state_effects(self):
        state=self.root/'state';(state/'jobs').mkdir(parents=True)
        args=SimpleNamespace(name='old-parent',new_name='new-linked',manifest=str(self.root/'manifest.json'),apply=False)
        Path(args.manifest).write_text(json.dumps(self.manifest))
        with patch.object(cl,'STATE',state),patch.object(cl,'hosts_table',return_value=[dict(name='live')]),patch.object(cl,'ledger'):
            cl.save_job(self.parent);old=cl.jpath('old-parent').read_bytes()
            self.manifest['parent']['state_sha256']=ie.canonical_sha(cl.load_job('old-parent'))
            Path(args.manifest).write_text(json.dumps(self.manifest))
            with patch.object(cl,'ssh') as ssh:
                cl.cmd_link_infra_eco(args)
                ssh.assert_not_called();self.assertFalse(cl.jpath('new-linked').exists())
            args.apply=True
            response=dict(verified=True,manifest_sha256=ie.canonical_sha(self.manifest))
            with patch.object(cl,'ssh',return_value=SimpleNamespace(stdout=json.dumps(response))) as ssh:
                cl.cmd_link_infra_eco(args)
                self.assertEqual(cl.jpath('old-parent').read_bytes(),old)
                self.assertEqual(cl.load_job('new-linked')['status'],'READY')
                child=cl.load_job('new-linked')
                self.assertEqual(cl.stage_list(child['spec'])[child['stage_idx']]['kind'],'verdict')
                # Large source manifests travel on stdin, never through argv/shell quoting.
                self.assertEqual(ssh.call_args.args[1],'python3 -')
                with self.assertRaisesRegex(ValueError,'already exists'):cl.cmd_link_infra_eco(args)
