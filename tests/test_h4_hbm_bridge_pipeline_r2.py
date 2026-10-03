import importlib.util,json,pathlib,unittest
P=pathlib.Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('r2',P/'tools/h4_hbm_bridge_pipeline_r2.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
    def request(self,SM=7):return dict(SM=SM,PC=10,rank=0,generation=2,lease=91,home_id=1,byte_offset=0,byte_count=32,source_port=f'host_rd_valid[{SM}]&&host_rd_ready[{SM}]',source_sha256=m.hashlib.sha256(m.inputs()['wrapper.sv']).hexdigest())
    def pub(self):return dict(home_id=1,rank=0,generation=2,producer_PC=5,published_bytes=32,visibility_accepted=True,read_lease=91)
    def native(self):return m.codec().encode_home(dict(home={'class':'HBM_NATIVE_STATE','base':33554432,'bytes':32},rank_group=[0],binding={'PC':5},word_count=8),0,'DS')
    def test_HBM_no_fixed_SM_retire_required_actual_requester(self):
        result=m.directory_admit(self.native(),self.request(),self.pub());self.assertEqual(result['requester_SM'],7);self.assertFalse(result['home_SM_required']);self.assertFalse(result['hardware_admitted'])
        with self.assertRaises(ValueError):m.directory_admit(self.native(),{},self.pub())
        with self.assertRaises(ValueError):m.directory_admit(self.native(),dict(self.request(),source_port='home.SM=0'),self.pub())
    def test_persistent_publication_generation_readlease_checked(self):
        for bad in [dict(self.pub(),generation=1),dict(self.pub(),read_lease=90),dict(self.pub(),published_bytes=64),dict(self.pub(),producer_PC=6),dict(self.pub(),visibility_accepted=False)]:
            with self.assertRaises(ValueError):m.directory_admit(self.native(),self.request(),bad)
    def test_RF_static_SM_lifetime_preserved_not_persistent_rule(self):
        raw=m.codec().encode_home(dict(home={'class':'RF','slot_first':0,'vectors':1},rank=0,SM=7,birth_pc=5,retire_pc=10,word_count=128),0,'Qwen')
        self.assertTrue(m.directory_admit(raw,self.request())['home_SM_required'])
        for req in [self.request(0),dict(self.request(),PC=11)]:
            with self.assertRaises(ValueError):m.directory_admit(raw,req)
    def test_pipeline_actual38edges_one_per_edge_each_lane(self):
        result=m.cadence();self.assertEqual(result['first_delivery_edge'],38);self.assertEqual(result['steady_deliveries_per_lane'],result['steady_window_edges']);self.assertEqual(result['observed_payload_Bpc_die'],4096)
    def test_pipeline_3to4_exact_cadence(self):
        r=m.cadence(ratio=True);self.assertEqual(r['steady_deliveries_per_lane'],r['steady_window_edges']*3//4);self.assertEqual(r['observed_payload_Bpc_die'],3072)
    def test_stalled_lane_fills_finite_seats_no_other_lane_block(self):
        p=m.ElasticPipeline(38,4);ids=[0]*4;accepted=[0]*4;outs=[0]*4
        for edge in range(160):
            r=p.step([(l,ids[l]) for l in range(4)],[False,True,True,True])
            for l in range(4):
                if r['accepted'][l]:ids[l]+=1;accepted[l]+=1
                if r['delivered'][l]is not None:outs[l]+=1
        self.assertEqual(accepted[0],76);self.assertEqual(outs[0],0);self.assertEqual(outs[1:], [122]*3)
        seen=[]
        for edge in range(90):
            r=p.step([None]*4,[True]*4)
            if r['delivered'][0]is not None:seen.append(r['delivered'][0][1])
        self.assertEqual(seen,list(range(76)));self.assertEqual(p.occupancy(),0)
    def test_empty_pipeline_is_not_parent_retirement(self):
        p=m.ElasticPipeline(4,1);o=m.ParentLeases();o.reserve(1,1);p.step([(1,0)],[True])
        for e in range(4):r=p.step([None],[True])
        self.assertEqual(r['delivered'][0],(1,0));self.assertEqual(p.occupancy(),0);o.deliver(1,0)
        with self.assertRaises(ValueError):o.reserve(2,1)
        with self.assertRaises(ValueError):o.reverse(1,0)
        o.ACK(1);o.consume(1,0);o.reverse(1,0)
        with self.assertRaises(ValueError):o.reserve(1,1)
        o.reserve(2,1)
    def test_common_ACK_complete_delivery_and_all_reverse(self):
        o=m.ParentLeases();o.reserve(1,4)
        for b in range(3):o.deliver(1,b)
        with self.assertRaises(ValueError):o.ACK(1)
        o.deliver(1,3);o.ACK(1)
        for b in range(4):o.consume(1,b)
        for b in range(3):o.reverse(1,b)
        self.assertIn(1,o.live);o.reverse(1,3);self.assertEqual(o.live,{})
    def test_model_replaces_old_pipeline_prices_coded_wires_no_fit(self):
        x=json.loads(m.outputs()['model.json']);self.assertEqual(x['directions']['return']['coded_bits_per_lane'],360)
        self.assertEqual(x['directions']['return']['bit_boundary_per_SM'],1448);self.assertFalse(x['engine_build_ready'])
        self.assertEqual(x['replacement_incremental_bits'],x['total_pipeline_protected_bits']-x['predecessor_single_seat_pipeline_bits'])
        self.assertTrue(x['directory_policy']['actual_appended4616_missing_SM_or_retire_is_not_itself_invalid'])
        self.assertIsNone(x['latency']['whole_operator_ns'])
    def test_owned_RFACK_stale_tag_rejected_and_lease_held_until_reverse(self):
        o=m.OwnedRFACK(7);o.write_go(1,32,91,copy0_edge=10,copy1_edge=10)
        with self.assertRaises(ValueError):o.ACK(2,32,91,valid=True,ready=True,edge=11)
        self.assertFalse(o.ACK(1,32,91,valid=True,ready=False,edge=11));self.assertTrue(o.ACK(1,32,91,valid=True,ready=True,edge=12))
        with self.assertRaises(ValueError):o.write_go(2,33,92,copy0_edge=13,copy1_edge=13)
        for e in ['visibility','consumer','reverse']:o.advance(1,91,e)
        o.write_go(2,33,92,copy0_edge=14,copy1_edge=14)
    def test_positive_ACK_CDC_composer_no_zero_or_omitted_term(self):
        b=m.source_bindings();rows=[dict(id=k,kind=k,owner='source-lease',duration_edges=b[k]['minimum_provisional_FAST_edges'],source_sha256=b[k]['source_sha256'],origin='provisional_source_model') for k in m.COSTS]
        result=m.compose(rows+[rows[0]]);self.assertEqual(result['unique_occurrences'],len(m.COSTS));self.assertFalse(result['hardware_admitted'])
        for bad in [rows[:-1],[dict(r,duration_edges=0) for r in rows],[]]:
            with self.assertRaises(ValueError):m.compose(bad)
        for bad in [[dict(r,duration_edges=1) for r in rows], [dict(r,source_sha256=b['owner_grant']['source_sha256']) for r in rows]]:
            with self.assertRaises(ValueError):m.compose(bad)
        self.assertEqual(result['provisional_edge_sum'],84)
    def test_source_attachment_actual_RF_and_CDC_leaves_not_installed_owner(self):
        b=m.source_bindings();src=m.inputs()
        self.assertIn(b'if(write_go) begin ack_valid<=1',src['rf.sv'])
        self.assertEqual(src['rf.sv'].count(b'.w_ce_in(write_go && wr_addr[8:7]==p)'),2)
        self.assertIn(b'.EDGES(38)',src['bridge.sv']);self.assertIn(b'wgr1<=wg;wgr2<=wgr1',src['fifo.sv'])
        self.assertEqual(b['CDC_forward']['CDC_receiver_sync_edges_each'],2)
        self.assertIsNone(b['CDC_return']['actual_clock_pair'])
        self.assertFalse(b['ACK_identity_match']['leaf_exists'])
        self.assertTrue(all(not r['connected_owner_installed'] for r in b.values()))
    def test_exact_outputs(self):
        for n,v in m.outputs().items():self.assertEqual((m.BASE/n).read_bytes(),v)
if __name__=='__main__':unittest.main()
