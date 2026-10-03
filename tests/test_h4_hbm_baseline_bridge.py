import gzip,importlib.util,json,pathlib,unittest
P=pathlib.Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bridge',P/'tools/h4_hbm_baseline_bridge.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class BridgeTests(unittest.TestCase):
    def test_secded_exact_codeword(self):
        for word in [0,1,2**64-1,0x0123456789abcdef]+[1<<b for b in range(64)]:
            code=m.secded64(word);data=sum(((code>>(p-1))&1)<<b for b,p in enumerate(m.DATA_POSITIONS));self.assertEqual(data,word)
            self.assertEqual(code.bit_count()%2,0)
            for mask in m.PARITY_MASKS:self.assertEqual((code&mask).bit_count()%2,0)
        for bad in [-1,2**64,True]:
            with self.assertRaises(ValueError):m.secded64(bad)
    def test_exact_compiled_directory_boundary_rows(self):
        src=m.inputs()
        for name in ['Qwen','DS']:
            x=json.loads(gzip.decompress(src[name+'_homes.json.gz']));homes=x['version_homes'] if name=='Qwen' else x
            raw=gzip.decompress((m.BASE/(name+'_directory.bin.gz')).read_bytes());self.assertEqual(len(raw),64*len(homes))
            for index in [0,1,len(homes)//2,len(homes)-1]:self.assertEqual(raw[index*64:(index+1)*64],m.encode_home(homes[index],index,name))
    def test_directory_refuses_unknown_home_rank_lifetime(self):
        h=dict(home={'class':'RF','slot_first':511,'vectors':1},rank=0,SM=0,birth_pc=-1,retire_pc=1736,word_count=128)
        self.assertEqual(len(m.encode_home(h,0,'Qwen')),64)
        for bad in [dict(h,rank=96),dict(h,retire_pc=4096),dict(h,home=dict(h['home'],vectors=2)),dict(h,home={'class':'mystery'})]:
            with self.assertRaises(ValueError):m.encode_home(bad,0,'Qwen')
    def test_connected_directory_gate_corrects_single_refuses_double_and_unknown(self):
        h=dict(home={'class':'RF','slot_first':32,'vectors':1},rank=0,SM=0,birth_pc=5,retire_pc=7,word_count=128)
        raw=m.encode_home(h,0,'Qwen');expected=m.decode_home(raw,rank=0,SM=0,PC=6)
        for bit in range(72):
            changed=bytearray(raw);changed[bit//8]^=1<<(bit%8)
            self.assertEqual(m.decode_home(bytes(changed),rank=0,SM=0,PC=6),expected)
        changed=bytearray(raw);changed[0]^=3
        with self.assertRaises(ValueError):m.decode_home(bytes(changed),rank=0,SM=0,PC=6)
        for args in [dict(rank=1,SM=0,PC=6),dict(rank=0,SM=1,PC=6),dict(rank=0,SM=0,PC=8),dict(rank=0,SM=0,PC=4)]:
            with self.assertRaises(ValueError):m.decode_home(raw,**args)
        native=dict(home={'class':'HBM_NATIVE_STATE','base':32,'bytes':32},rank_group=[0],binding={'PC':5},word_count=8)
        with self.assertRaises(ValueError):m.decode_home(m.encode_home(native,0,'DS'),rank=0,SM=0,PC=6)
    def test_graph_is_acyclic_and_full_audit_coverage(self):
        graph=json.loads((m.BASE/'implementation_graph.json').read_bytes());seen=set()
        for n in graph:self.assertTrue(set(n['depends_on'])<=seen);seen.add(n['id']);self.assertTrue(n['mandatory_baseline']);self.assertFalse(n['implementation_done'])
        self.assertTrue({'W'+str(i) for i in range(1,14)}<=seen)
        gate=next(n for n in graph if n['id']=='BASELINE_GATE');self.assertIn('DS_CONNECT',gate['depends_on'])
    def test_frozen_baseline_is_not_performance_novelty_or_admission(self):
        x=json.loads((m.BASE/'model.json').read_bytes());self.assertTrue(x['frozen']);self.assertFalse(x['performance_opt_in']);self.assertFalse(x['engine_build_ready'])
        self.assertEqual(len(x['latency']['required_positive_events']),21);self.assertEqual(x['owner_gate']['endpoint_entries'],64)
        self.assertEqual(x['default_off_bug']['added_state_bits'],0);self.assertFalse(x['default_off_bug']['installed_fix'])
        self.assertIn('one common ACK',x['common_RF_ACK']['mirrors']);self.assertIsNone(x['latency']['backpressure_waits_ns'])
        for v in x['full_context'].values():self.assertEqual(v['retained_SMs'],32);self.assertFalse(v['fit'])
    def test_actual_consumer_CDC_width_service_and_held_route(self):
        x=json.loads((m.BASE/'model.json').read_bytes());d=x['actual_consumer_delta']
        self.assertTrue(d['generic324bit_identity_rejected']);self.assertEqual(d['physical_tag_candidate_bits'],16)
        self.assertEqual(d['FIFO_candidate']['read_return']['payload_bits_per_entry'],1108)
        self.assertEqual(sum(d['local_gate_fields'].values()),30);self.assertEqual(sum(d['bank_gate_fields'].values()),58)
        self.assertEqual(d['source_route']['minimum_packet_acceptance_spacing_FAST_edges'],40)
        self.assertEqual(d['source_route']['ceiling128PC_1lane_Bpc'],102.4)
        self.assertEqual(d['service']['priced320bit_FIFO_payload_Bpc_3to4'],768)
        self.assertEqual(d['service']['candidate4lane_payload_Bpc_3to4'],3072)
        self.assertTrue(d['onebit_generation_not_admitted']);self.assertFalse(d['W10_RTL_admitted'])
        self.assertEqual(d['source_KV_RMW']['actual_partial_sector_mask_merge_count'],18432)
        self.assertTrue(d['source_KV_RMW']['fullhead128B_RMW_avoidance_not_transferred'])
    def test_bounded_dictionary_and_resource_reconcile(self):
        x=json.loads((m.BASE/'model.json').read_bytes());d=x['directory_schema']['actual_source_statistics']
        self.assertEqual(d['Qwen']['entries'],31232);self.assertEqual(d['DS']['entries'],290730)
        for v in d.values():self.assertEqual(v['dictionary_bytes'],v['entries']*64);self.assertEqual(v['lookup_miss_reads32B'],2);self.assertIsNone(v['directory_base'])
        self.assertEqual(d['DS']['rows_missing_source_SM'],4616);self.assertEqual(d['DS']['rows_missing_source_retirement'],4616)
        self.assertTrue(d['DS']['unknown_field_flags_require_refusal_not_zero_latency'])
        self.assertEqual(len(x['emitted_calendar_join']['missing_physical_phase_costs']),21)
        self.assertEqual(x['emitted_calendar_join']['actual_PC0_transactions'],738816)
        r=x['resource_ledger'];self.assertEqual(r['candidate_control_bits'],x['actual_consumer_delta']['total_candidate_bits'])
        self.assertLess(r['candidate_FF_mux_ECC_area_mm2_ASSUMED'],x['unadopted_wide_tuple_screen']['area_mm2'])
    def test_preserved_pinned_source_defect_and_exact_model_inputs(self):
        src=m.inputs();self.assertIn(b'assign commit_ready=0',src['provider.sv']);x=json.loads((m.BASE/'model.json').read_bytes())
        self.assertEqual(x['source_sha256']['provider.sv'],x['default_off_bug']['original_sha256'])
        self.assertEqual(x['historical_zero_cost_findings'],json.loads(src['hbm_owner_ack_gaps.json'])['zero_cost_flags'])
if __name__=='__main__':unittest.main()
