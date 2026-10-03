import copy
import gzip
import importlib.util
import json
import hashlib
import socket
import struct
import tempfile
import threading
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('real_bridge_schedule',ROOT/'tools/h3_qwen_real_bridge_schedule.py')
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)


class ControlBackend:
    """Transport controls only. Does not implement numerical execution."""
    def __init__(self,primitives):
        self.primitives=primitives;self.edge=0;self.mutator=lambda r:r;self.calls=[]
    def capabilities(self):
        return dict(execution_kind='RTL_BRIDGE',source_pins={'CONTROL_TEST':'not production'},clock_domains={'streaming':{'target_hz':1200000000,'reset_epoch':0}},
            native_primitives=self.primitives,SMs_per_rank=32,RF_mirrors=2,max_native_outstanding=1,
            RF_slots_per_SM=512,
            shared_bytes_per_SM=65536,shared_transaction_bytes=64,
            methods=['pc_admit','pc_retire','version_admit','version_write','version_read','version_publish','version_retire','immutable_read','native',
                     'KV_begin','KV_write','KV_commit','KV_acquire','KV_read','KV_done','shared_stage','shared_release'])
    def transact(self,c):
        self.calls.append(c);events=[];parent=list(c['depends_on'])
        for i,phase in enumerate(M.REQUIRED_PHASES[c['kind']]):
            start=self.edge;self.edge+=2
            e=dict(eventID='e'+str(c['commandID'])+'/'+str(i),phase=phase,clock_domain='streaming',reset_epoch=0,resource=['SM0','RF'],start_edge=start,end_edge=self.edge,depends_on=parent,accepted=True)
            events.append(e);parent=[e['eventID']]
        owner=dict(owner46=1,native_tag64=1,generation64=1,reset_epoch=0,retained=True)
        response=dict(commandID=c['commandID'],PC=c['PC'],execution_kind='RTL_BRIDGE',source_pins=self.capabilities()['source_pins'],
            events=events,completion_event=e['eventID'],owner_binding=owner,native_complete=True,consumer_complete=True,reverse_CDC_complete=True)
        if 'version'in c['body']:response['version']=c['body']['version']
        return self.mutator(response)



class RealBridgeScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=ROOT/'results/uarch/h3_complete_native_calendar_20261002/bounded_provider_milestone/Qwen_tiled.json.gz'
        cls.native=json.loads(gzip.decompress(p.read_bytes()))
        cls.required=set()
        for op in cls.native['operations']:
            for name,count in op['calendar_export']['physical_primitives']['kernel_invocations'].items():
                if count:cls.required.update(cls.native['tile_kernel_ABI'][name]['native_counts_per_invocation'])
    def calendar(self):return M.BridgeCalendar(ControlBackend(self.required),self.native)
    def test_full_canonical_preflight(self):
        c=self.calendar();self.assertEqual(len(c.native['operations']),1737)
        self.assertEqual(len({o['opcode']for o in c.native['operations']}),21)
        self.assertEqual(c.serial,0)
    def test_cpu_backend_rejected(self):
        b=ControlBackend(self.required);caps=b.capabilities();caps['execution_kind']='CPU_PRIMITIVE_VM';b.capabilities=lambda:caps
        with self.assertRaisesRegex(ValueError,'CPU primitive'):M.BridgeCalendar(b,self.native)
    def test_missing_actual_opcode_rejected_before_run(self):
        with self.assertRaisesRegex(ValueError,'unimplemented'):M.BridgeCalendar(ControlBackend([]),self.native)
    def test_reduced_program_rejected(self):
        n=copy.copy(self.native);n['operations']=n['operations'][:40]
        with self.assertRaisesRegex(ValueError,'1737'):M.BridgeCalendar(ControlBackend(self.required),n)
    def test_reduced_shape_1737_program_also_rejected(self):
        n=copy.copy(self.native);n['source_program']=dict(n['source_program'],config=dict(n['source_program']['config'],hidden_size=8))
        with self.assertRaisesRegex(ValueError,'fullshape'):M.BridgeCalendar(ControlBackend(self.required),n)
    def test_empty_boundary_not_zero_service(self):
        c=self.calendar();c.backend.mutator=lambda r:dict(r,events=[])
        with self.assertRaisesRegex(ValueError,'zero-service'):c.call('version_read',{})
    def test_zero_edge_boundary_rejected(self):
        c=self.calendar()
        def bad(r):r['events'][0]['end_edge']=r['events'][0]['start_edge'];return r
        c.backend.mutator=bad
        with self.assertRaisesRegex(ValueError,'positive'):c.call('version_read',{})
    def test_actual_port_serialization(self):
        c=self.calendar();c.call('version_read',{});c.call('version_write',{})
        self.assertEqual(c.port_end['streaming',('SM0','RF')],10)
    def test_wrong_owner_generation_rejected(self):
        c=self.calendar();c.enter_pc(self.native['operations'][0])
        def bad(r):r['owner_binding']['generation64']=2;return r
        c.backend.mutator=bad
        with self.assertRaisesRegex(ValueError,'caller owner'):c.call('native',{})
    def test_source_pin_drift(self):
        c=self.calendar();c.backend.mutator=lambda r:dict(r,source_pins={'wrong':'source'})
        with self.assertRaisesRegex(ValueError,'source identity'):c.call('native',{})
    def test_causal_event_missing(self):
        c=self.calendar()
        def bad(r):r['events'][0]['depends_on']=['not accepted'];return r
        c.backend.mutator=bad
        with self.assertRaisesRegex(ValueError,'producer event'):c.call('native',{})
    def test_real_DAG_retirement(self):
        c=self.calendar();op=self.native['operations'][0];c.enter_pc(op);c.finish_pc(op)
        self.assertEqual(c.pc_done,[0])
        with self.assertRaises(ValueError):c.enter_pc(self.native['operations'][2])
    def test_no_reverse_no_retire(self):
        c=self.calendar();op=self.native['operations'][0];c.enter_pc(op)
        c.backend.mutator=lambda r:dict(r,reverse_CDC_complete=False)
        with self.assertRaisesRegex(ValueError,'reverse'):c.finish_pc(op)
        self.assertEqual(c.pc_done,[])
    def test_generic_event_cannot_pay_all_phases(self):
        c=self.calendar()
        def bad(r):r['events']=r['events'][:1];return r
        c.backend.mutator=bad
        with self.assertRaisesRegex(ValueError,'phases missing'):c.call('version_write',{})
    def test_later_command_cannot_erase_causality(self):
        c=self.calendar();c.call('version_read',{})
        def bad(r):r['events'][0]['depends_on']=[];return r
        c.backend.mutator=bad
        with self.assertRaisesRegex(ValueError,'preceding causal'):c.call('version_write',{})
    def test_captured_read_port_cannot_overlap(self):
        c=self.calendar();c.call('version_read',{})
        def bad(r):
            r['events'][0].update(start_edge=1,end_edge=3);return r
        c.backend.mutator=bad
        with self.assertRaisesRegex(ValueError,'port contention'):c.call('version_write',{})
    def test_cross_clock_requires_actual_match(self):
        c=self.calendar();c.capabilities['clock_domains']['serial']={'target_hz':900000000,'reset_epoch':0}
        def bad(r):r['events'][1]['clock_domain']='serial';return r
        c.backend.mutator=bad
        with self.assertRaisesRegex(ValueError,'cross-clock'):c.call('version_read',{})
    def test_CDC_invalid_sender_domain_rejected(self):
        c=self.calendar();c.capabilities['clock_domains']['serial']={'target_hz':900000000,'reset_epoch':0}
        def bad(r):
            r['events'][1].update(clock_domain='serial',CDC_match=dict(producer_event=r['events'][0]['eventID'],
                accepted=True,sender_domain='NOT_A_BOUND_CLOCK_DOMAIN',receiver_domain='serial',sender_reset_epoch=0,receiver_reset_epoch=0))
            return r
        c.backend.mutator=bad
        with self.assertRaisesRegex(ValueError,'domain/reset'):c.call('version_read',{})
    def test_stale_reset_event_rejected(self):
        c=self.calendar()
        def bad(r):r['events'][0]['reset_epoch']=1;return r
        c.backend.mutator=bad
        with self.assertRaisesRegex(ValueError,'reset epoch'):c.call('version_read',{})
    def test_completion_cannot_precede_write_ACK_visibility(self):
        c=self.calendar();c.backend.mutator=lambda r:dict(r,completion_event=r['events'][0]['eventID'])
        with self.assertRaisesRegex(ValueError,'premature'):c.call('version_write',{})
    def test_actual64B_shared_inventory(self):
        b=ControlBackend(self.required);caps=b.capabilities();caps['shared_transaction_bytes']=128;b.capabilities=lambda:caps
        with self.assertRaisesRegex(ValueError,'64B'):M.BridgeCalendar(b,self.native)
    def test_RF38_and_remoteRF32_have_no_invented_W2_parent(self):
        body={'locations':[{'home':['RF',0,0,38],'lane':0},{'home':['RF',0,24,32],'lane':0}]}
        self.assertEqual(M.hbm_sector_demands('version_read',body),[])
    def test_actual_HBM_partial_sector_patches_leave_oldtail_to_hardware(self):
        body=dict(locations=[dict(home=['HBM',1,0,1024],lane=1)],payload=b'\x01\x02\x03\x04')
        demands=M.hbm_sector_demands('version_write',body)
        self.assertEqual(demands,[dict(rank=1,source_byte_address=1024,sector_bytes=32,write=True,
            byte_mask=240,patches=[[4,1],[5,2],[6,3],[7,4]])])
    def test_strided_partial_KV_writes_enumerate_every_sector(self):
        body=dict(rank=0,addresses=[0,16,32,48],payload=b'abcd')
        demands=M.hbm_sector_demands('KV_write',body)
        self.assertEqual(len(demands),2)
        self.assertEqual(demands[0]['patches'],[[0,97],[16,98]])
        self.assertEqual(demands[1]['byte_mask'],1|(1<<16))
    def test_W2_reverse_authority_stub_rejected_before_any_service(self):
        b=ControlBackend(self.required);caps=b.capabilities()
        caps['W2']=dict(parameters=M.W2_PARAMETERS,authority_ports={p:'CONNECTED_ACTUAL_OWNER'for p in M.W2_AUTHORITY_PORTS})
        caps['W2']['authority_ports']['reverse_fenced']='TIE_HIGH'
        b.capabilities=lambda:caps;c=M.BridgeCalendar(b,self.native)
        with self.assertRaisesRegex(ValueError,'no stubs'):
            c.call('version_read',dict(locations=[dict(home=['HBM',0,0,1024],lane=0)]))
        self.assertFalse(b.calls)
    def test_W2_exact_sector_service_and_full_generation_echo(self):
        b=ControlBackend(self.required);caps=b.capabilities()
        caps['W2']=dict(parameters=M.W2_PARAMETERS,authority_ports={p:'CONNECTED_ACTUAL_OWNER'for p in M.W2_AUTHORITY_PORTS})
        b.capabilities=lambda:caps
        def result(r):
            body=b.calls[-1]['body'];head,tail=r['events']
            req=dict(eventID='w2.req',phase='W2_p_req_accept',clock_domain='streaming',reset_epoch=0,
                resource=['W2','PC0','request'],start_edge=2,end_edge=3,depends_on=[head['eventID']],accepted=True)
            ack=dict(eventID='w2.rsp',phase='W2_p_rsp_accept',clock_domain='streaming',reset_epoch=0,
                resource=['W2','PC0','response'],start_edge=23,end_edge=24,depends_on=[req['eventID']],accepted=True)
            tail.update(start_edge=24,end_edge=26,depends_on=[head['eventID'],ack['eventID']])
            r.update(events=[head,req,ack,tail],W2_sector_demands=body['W2_sector_demands'],
                W2_transactions=[dict(source_byte_address=1024,rank=0,PC_ID=0,client=0,customer_tag=123,
                    generation=15,physical_tag=123,physical_address=1024,generation_echo=15,customer_echo=123,
                    accepted_event=req['eventID'],completion_event=ack['eventID'],reverse_owner_retained=True,
                    repair_authority_bound=True)])
            return r
        b.mutator=result;c=M.BridgeCalendar(b,self.native)
        body=dict(locations=[dict(home=['HBM',0,0,1024],lane=0)])
        c.call('version_read',body)
        self.assertEqual(len(c.events),4)
        # Truncating or wrapping the separate generation field is a mismatch,
        # even with exactly matching payload/address/customer low bits.
        b2=ControlBackend(self.required);b2.capabilities=lambda:caps
        def wrong(r):
            original=b.calls;b.calls=b2.calls
            try:r=result(r)
            finally:b.calls=original
            r['W2_transactions'][0]['generation_echo']=0;return r
        b2.mutator=wrong
        with self.assertRaisesRegex(ValueError,'gen4/customer32'):
            M.BridgeCalendar(b2,self.native).call('version_read',body)
    def test_disk_index_preserves_full_event_and_duplicates_refused(self):
        with tempfile.TemporaryDirectory()as tmp:
            index=M.EventIndex(Path(tmp)/'events.sqlite')
            c=M.BridgeCalendar(ControlBackend(self.required),self.native,index)
            c.call('version_read',{});c.call('version_write',{})
            self.assertEqual(len(index),5)
            self.assertEqual(index['e1/0']['depends_on'],['e0/1'])
            with self.assertRaises(Exception):index['e0/0']={'wrong':'duplicate'}
            index.close()
            with self.assertRaisesRegex(ValueError,'preserve'):M.EventIndex(Path(tmp)/'events.sqlite')
    def test_native_call_uses_source_step_and_no_CPU_arithmetic(self):
        import numpy as np
        path=ROOT/'tools/h3_qwen_bounded_native.py'
        module=M.load_controller(path,hashlib.sha256(path.read_bytes()).hexdigest())
        def forbidden(*args,**kw):raise AssertionError('CPU primitive executed')
        original=module.NativePrimitiveVM.primitive
        module.NativePrimitiveVM.primitive=forbidden
        try:
            b=ControlBackend(self.required)
            def result(r):
                command=b.calls[-1]
                if command['kind']=='native':
                    r.update(dtype='<f4',shape=[],payload=struct.pack('<f',3),native_result_capture=True,
                             producer_retained=True,source_operands_bound=True,fault=False,
                             workspace_leases=[],
                             literal_source_step=command['body']['literal_source_step'])
                return r
            b.mutator=result
            machine,calendar=M.attach(module,self.native,b)
            calendar.enter_pc(self.native['operations'][0])
            value=machine.kernel('add',a=np.float32(1),b=np.float32(2))
            self.assertEqual(value.tobytes(),struct.pack('<f',3))
            self.assertEqual(b.calls[-1]['body']['source_instruction'],self.native['microcode']['add'][0])
            self.assertEqual(machine.vm.counts['FADD'],1)
            scalar=value[()]
            machine.kernel('add',a=scalar,b=np.float32(2))
            self.assertIn('parent',b.calls[-1]['body']['operands'][0]['origin'])
            self.assertNotIn('source_immediate',b.calls[-1]['body']['operands'][0]['origin'])
            self.assertEqual(calendar.pc_done,[]) # protocol control is never a token PASS
        finally:module.NativePrimitiveVM.primitive=original
    def test_workspace_slot_in_range_still_rejects_live_provider_alias(self):
        import numpy as np
        path=ROOT/'tools/h3_qwen_bounded_native.py'
        module=M.load_controller(path,hashlib.sha256(path.read_bytes()).hexdigest())
        b=ControlBackend(self.required)
        def result(r):
            command=b.calls[-1]
            if command['kind']=='version_admit':r.update(lease='actual-control-lease',alias_free=True)
            if command['kind']=='native':
                r.update(dtype='<f4',shape=[],payload=struct.pack('<f',3),native_result_capture=True,
                    producer_retained=True,source_operands_bound=True,fault=False,
                    literal_source_step=command['body']['literal_source_step'],
                    workspace_leases=[dict(**{'class':'RF'},rank=0,SM=0,
                        slot_first=38,slots=1,retained=True)])
            return r
        b.mutator=result;machine,calendar=M.attach(module,self.native,b)
        # A protocol control reserves the actual PC39 producer home. It does
        # not invent the missing PC0..39 production service or token completion.
        version=self.native['operations'][40]['reads'][0]
        calendar.pc=40;machine.store.reserve(version,0)
        self.assertEqual(machine.store.key(version,0,0),(('RF',0,0,38),0))
        self.assertEqual(machine.store.key(version,6144,0),(('RF',0,24,32),0))
        with self.assertRaisesRegex(ValueError,'entering live source'):
            machine.kernel('add',a=np.float32(1),b=np.float32(2))
        self.assertEqual(calendar.pc_done,[])
    def test_wire_socket_bytes_exact_and_rejected_receipt_retained(self):
        with tempfile.TemporaryDirectory()as tmp:
            path=str(Path(tmp)/'bridge.sock');server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            server.bind(path);server.listen(1);received=[];errors=[]
            def serve():
                try:
                    connection,_=server.accept()
                    with connection:
                        stream=connection.makefile('rb')
                        for response in [dict(program_sha256='PIN'),dict(payload=b'\x00\xff',execution_kind='REJECTED')]:
                            size=struct.unpack('!Q',stream.read(8))[0]
                            received.append(M.wire_decode(json.loads(stream.read(size))))
                            data=json.dumps(M.wire_encode(response)).encode()
                            connection.sendall(struct.pack('!Q',len(data))+data)
                except BaseException as e:errors.append(e)
            thread=threading.Thread(target=serve);thread.start()
            backend=M.SocketBridge(path,'PIN',Path(tmp)/'receipts.frames')
            response=backend.transact(dict(kind='native',payload=b'\xff\x00'))
            backend.close();thread.join();server.close()
            self.assertFalse(errors);self.assertEqual(response['payload'],b'\x00\xff')
            self.assertEqual(received[1]['payload'],b'\xff\x00')
            self.assertIn(b'REJECTED',(Path(tmp)/'receipts.frames').read_bytes())

if __name__=='__main__':unittest.main()
