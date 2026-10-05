"""Source ordering and controller protocol gates, no arithmetic/hardware claim."""
import unittest
from tools.gpu_sys import canonical_qwen_service_calendar as C
from tools.gpu_sys import canonical_qwen_matrix_loop as M

class Pins:
    def __init__(self):self.values=dict(fault=0,busy=0,req_v=0,rv=0,d_ready=0);self.edges=[]
    def get(self,k):return self.values.get(k,0)
    def set(self,k,v):self.values[k]=v
    def tick(self):self.edges.append(dict(self.values))

class ProtocolServices:
    """Metadata fixture, does not simulate matrix or physical memory."""
    def __init__(self,t):
        self.t=t;self.x=None;self.requests=[];self.response=None;self.receipt=None;self.captures=[]
        self.lease=dict(retained=True,source_PC=t.source_PC,rank=t.weight_rank,row_start=t.row_start,
            input_version=t.input_version,output_version=t.output_version,
            weight_descriptor_sha256=t.weight_descriptor_sha256,identity=dict(session=1,source_PC=t.source_PC,native_tag=2,native_generation=3,
                rank=0,SM=0,owner55=1,output_version_id=4,range_begin=0,range_end=1),GO_captured=True,
            engine_quiescent=True,output_capture_bytes=8192,input_home=('RF',0,0,1))
    def reserve_tile(self,d):return self.lease
    def capture_x_fragment(self,p,r):return self.x
    def offer_weight_line(self,tag,p,r):self.requests.append((tag,p));return True
    def poll_weight_line(self,r):x=self.response;self.response=None;return x
    def capture_result(self,row,data,r):self.captures.append((row,data));return True
    def completion(self,r):return self.receipt
    def release_tile(self,r,c):return True

class MatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native=C.read(C.ROOT/C.PROGRAM);cls.tiles=M.lower_matrix(cls.native,2,enabled=True);cls.t=cls.tiles[0]
    def test_actual_first_matrix_identity_order_and_bounds(self):
        t=self.t
        self.assertEqual((t.source_PC,t.K,t.split,t.chunk,t.groups,t.rows),(2,4096,256,16,2,128))
        self.assertEqual(t.checkpoint_components,tuple(self.native['source_program']['weight_descriptors'][t.weight_key]['checkpoint_sources']))
        self.assertEqual(len(self.tiles),24)
        self.assertEqual(t.line(0)['source_K_indices'][:3],(0,16,32))
        self.assertEqual(t.line(8)['source_K_indices'][:3],(1,17,33))
        self.assertEqual(t.line(128)['source_K_indices'][:3],(2048,2064,2080))
        self.assertEqual(t.line(256)['source_row'],8)
    def test_all_source_codes_once_per_row_and_exact_chunk_order(self):
        t=self.t
        seen={r:[] for r in range(128)}
        for i in range(t.line_count):
            p=t.line(i);seen[p['source_row']].append(p['source_K_indices'])
        for row,vectors in seen.items():
            self.assertEqual(sorted(k for v in vectors for k in v),list(range(t.K)))
            for g in range(t.groups):
                for lane in range(128):
                    actual=[vectors[g*t.chunk+i][lane] for i in range(t.chunk)]
                    leaf=g*128+lane
                    self.assertEqual(actual,list(range(leaf*t.chunk,(leaf+1)*t.chunk)))
    def test_line_identity_survives_layout_cursor_decoding(self):
        for i in range(self.t.line_count):
            self.assertEqual(self.t.line(i)['line_address'],i)

    def test_defaultoff_nonmatrix_changed_program_refused(self):
        with self.assertRaises(ValueError):M.lower_matrix(self.native,2)
        with self.assertRaises(ValueError):M.lower_matrix(self.native,0,enabled=True)
        with self.assertRaises(ValueError):M.lower_matrix(dict(self.native,schema='changed'),2,enabled=True)
    def test_unproved_split64_padding_refused(self):
        op=next(o for o in self.native['operations'] if o['opcode']=='MATRIX' and self.native['source_program']['weight_descriptors'][o['attributes']['weight']]['split']==64)
        with self.assertRaisesRegex(ValueError,'split64'):M.lower_matrix(self.native,op['pc'],enabled=True)
    def test_actual_lm_head_tail64_needs_no_extra_weight_bubbles(self):
        pc=next(o['pc'] for o in self.native['operations'] if o['opcode']=='MATRIX' and self.native['source_program']['weight_descriptors'][o['attributes']['weight']]['rows']==75968)
        tiles=M.lower_matrix(self.native,pc,enabled=True);t=tiles[-1]
        self.assertEqual(t.rows,64)
        self.assertEqual(t.row_start+t.rows,75968)
        self.assertEqual(t.line(t.line_count-1)['source_row'],75967)

    def test_finite_source_model_not_free_owner_or_token_prediction(self):
        x=M.price_tiles(self.tiles,100)
        self.assertEqual(x['weight_line_requests'],3072*4096//128)
        self.assertEqual(x['xstore_write_beats'],24*32*16)
        self.assertEqual(x['native_arithmetic_removed'],0)
        self.assertEqual(x['required_output_capture']['SECDED_64plus8_storage_bits'],73728)
        self.assertFalse(x['physical_admission']);self.assertIsNone(x['composed_token_latency_ps'])
        self.assertIsNone(x['weight_scatter_gather_edges'])
    def test_missing_owned_services_refused(self):
        with self.assertRaises(ValueError):M.MatrixLoopController(Pins(),object(),self.t,enabled=True)
    def controller(self):
        p=Pins();s=ProtocolServices(self.t);v=M.MatrixLoopController(p,s,self.t,enabled=True);return p,s,v
    def test_wrong_source_reservation_refused(self):
        p,s,v=self.controller();s.lease['input_version']='other'
        with self.assertRaises(ValueError):v.step()
    def test_partial_or_wrong_full_issuer_stamp_refused(self):
        p,s,v=self.controller();s.lease['identity']['source_PC']=17
        with self.assertRaises(ValueError):v.step()
        p,s,v=self.controller();del s.lease['identity']['native_generation']
        with self.assertRaises(ValueError):v.step()

    def test_preload_uses_captured_bits_without_host_conversion(self):
        p,s,v=self.controller();v.step();v.step();self.assertEqual(v.phase,'preload')
        s.x=dict(captured=True,dtype='BF16',fragment=0,payload=bytes(range(256)),input_version=self.t.input_version,home=s.lease['input_home'],
                 native_recipe_sha256=self.t.native_recipe_sha256)
        for _ in range(16):v.step()
        beats=[r for r in p.edges if r.get('xw_en')]
        self.assertEqual(len(beats),16)
        self.assertEqual([r['xw_grp'] for r in beats],[0,1]*8)
        self.assertEqual([r['xw_addr'] for r in beats],[i//2 for i in range(16)])
        self.assertTrue(all(r['xw_data'].to_bytes(256,'little')==bytes(range(256)) for r in beats))
    def test_descriptor_held_and_start_once(self):
        p,s,v=self.controller();v.step();v.phase='issue'
        v.step();v.step();p.values['d_ready']=1;v.step();v.step()
        self.assertEqual(sum(r['start'] for r in p.edges),1)
        self.assertEqual([r['d_valid'] for r in p.edges],[0,1,1,1,0])
        self.assertEqual(p.values['op_scale'],0)
    def test_weight_response_requires_retained_tag_and_real_capture(self):
        p,s,v=self.controller();v.step();v.phase='issue';p.values.update(req_v=1,req_tag=7,req_addr=0)
        v.step();p.values['req_v']=0
        s.response=dict(tag=7,line_address=1,payload=bytes(128),captured=True)
        with self.assertRaises(ValueError):v.step()
    def test_busy_idle_is_not_retirement(self):
        p,s,v=self.controller();v.step();v.phase='retire';v.step()
        self.assertEqual(v.phase,'retire')
        s.receipt=dict(source_PC=2,row_start=0,identity=s.lease['identity'],RF_visible=True,W4_ACK=True,W6_retired=True,reverse_validated=False)
        with self.assertRaises(ValueError):v.step()
        s.receipt['reverse_validated']=True;self.assertEqual(v.step(),'done')
    def test_remote_weight_rank_is_not_guessed_execution_rank(self):
        t=M.lower_matrix(self.native,18,enabled=True)[0]
        self.assertEqual(t.weight_rank,1)
        s=ProtocolServices(t);p=Pins();v=M.MatrixLoopController(p,s,t,enabled=True)
        self.assertEqual(s.lease['identity']['rank'],0)
        self.assertEqual(v.step(),'preload')

    def test_whole_completion_requires_all_tiles_and_reverse(self):
        p,s,v=self.controller()
        s.begin_operator=lambda d:dict(identity=s.lease['identity'],GO_captured=True)
        s.whole_completion=lambda origin:s.receipt
        s.release_operator=lambda *args:True
        whole=M.MatrixOperatorController(p,s,self.native,2,enabled=True);whole.step()
        whole.phase='whole_retire'
        s.receipt=dict(identity=s.lease['identity'],tile_count=1,all_output_RF_visible=True,
            all_W4_ACK=True,whole_terminal=True,whole_reverse_validated=True,source_publication=True)
        with self.assertRaises(ValueError):whole.step()
        s.receipt['tile_count']=len(whole.tiles);s.receipt['whole_reverse_validated']=False
        with self.assertRaises(ValueError):whole.step()
        s.receipt['whole_reverse_validated']=True
        self.assertEqual(whole.step(),'done')

    def test_unbackpressured_sink_overflow_refused(self):
        p,s,v=self.controller();v.step();v.phase='issue';p.values.update(rv=1,rrow=0,rdata=0)
        s.capture_result=lambda *args:False
        with self.assertRaisesRegex(ValueError,'finite hardware capture'):v.step()

if __name__=='__main__':unittest.main()
