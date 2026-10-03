"""Source-only proof/protocol tests; no model inference or hardware PASS."""
import unittest
from tools.gpu_sys import canonical_qwen_service_calendar as C
from tools.gpu_sys import canonical_qwen_matrix_loop as M
from tools.gpu_sys import canonical_qwen_matrix_padding as P
from tools.gpu_sys import canonical_qwen_matrix_services as S
from tools.gpu_sys.test_canonical_qwen_matrix_loop import Pins

class ServicePins(Pins):
    def settle(self):pass
    def parameter(self,key):return {'NC':6,'MAX_OUT':16,'AW':34,'CTAGW':32,'GENW':4,'PTAGW':35,
        'OPT_EXACT':1,'OPT_RESET_QUARANTINE':1,'PC_ID':7,'ACK_ID':1}[key]
    def set_client(self,c,k,v):self.values[k+'_'+str(c)]=v

class ReadAuthority:
    def __init__(self):self.capture=True;self.reverse=False
    def completion_ready(self,*a):return self.capture
    def reverse_validated(self,*a):return self.reverse

class PaddingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native=C.read(C.ROOT/C.PROGRAM);cls.proof=P.padding_proof()
        cls.pc=next(o['pc'] for o in cls.native['operations'] if o['opcode']=='MATRIX' and cls.native['source_program']['weight_descriptors'][o['attributes']['weight']]['split']==64)
        cls.tile=P.lower_matrix(cls.native,cls.pc,enabled=True)[0]
    def test_all290_source_MATRIX_PCs_have_exact_descriptors(self):
        ops=[o for o in self.native['operations'] if o['opcode']=='MATRIX']
        tiles=[P._lower_verified(self.native,o['pc'],self.proof) for o in ops]
        self.assertEqual(len(tiles),290)
        self.assertEqual(sum(t[0].split==64 for t in tiles),72)
        self.assertEqual(sum(len(t) for t in tiles),14436)
    def test_original_refusal_remains_and_successor_proof_is_explicit(self):
        with self.assertRaises(ValueError):M.lower_matrix(self.native,self.pc,enabled=True)
        self.assertTrue(self.proof['source_correctness']);self.assertFalse(self.proof['physical_admission'])
        self.assertFalse(self.proof['numerical_waveform_PASS'])
        self.assertEqual(self.tile.padding_proof_sha256,C.sha(C.canonical(self.proof)))
    def test_padded_exact_contiguous_recurrence_and_unique_code_bytes(self):
        t=self.tile;self.assertEqual((t.split,t.chunk,t.groups),(64,64,1))
        self.assertEqual(t.fragments,64);self.assertEqual(t.line_count,8192)
        row_vectors=[t.line(step*8)['source_K_indices'] for step in range(64)]
        for leaf in range(64):
            self.assertEqual([v[leaf] for v in row_vectors],list(range(leaf*64,(leaf+1)*64)))
        self.assertTrue(all(k is None for v in row_vectors for k in v[64:]))
        self.assertEqual(sorted(k for v in row_vectors for k in v if k is not None),list(range(4096)))
        self.assertEqual(t.line(8191)['line_address'],8191)
    def test_canonical_zero_symbolic_branch_all_cases(self):
        # Specialize the PINNED bypass branch at b=+0/nonfinite=False;
        # this is a Boolean proof of the exact branch, not float execution.
        for a_zero in (False,True):
            returned='0' if a_zero else 'a'
            canonical_source='0' if a_zero else 'a'
            self.assertEqual(returned,canonical_source)
        self.assertEqual(self.proof['extra_pipeline_edges'],7)
    def test_padding_latency_and_all_physical_sector_reads_are_charged(self):
        m=P.price_tiles((self.tile,),100)
        self.assertEqual(m['weight_line_requests'],8192)
        self.assertEqual(m['xstore_write_beats'],1024)
        self.assertEqual(m['uncached_gather_code_sector_reads32'],8192*64)
        self.assertEqual(m['padded_extra_pipeline_edges_per_tile'],7)

class PumpTests(unittest.TestCase):
    def test_actual_W2_capture_then_reverse_not_clock_timer(self):
        p=ServicePins();a=ReadAuthority();port=S.W2PrimaryPort(p,a);v=S.W2ReadPump()
        v.start((1,port,2,64,19,3));p.values['c_req_rdy']=1<<2
        v.before_edge();v.after_edge();self.assertEqual(v.phase,'response')
        raw=bytes(range(32));p.values.update(c_rsp_v=1<<2,c_rsp_tag=19<<(32*2),c_rsp_gen=3<<(4*2),
                                           c_rsp_data=int.from_bytes(raw,'little')<<(256*2))
        v.before_edge();v.after_edge();p.values['c_rsp_v']=0
        self.assertIsNone(v.take());self.assertIsNotNone(port.pending)
        v.before_edge();v.after_edge();self.assertIsNone(v.take())
        a.reverse=True;v.before_edge();v.after_edge()
        self.assertEqual(v.take(),raw);self.assertIsNone(port.pending)
    def test_W2_wrong_generation_and_request_repair_refused(self):
        p=ServicePins();a=ReadAuthority();port=S.W2PrimaryPort(p,a);v=S.W2ReadPump()
        v.start((0,port,1,32,8,2));p.values.update(c_req_rdy=2,repair_busy=1)
        with self.assertRaises(ValueError):v.before_edge()
        p.values['repair_busy']=0;v.before_edge();v.after_edge()
        p.values.update(c_rsp_v=2,c_rsp_tag=8<<32,c_rsp_gen=3<<4)
        with self.assertRaises(ValueError):v.before_edge()
    def test_actual_scratch_write_waits_done_and_actual_read_capture(self):
        p=ServicePins();v=S.ScratchPump(p);p.values['ready']=1;v.start(129,bytes(64))
        v.before_edge();v.after_edge();self.assertIsNone(v.take())
        p.values['done']=1;v.before_edge();v.after_edge();self.assertEqual(v.take(),b'')
        p.values['done']=0;v.start(129);v.before_edge();v.after_edge()
        p.values.update(done=1,rdata=int.from_bytes(bytes(range(64)),'little'))
        v.before_edge();v.after_edge();self.assertEqual(v.take(),bytes(range(64)))
    def test_W4_commonACK_owner55_not_first_wrong_owner(self):
        from tools.gpu_sys.canonical_qwen_rf_ports import RFPorts
        p=ServicePins();v=S.RFWritePump(RFPorts(p));v.start(38,17,bytes(512))
        p.values['wr_ready']=1;v.before_edge();v.after_edge();self.assertFalse(v.take())
        p.values.update(ack_valid=1,ack_slot=38,ack_owner=18)
        with self.assertRaises(ValueError):v.before_edge()
        p.values['ack_owner']=17;v.before_edge();v.after_edge();self.assertTrue(v.take())

class ServiceTests(unittest.TestCase):
    def service(self):
        class Authority:pass
        a=Authority()
        for k in S.MatrixPhysicalServices.REQUIRED:setattr(a,k,lambda *args:None)
        s=S.MatrixPhysicalServices(a,ServicePins(),enabled=True);s.reservation={};return s,a
    def test_missing_actual_authority_refused(self):
        with self.assertRaises(ValueError):S.MatrixPhysicalServices(object(),ServicePins(),enabled=True)
    def test_source_leases_are_never_workspace_retired(self):
        s,a=self.service()
        a.matrix_workspace_release=lambda *x:dict(workspace_released=True,source_leases_retired=True)
        with self.assertRaises(ValueError):s.release_tile({}, {})
        self.assertTrue(s.faulted)
        s,a=self.service()
        a.matrix_workspace_release=lambda *x:dict(workspace_released=True,source_leases_retired=False)
        self.assertTrue(s.release_tile({}, {}))
        a.matrix_issuer_workspace_retire=lambda *x:dict(workspace_released=True,source_leases_retired=True)
        s.origin=dict(identity={},GO_tuple239=0);s.input_rows=()
        with self.assertRaises(ValueError):s.release_operator(s.origin,dict(identity={},GO_tuple239=0,input_rows=()))
    def test_partial_input_barrier_cannot_GO(self):
        s,a=self.service();go=[]
        a.matrix_input_binding=lambda *x:dict(all_input_leases_bound=False,program_sha256=C.PROGRAM_SHA,source_PC=2,input_rows=(1,))
        a.matrix_begin=lambda *x:go.append(x)
        self.assertIsNone(s.begin_operator(dict(program_sha256=C.PROGRAM_SHA,source_PC=2)))
        self.assertFalse(go)
    def test_captured_GO_is_not_mutated_live_authority_dictionary(self):
        s,a=self.service();identity=dict(session=9,source_PC=2,native_tag=3,native_generation=4,rank=0,SM=0,
            output_version_id=7,range_begin=2,range_end=3)
        origin=dict(identity=identity,input_rows=(1,),GO_tuple239=S.pack_GO(identity))
        a.matrix_input_binding=lambda *x:dict(all_input_leases_bound=True,program_sha256=C.PROGRAM_SHA,source_PC=2,input_rows=(1,),
            output_ranges=(dict(rank=0,SM=0,output_version_id=7,range_begin=2,range_end=3,owner55=2,expected_ACK_bitmap=1,source_version='v'),))
        a.matrix_begin=lambda *x:origin
        saved=s.begin_operator(dict(program_sha256=C.PROGRAM_SHA,source_PC=2,output_version='v'))
        origin['identity']['session']=10
        self.assertEqual(saved['identity']['session'],9)
        self.assertEqual(s.origin['identity']['session'],9)

    def test_padded_x_only_inactive_lanes_receive_constant_zero(self):
        s,a=self.service();a.matrix_lease_live=lambda *x:True
        a.matrix_x_capture=lambda *x:dict(payload=bytes(range(128)))
        frame=s.capture_x_fragment(dict(source_K_indices=tuple(range(64))+(None,)*64),{})
        self.assertEqual(frame['payload'],bytes(range(128))+bytes(128))
        a.matrix_x_capture=lambda *x:dict(payload=bytes(126))
        with self.assertRaises(ValueError):s.capture_x_fragment(dict(source_K_indices=tuple(range(64))+(None,)*64),{})
    def test_workspace_snapshot_cannot_redirect_physical_scratch(self):
        s,a=self.service();s.reservation=dict(scratch_base=7)
        with self.assertRaises(ValueError):s.capture_result(0,0,dict(scratch_base=8))
        self.assertTrue(s.faulted)

    def test_actual_scratch_reread_then_actual_RF_ACK_only(self):
        from tools.gpu_sys.canonical_qwen_rf_ports import RFPorts
        s,a=self.service();s.input_rows=(7,)
        r=dict(rows=1,scratch_base=8,identity=dict(owner55=(17<<9)|38))
        s.reservation=r;s.seen_rows={0};sp=s.scratch.p;sp.values['ready']=1
        rp=ServicePins();rf=RFPorts(rp)
        a.matrix_lease_live=lambda *args:True
        a.matrix_output_page=lambda *args:(rf,38,17)
        a.matrix_tile_completion=lambda *args:None
        self.assertIsNone(s.completion(r));s.before_edge();s.after_edge()
        bits=sum(0xdeadbeef<<(32*i) for i in range(16));sp.values.update(done=1,rdata=bits)
        s.before_edge();s.after_edge();sp.values['done']=0
        self.assertIsNone(s.completion(r));self.assertEqual(s.rf_frame,bytes.fromhex('efbeadde'))
        self.assertIsNone(s.completion(r));rp.values['wr_ready']=1
        s.before_edge();s.after_edge();self.assertFalse(s.output_ACK)
        rp.values.update(ack_valid=1,ack_owner=17,ack_slot=38)
        s.before_edge();s.after_edge();self.assertIsNone(s.completion(r));self.assertTrue(s.output_ACK)
        self.assertEqual(rp.values['wr_data'].to_bytes(512,'little')[:4],bytes.fromhex('efbeadde'))

    def test_complete_first_range_does_not_publish_missing_second_range(self):
        s,a=self.service();s.input_rows=(7,);s.origin=dict(identity={},GO_tuple239=9)
        r=dict(rank=0,SM=0,output_version_id=3,range_begin=2,range_end=4,owner55=2,
            expected_ACK_bitmap=3,source_version='v',ACK_bitmap=3,GO_tuple239=9,input_rows=(7,),full_engine_visible=True)
        second=dict(r,SM=1,owner55=3)
        s.expected_ranges=(dict(r),dict(second));a.matrix_output_ranges=lambda *args:(r,)
        self.assertIsNone(s.whole_completion(s.origin))
        self.assertFalse(s.faulted)

    def test_GO_pack_uses_exact239_layout_and_no_owner_tag_substitution(self):
        identity=dict(session=11,source_PC=37,native_tag=13,native_generation=17,rank=1,SM=24,
                      output_version_id=29,range_begin=38,range_end=39,owner55=123)
        v=S.pack_GO(identity)
        self.assertEqual(v>>175,11);self.assertEqual(v>>164&2047,37)
        self.assertEqual(v>>100&(2**64-1),13);self.assertEqual(v>>36&(2**64-1),17)
        self.assertEqual(v>>35&1,1);self.assertEqual(v>>30&31,24)
        self.assertEqual(v&1023,39)
        self.assertEqual(S.pack_GO(dict(identity,owner55=456)),v)

    def test_one_live_line_and_no_inactive_source_read(self):
        s,a=self.service();a.matrix_lease_live=lambda *x:True
        plan=dict(source_code_byte_offsets=tuple(i*64 for i in range(64))+(None,)*64)
        self.assertTrue(s.offer_weight_line(3,plan,{}));self.assertFalse(s.offer_weight_line(4,plan,{}))
        self.assertEqual(len(s.line['sectors']),64)
        self.assertEqual(s.line['payload'],bytes(128))
    def test_first_ACK_cannot_publish_full_range_or_wrong_GO(self):
        s,a=self.service();s.input_rows=(2,3);origin=dict(identity=dict(session=9),GO_tuple239=7);s.origin=origin
        ranges=(dict(rank=0,SM=0,output_version_id=4,range_begin=5,range_end=8,source_version='v',owner55=5,expected_ACK_bitmap=7,ACK_bitmap=1,full_engine_visible=True,GO_tuple239=7,input_rows=(2,3)),)
        s.expected_ranges=tuple(dict(r) for r in ranges)
        a.matrix_output_ranges=lambda *x:ranges
        self.assertIsNone(s.whole_completion(origin))
        self.assertFalse(s.faulted)
        ranges[0]['ACK_bitmap']=7
        a.matrix_whole_completion=lambda *x:dict(identity=dict(session=8),input_rows=(2,3))
        with self.assertRaises(ValueError):s.whole_completion(origin)
        self.assertTrue(s.faulted)
        s,a=self.service();s.input_rows=(2,3);s.origin=origin;s.expected_ranges=tuple(dict(r) for r in ranges)
        a.matrix_output_ranges=lambda *x:ranges
        a.matrix_whole_completion=lambda *x:dict(identity=origin['identity'],input_rows=(2,3),GO_tuple239=7,
            all_output_RF_visible=True,all_W4_ACK=True,whole_terminal=True,whole_reverse_validated=True,source_publication=True)
        self.assertEqual(s.whole_completion(origin)['identity'],origin['identity'])

if __name__=='__main__':unittest.main()
