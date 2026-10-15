import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from compile_calendar import check_persistent_state


class PersistentStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);p=self.root/'cp.sv';p.write_text('// compiler-only test evidence\n')
        self.program=dict(ops=[dict(id='previous_native_field',start=0,end=10),dict(id='native_slot_store',start=11,end=20),
                               dict(id='L2.attn.cmp.pool',start=22,end=40),dict(id='L8.attn.cmp.pool',start=22,end=40)])
        self.binding=dict(jobs={o['id']:dict(implementation='native_rtl') for o in self.program['ops']},
                          tensors={n:dict(source='native_job',producer='previous_native_field') for n in ('prior_k','prior_sc')})
        self.state=dict(id='user0-L2-group7',cache='CP',physical_cache_instance='actual_die/u_cp',physical_bank=0,context_id=1,context_key='user0/L2/history7',
                        live_from_cycle=11,live_until_cycle=41,producer_job='native_slot_store',producer_commit_cycle=18,
                        state_input_tensors={'kv':'prior_k','score':'prior_sc'},consumer_jobs=['L2.attn.cmp.pool'],
                        evidence=[dict(path='cp.sv',sha256=hashlib.sha256(p.read_bytes()).hexdigest())])
        self.binding['persistent_cache_instances']={'actual_die/u_cp':dict(type='CP',physical_groups=1,evidence=self.state['evidence'])}
        self.binding['persistent_buffers']=[self.state]
        del self.binding['jobs']['L8.attn.cmp.pool']

    def check(self):return check_persistent_state(self.program,self.binding,self.root)

    def test_single_user_actual_prior_state_and_lifetime(self):
        self.assertEqual(self.check(),[])

    def test_missing_prior_slot_or_golden_tensor_is_rejected(self):
        self.state['producer_job']='golden_initialization'
        self.assertTrue(self.check())
        self.state['producer_job']='native_slot_store';self.binding['tensors']['prior_k']['source']='resident_constant'
        self.assertTrue(self.check())

    def test_two_open_users_cannot_share_one_physical_cache(self):
        other=copy.deepcopy(self.state);other.update(id='user1',context_id=2,context_key='user1/L8/history8',consumer_jobs=['L8.attn.cmp.pool'])
        self.binding['jobs']['L8.attn.cmp.pool']=dict(implementation='native_rtl')
        self.binding['persistent_buffers'].append(other)
        self.assertIn('overlapping open contexts',' '.join(e.get('reason','') for e in self.check()))

    def test_fake_second_physical_bank_is_rejected(self):
        self.state['physical_bank']=1
        self.assertTrue(self.check())

    def test_pool_cannot_precede_native_state_commit(self):
        self.state['producer_commit_cycle']=23
        self.assertTrue(self.check())

    def test_missing_state_reservation_blocks_pool(self):
        self.binding['persistent_buffers']=[]
        self.assertEqual(self.check()[0]['kind'],'missing_native_persistent_state')


if __name__=='__main__':unittest.main()
