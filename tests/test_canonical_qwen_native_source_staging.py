"""Captured-role controls; no SRAM/whole-token qualification from mocks."""
from types import SimpleNamespace
import unittest
from tools.gpu_sys.canonical_qwen_native_source_staging import SourceStaging
from tools.gpu_sys.canonical_qwen_native_rf_pump import OwnedPage
from tools.gpu_sys.canonical_qwen_transport import TransportError


class Pins:
    def __init__(self,root,values):self.root=root;self.values=values
    def settle(self):pass
    def get(self,k):return self.values[k]
    def parameter(self,k):return self.values.get(k,0)


class SourceStagingTests(unittest.TestCase):
    def setUp(self):
        self.root=object();self.t=40<<164
        self.binding=SimpleNamespace(tuple239=self.t,owner55=7,fields=tuple(dict(
            cmd_source_slots=0,cmd_source_owners=77).items()))
        self.request=dict(sequence=90)
        self.p=Pins(self.root,dict(fault=0,context_live=1,source_cursor_valid=1,
            authority_tuple=self.t,authority_owner=7,authority_sequence=90,
            lease_slots=0,lease_owner=77,lease_workspace=1,lease_write=1,
            source_owner_held=0,lease_double=0,lease_version=111,lease_bank=0))
        self.policy=SourceStaging(self.root,self.p)
    def page(self):
        q=Pins(self.root,dict(query_result_write=1,query_result_workspace=1,
             query_result_version=111,query_result_first=0,query_result_end=10))
        rf=SimpleNamespace(ports=SimpleNamespace(tick=lambda:None))
        return OwnedPage(rf,SimpleNamespace(physical=q),self.t,0,77)
    def test_borrowed_read_role_does_not_stage(self):
        self.p.values.update(lease_workspace=0,lease_write=0,source_owner_held=1)
        self.assertFalse(self.policy.workspace(self.request,self.binding,0))
        with self.assertRaisesRegex(TransportError,'forbidden'):
            self.policy.write(self.request,self.binding,0,0,self.page(),b'x'*512)
    def test_borrowed_lost_owner_or_wrong_command_rejected(self):
        self.p.values.update(lease_workspace=0,lease_write=0,source_owner_held=0)
        with self.assertRaisesRegex(TransportError,'retained'):
            self.policy.workspace(self.request,self.binding,0)
        self.p.values['lease_owner']=78
        with self.assertRaisesRegex(TransportError,'differs'):
            self.policy.workspace(self.request,self.binding,0)
    def test_raw_workspace_payload_no_transformation_and_port_restored(self):
        page=self.page();original=page.RF.ports;payload=bytes(range(256))*2;seen=[]
        def write(p,raw):
            seen.append(raw);p.RF.ports.tick();return 'actual-transactor-result'
        self.policy.initializer=SimpleNamespace(write=write)
        result=self.policy.write(self.request,self.binding,0,0,page,payload)
        self.assertEqual((seen,result),([payload],'actual-transactor-result'))
        self.assertIs(page.RF.ports,original)
    def test_typed_query_direction_version_and_bounds_refused(self):
        for name,value in [('query_result_write',0),('query_result_workspace',0),
                           ('query_result_version',112),('query_result_first',1),('query_result_end',0)]:
            page=self.page();page.query.physical.values[name]=value
            with self.assertRaisesRegex(TransportError,'typed workspace'):
                self.policy.write(self.request,self.binding,0,0,page,b'x'*512)
    def test_scope_changed_during_wait_fails_before_rf_edge(self):
        page=self.page();original=page.RF.ports
        def write(p,raw):
            self.p.values['authority_sequence']=91
            p.RF.ports.tick()
        self.policy.initializer=SimpleNamespace(write=write)
        with self.assertRaisesRegex(TransportError,'scope lost'):
            self.policy.write(self.request,self.binding,0,0,page,b'x'*512)
        self.assertIs(page.RF.ports,original)
    def test_same_slot_owner_foreign_bank_not_workspace_authority(self):
        page=self.page();page.query.physical.values['SM_INDEX']=32
        with self.assertRaisesRegex(TransportError,'page identity'):
            self.policy.write(self.request,self.binding,0,0,page,b'x'*512)

if __name__=='__main__':unittest.main()
