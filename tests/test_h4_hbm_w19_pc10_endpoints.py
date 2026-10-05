import gzip
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('pc10',ROOT/'tools/h4_hbm_w19_pc10_endpoints.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ProductionEndpointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=m.inputs();cls.model=m.build();cls.homes=m.decoded(cls.s,'homes.json.gz')['homes']

    def provider(self):
        return SimpleNamespace(homes=self.homes,generation=1,locations={})

    def populate_metadata(self,p):
        plan=next(x for x in m.decoded(self.s,'tiles.json.gz') if x['PC']==10)
        for r in range(64):
            indices=[i for i in plan['source_reads'][0]['home_indices'] if r in self.homes[i]['rank_group']]
            p.locations[plan['source_reads'][0]['version'],r]=dict(indices=indices,pc=9,shape=[1024],dtype='float32')

    def test_w19_actual96_distinct_dies_full32SM(self):
        rows=self.model['rank_die_SM'];self.assertEqual(len(rows),3072)
        self.assertEqual({(r['rank'],r['die'],r['SM']) for r in rows},{(r,r,s) for r in range(96) for s in range(32)})

    def test_all96_tiles_real_current_home_refs_and_wholeK(self):
        self.assertEqual(sum(len(x['tiles']) for x in self.model['PC10']),6144)
        self.assertEqual(self.model['source_spans'],49152)
        for row in self.model['PC10']:
            for t in row['tiles']:
                output=t['output'];h=self.homes[output['provider_reference']]
                self.assertEqual(h['version'],'DeepSeek.10.z.68')
                self.assertIn(row['rank'],h['rank_group']);self.assertEqual(output['die'],row['rank'])
                self.assertEqual(len(output['mirror_byte_addresses']),2)
                for r in t['source']:
                    self.assertEqual(r['die'],r['rank']);self.assertEqual(r['matrix_whole_K'],512)
                    self.assertEqual(self.homes[r['provider_reference']]['version'],'DeepSeek.9.zpart.67')
                    self.assertLess(r['mirror_byte_addresses'][1]+512,m.RF_BYTES+1)

    def test_selected_L2_lines_are_real_nonoverlapping_source_macros(self):
        rows=self.model['selected_L2_transient_directory'];self.assertEqual(len(rows),32)
        self.assertEqual(len({r['macro']['name'] for r in rows}),32)
        for r in rows:self.assertEqual(r['word_rows'],list(range(1008,1024)))
        self.assertEqual(self.model['general_L2_capacity_bytes_before']-self.model['general_L2_capacity_bytes_after'],16384)
        self.assertIsNone(self.model['cache_miss_latency_delta'])

    def test_missing_production_PC9_refuses_before_execution(self):
        p=self.provider();a=m.ProductionPC10(p)
        with self.assertRaisesRegex(ValueError,'PC9 production'):a.ready(0)

    def test_synthetic_directory_and_state_fragment_refuse(self):
        with self.assertRaisesRegex(ValueError,'actual production'):m.ProductionPC10(SimpleNamespace(homes=[]))
        p=self.provider();self.populate_metadata(p);a=m.ProductionPC10(p)
        key=next(iter(p.locations));p.locations[key]['kind']='state_fragment'
        with self.assertRaisesRegex(ValueError,'PC9 production'):a.ready(0)

    def test_real_writer_identity_references_current_directory(self):
        p=self.provider();self.populate_metadata(p);a=m.ProductionPC10(p)
        for rank in (0,31,64,95):
            identity=a.ready(rank)
            self.assertEqual(len(identity['home_indices']),32)
            self.assertTrue(all(self.homes[i]['version']=='DeepSeek.10.z.68' for i in identity['home_indices']))

    def test_highlevel_oracle_executor_rejected_before_read(self):
        p=self.provider();a=m.ProductionPC10(p)
        calendar=SimpleNamespace(execute_ds_provider_group128=lambda *a,**k:None)
        with self.assertRaisesRegex(ValueError,'no family oracle'):
            a.execute(SimpleNamespace(provider=p),calendar,rank=0,shared_factory=None,primitive_sources=None)

    def test_source_dtype_rejected(self):
        p=self.provider();self.populate_metadata(p);a=m.ProductionPC10(p)
        next(iter(p.locations.values()))['dtype']='int64'
        with self.assertRaisesRegex(ValueError,'PC9 production'):a.ready(0)

    def test_finite_shared_end_address_exact_opaque_bytes(self):
        from hbm_bound_event_journal_r30 import JournalBudget
        with tempfile.TemporaryDirectory() as t:
            #32 sectors*max8 events*2048B*8 page upper + per-journal overhead.
            budget=JournalBudget(Path(t)/'journal',32*8*2048*8+262144)
            try:
                f=m.ProductionSharedFactory(budget);owner=dict(rank=95,SM=31,PC=10,generation=1,tile=63)
                memory=f(owner);raw=(bytes.fromhex('0000807f00000080')*64)
                memory.transact(65024,write=True,payload=raw,length=512)
                self.assertEqual(memory.transact(65024,write=False,payload=None,length=512),raw)
                self.assertFalse(memory.p.live)
                with self.assertRaises(ValueError):memory.transact(65504,write=False,payload=None,length=512)
                self.assertEqual(memory.extent['base'],m.RF_BYTES+31*65536)
            finally:budget.db.close()

    def test_physical_source_selection_is_not_hardware_admission(self):
        self.assertTrue(self.model['source_mapping_admitted'])
        self.assertFalse(self.model['hardware_admitted']);self.assertFalse(self.model['engine_build_allowed'])
        self.assertEqual(self.model['production_physical_bound_calls'],0)
        self.assertIsNone(self.model['costs']['external_backend_consumer_reverse_edges'])
        self.assertIsNone(self.model['costs']['whole_token_latency_ns'])

    def test_physical_port_counts_charge_unused_RF_payload_and_stage(self):
        c=self.model['movement_count_model']
        self.assertEqual(c['PC10_RF_pair_response_bytes'],2*c['PC10_actual_contributor_payload_bytes'])
        self.assertEqual(c['PC10_shared64_commands'],884736)
        self.assertEqual(c['PC10_shared64_bytes'],56623104)
        self.assertEqual(c['PC9_L2_reference_leaf_edges_per_active_SM'],160)
        self.assertEqual(c['PC10_RF_two_mirror_write_bytes'],6291456)
        self.assertFalse(c['new_L2_stage_cost_inserted_into_calendar'])

    def test_vector_owner_holds_bank_through_all_words_and_mirrors(self):
        c=m.vector_owner_controller([63]);o=(1,9,1,63,0);kw=dict(die=63,lease=1,reference=18)
        c.acquire(o,die=63,sm=0,bank=0,address=261632,size=512,lease=1,reference=18,write=True)
        for e in ('all_prior_H1_sinks_drained','bank_request_accepted'):c.event(o,event=e,**kw)
        for n in range(32):
            desc=c.word_descriptor(o,die=63)
            self.assertEqual((desc['ordinal'],desc['row'],desc['write']),(n,1008+n%16,n<16))
            c.event(o,event='bank_word_request_accepted',ordinal=n,**kw)
            c.event(o,event='bank_word_capture_accepted',ordinal=n,**kw)
            if n==15:
                with self.assertRaises(ValueError):c.event(o,event='RF_mirror_ACK_accepted',mirror=0,**kw)
        c.h1_combined_ACK(o,copy0_write_edge=True,copy1_write_edge=True,host_ack_valid=True,host_ack_ready=True,**kw)
        for e in ('visibility_fence_accepted','consumer_completion_accepted','reverse_lease_grant_accepted'):c.event(o,event=e,**kw)
        self.assertFalse(c.banks)

    def test_vector_reservation_rejects_unselected_range(self):
        c=m.vector_owner_controller([0])
        with self.assertRaises(ValueError):c.acquire((1,9,1,0,0),die=0,sm=0,bank=0,address=0,size=512,lease=1,reference=1,write=True)

    def test_vector_wait_counts_all32_words_no_qualified_placeholder(self):
        waits={k:(2,'source_model','a'*64) for k in ('drain','bank_write32','bank_read32','mirror_ACK','visibility','consumer','reverse')}
        b=m.vector_finite_bounds(3,waits,'selected_physical_port_inventory')
        self.assertEqual(b['credit_hold_upper_edges'],74)
        self.assertEqual(b['completion_upper_edges'],224)
        self.assertFalse(b['hardware_qualified'])
        waits['consumer']=None
        self.assertIsNone(m.vector_finite_bounds(3,waits,'pin')['upper_edges'])

    def test_vector_bound_rejects_software_ticks(self):
        waits={k:(2,'software_ticks','a'*64) for k in ('drain','bank_write32','bank_read32','mirror_ACK','visibility','consumer','reverse')}
        with self.assertRaises(ValueError):m.vector_finite_bounds(3,waits,'pin')

if __name__=='__main__':unittest.main()
