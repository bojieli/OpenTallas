"""Byte caller protocol tests using explicit port/physical-capture test doubles.

Not an RTL, W2, arithmetic or native execution oracle. HDL join separately gates
real accepted sector tuples and whole-root retirement under drain/backpressure.
"""
import unittest
from tools.gpu_sys.canonical_qwen_state_rpc_join import StateRPCByteHandlers
from tools.gpu_sys.canonical_qwen_transport import TransportError,PROGRAM_SHA

class Pins:
    def __init__(self):
        self.v=dict(por_n=1,local_reset=0,fault=0,rpc_ready=1,rpc_reply_valid=0,sector_capture_valid=0)
        self.captures=0;self.withdraw=False;self.wrong=False
    def parameter(self,name):return 1
    def set(self,name,value):self.v[name]=value
    def get(self,name):return self.v.get(name,0)
    def settle(self):pass
    def tick(self):
        if self.get('rpc_valid') and self.get('rpc_ready'):self.v['rpc_ready']=0
        if self.get('sector_capture_valid') and self.get('sector_capture_ready'):
            self.captures+=1;self.v['sector_capture_valid']=0
            if self.captures==2:
                self.v.update(rpc_reply_valid=1,rpc_reply_identity=self.get('rpc_identity')+int(self.wrong),
                              rpc_reply_rank=self.get('rpc_rank'),rpc_reply_address=self.get('rpc_address'),rpc_reply_bytes=self.get('rpc_bytes'))
        if self.get('rpc_reply_valid') and self.get('rpc_reply_ready'):self.v['rpc_reply_valid']=0
class Authority:
    def kv_aperture(self,request,region):return 0x100000,37504
    def kv_owner_retained(self,request):return True  # test double, not production authority
class Caller(StateRPCByteHandlers):
    def __init__(self,pins):super().__init__(Authority(),pins,enabled=True);self.calls=[]
    def _read_sector(self,request,sector):
        raw=bytes(range(32));self.calls.append(('OLD',sector,raw))
        self.rpc_ports.v.update(sector_capture_valid=1,sector_capture_source_addr=sector,sector_capture_old_data=int.from_bytes(raw,'little'))
        return raw
    def _sector(self,request,sector,payload=None):self.calls.append(('NEW',sector,payload));return {}
def request(**extra):
    r=dict(program_sha256=PROGRAM_SHA,source_PC=40,sequence=64,rank=1,address=0x10001e,payload=b'ABC')
    r.update(extra);return r
class StateRPCDriverTests(unittest.TestCase):
    def test_actual_OLD_byte_merge_and_two_capture_then_parent_reply(self):
        p=Pins();c=Caller(p)
        response=c.handlers['kv_state_write'](request())
        self.assertEqual([(v[0],v[1]) for v in c.calls],[('OLD',0x100000),('NEW',0x100000),('OLD',0x100020),('NEW',0x100020)])
        self.assertEqual(c.calls[1][2],bytes(range(30))+b'AB')
        self.assertEqual(c.calls[3][2],b'C'+bytes(range(1,32)))
        self.assertEqual(p.captures,2);self.assertTrue(response['visible'])
        self.assertEqual(p.get('rpc_reply_ready'),0);self.assertEqual(p.get('sector_capture_ready'),0)
    def test_wrong_hardware_parent_identity_faults_without_root_clear(self):
        p=Pins();p.wrong=True;c=Caller(p)
        with self.assertRaisesRegex(TransportError,'retirement identity'):c.handlers['kv_state_write'](request())
        self.assertTrue(c.stopped);self.assertIsNotNone(c.pending)
        self.assertEqual(p.get('rpc_reply_ready'),0);self.assertEqual(p.get('rpc_valid'),0)
    def test_source_extent_and_payload_width_refuse_without_issuing_command(self):
        for r in (request(payload=b'x'*33),request(address=0x100000+37503,payload=b'XY')):
            p=Pins();c=Caller(p)
            with self.assertRaises(TransportError):c.handlers['kv_state_write'](r)
            self.assertEqual(p.get('rpc_valid'),0);self.assertFalse(c.calls)
    def test_no_enable_or_foreign_program(self):
        with self.assertRaises(TransportError):StateRPCByteHandlers(Authority(),Pins())
        p=Pins();c=Caller(p)
        with self.assertRaises(TransportError):c.handlers['kv_state_write'](request(program_sha256='wrong'))
        self.assertEqual(p.get('rpc_valid'),0)
if __name__=='__main__':unittest.main()
