import copy
from contextlib import contextmanager
import subprocess
import time
import unittest
from unittest.mock import Mock, patch

import closure_loop as C
from test_bench_track import Fleet, job


class CheckpointAffinity(unittest.TestCase):
    def setUp(self):
        self.j=job(host='AGI',run='/saved/job',bench_par=False,source_synced=True,resume={
            'same_host':True,'next_stage_dryrun':{'rc':0,'stage':'5_1_grt','host':'AGI','run':'/saved/job'},
            'completed_checkpoints_preserved':True})
        self.j['spec']=copy.deepcopy(self.j['spec'])
        self.j['spec']['stages']['calibrate']={'cmd':'cal','base':'/r','enabled':True}
        self.j['spec']['verdict']={'drc_metrics':'{RUN}/logs/asap7/x/base/5_2_route.json'}
        self.stages=C.stage_list(self.j['spec']);self.idx=next(i for i,s in enumerate(self.stages) if s['kind']=='route')
        self.j['stage_idx']=self.idx;self.st=self.stages[self.idx]
        self.fleet=Fleet();self.fleet.choose=Mock(return_value=('EPYC3','fits'))

    def test_capacity_wait_past_120_seconds_preserves_checkpoint_stage(self):
        self.j['wait_since']=time.time()-1000;self.fleet.fits=Mock(return_value=(False,'memory headroom'))
        with patch.object(C,'log'):
            self.assertIsNone(C.launch_ready(self.j,self.fleet,self.j['spec'],self.stages,self.st))
        self.fleet.choose.assert_not_called()
        self.assertEqual((self.j['host'],self.j['run'],self.j['stage_idx'],self.j['status']),('AGI','/saved/job',self.idx,'READY'))

    def test_same_host_source_sync_keeps_route_position(self):
        self.j['status']='SYNC'
        with patch.object(C,'sync_source') as sync,patch.object(C,'log'):
            C.step(self.j,self.fleet)
        sync.assert_called_once();self.fleet.choose.assert_not_called()
        self.assertEqual(self.j['stage_idx'],self.idx);self.assertEqual(self.j['status'],'READY')

    def test_wrong_host_source_sync_refused_before_any_remote_operation(self):
        self.j.update(host='EPYC3',run='/new/job')
        with patch.object(C,'ssh') as ssh,patch.object(C,'gfetch') as fetch:
            with self.assertRaisesRegex(ValueError,'without a verified full checkpoint transfer'):
                C.sync_source(self.j)
        ssh.assert_not_called();fetch.assert_not_called();self.assertEqual(self.j['stage_idx'],self.idx)

    def test_queued_resume_cannot_choose_empty_destination(self):
        self.j['status']='QUEUED'
        with patch.object(C,'sync_source'),patch.object(C,'log'):
            C.step(self.j,self.fleet)
        self.fleet.choose.assert_not_called();self.assertEqual(self.j['stage_idx'],self.idx)
        self.assertEqual(self.j['host'],'AGI')

    def test_resource_retry_stays_same_checkpoint_host(self):
        self.j['stage_tag']='route.a1'
        with patch.object(C,'stage_tail',return_value='Killed'),patch.object(C,'log'):
            C.crash(self.j,self.st,self.fleet,'resource pressure')
        self.fleet.choose.assert_not_called();self.assertEqual(self.j['host'],'AGI')
        self.assertEqual(self.j['stage_idx'],self.idx)

    def test_transient_sync_and_rebalance_never_source_migrate_resume(self):
        self.j.update(status='SYNC',transient=2)
        with patch.object(C,'log'):
            C.handle_transient(self.j,self.fleet,RuntimeError('ssh: reset'))
        self.fleet.choose.assert_not_called()
        with patch.object(C,'host_cfg',side_effect=AssertionError('resume must be excluded')),patch.object(C,'kill_own_stage') as kill:
            C.migrate_overloaded([self.j],self.fleet)
        kill.assert_not_called();self.assertEqual(self.j['stage_idx'],self.idx)

    def transfer(self,result):
        @contextmanager
        def command(host):yield ['ssh',host]
        def remote(host,script,**kw):
            if 'resume_check.sh' in script:return result
            return subprocess.CompletedProcess([],0,'','')
        with patch.object(C,'ssh',side_effect=remote),patch.object(C,'transport_command',command),patch.object(C.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')),patch.object(C,'host_cfg',return_value={'base':'/saved','label':'host'}),patch.object(C,'kill_own_stage'),patch.object(C,'ship_helpers'),patch.object(C,'save_job'),patch.object(C,'event'),patch.object(C,'experiment'):
            C.migrate_checkpoint(self.j,'EPYC3')

    def test_transfer_without_verified_resume_receipt_does_not_move_affinity(self):
        with self.assertRaisesRegex(RuntimeError,'resume check failed'):
            self.transfer(subprocess.CompletedProcess([],1,'RESUME_OK=0\n',''))
        self.assertEqual(self.j['host'],'AGI');self.assertEqual(self.j['checkpoint_affinity']['host'],'AGI')
        self.assertEqual(self.j['stage_idx'],self.idx)

    def test_transfer_exit_zero_without_explicit_receipt_is_not_verified(self):
        with self.assertRaisesRegex(RuntimeError,'resume check failed'):
            self.transfer(subprocess.CompletedProcess([],0,'dry run had no terminal receipt\n',''))
        self.assertEqual(self.j['host'],'AGI')
        self.assertEqual(self.j['stage_idx'],self.idx)

    def test_verified_full_transfer_updates_affinity_without_resetting_stage(self):
        self.transfer(subprocess.CompletedProcess([],0,'RESUME_FROM=5_1_grt\nRESUME_OK=1\n',''))
        self.assertEqual(self.j['host'],'EPYC3');self.assertEqual(self.j['checkpoint_affinity'],{'host':'EPYC3','run':'/saved/job'})
        self.assertTrue(self.j['resume']['checkpoint_transfer_verified']);self.assertEqual(self.j['stage_idx'],self.idx)

if __name__=='__main__':unittest.main()
