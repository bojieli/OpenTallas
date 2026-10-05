import importlib.util
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('production_owner',ROOT/'tools/h4_hbm_production_owner.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.c=m.OwnerController();self.o=(1,0,1,0,0)
        self.kw=dict(die=0,sm=0,bank=0,address=0,size=128,lease=1,reference=9,write=True)
        self.c.acquire(self.o,**self.kw)

    def event(self,event,**kw):
        self.c.event(self.o,die=0,lease=1,reference=9,event=event,**kw)

    def start(self):
        for e in ('all_prior_H1_sinks_drained','bank_request_accepted'):
            self.event(e)
        for ordinal in range(4):
            self.event('bank_word_request_accepted',ordinal=ordinal)
            self.event('bank_word_capture_accepted',ordinal=ordinal)

    def finish(self):
        for e in ('visibility_fence_accepted','consumer_completion_accepted','reverse_lease_grant_accepted'):
            self.event(e)

    def test_both_mirror_ACKs_hold_credit_through_reverse(self):
        self.start();self.event('RF_mirror_ACK_accepted',mirror=1)
        with self.assertRaises(ValueError):self.event('visibility_fence_accepted')
        self.event('RF_mirror_ACK_accepted',mirror=0)
        self.event('visibility_fence_accepted');self.event('consumer_completion_accepted')
        with self.assertRaises(ValueError):self.c.acquire((1,0,2,1,1),**dict(self.kw,sm=1))
        self.event('reverse_lease_grant_accepted')
        self.assertFalse(self.c.sms);self.assertFalse(self.c.banks)

    def test_duplicate_ACK_cannot_publish(self):
        self.start();self.event('RF_mirror_ACK_accepted',mirror=0)
        with self.assertRaises(ValueError):self.event('RF_mirror_ACK_accepted',mirror=0)
        self.assertEqual(self.c.sms[0,0]['phase'],'MIRRORS')

    def test_stale_owner_and_lease_reject(self):
        for change in [dict(lease=2),dict(reference=10),dict(owner=(1,0,2,0,0))]:
            kw=dict(owner=self.o,die=0,lease=1,reference=9,event='all_prior_H1_sinks_drained');kw.update(change)
            with self.assertRaises(ValueError):self.c.event(**kw)

    def test_generation_and_sequence_cannot_reuse(self):
        self.start();self.event('RF_mirror_ACK_accepted',mirror=0);self.event('RF_mirror_ACK_accepted',mirror=1);self.finish()
        with self.assertRaises(ValueError):self.c.acquire(self.o,**self.kw)
        self.c.acquire((2,0,1,0,0),**self.kw)

    def test_same_bank_serializes_different_SM_and_nonoverlapping_ranges(self):
        with self.assertRaises(ValueError):self.c.acquire((1,0,1,1,1),**dict(self.kw,sm=1,address=128))
        self.c.acquire((1,0,1,1,1),**dict(self.kw,sm=1,bank=1))

    def test_distinct_dies_are_explicit(self):
        c=m.OwnerController((0,1));c.acquire(self.o,**self.kw)
        c.acquire((1,0,1,1,0),**dict(self.kw,die=1))
        with self.assertRaises(ValueError):self.c.acquire((1,0,1,1,0),**dict(self.kw,die=1))
        with self.assertRaises(ValueError):m.OwnerController().acquire(self.o,**dict(self.kw,die=None))

    def test_read_still_requires_consume_and_reverse(self):
        c=m.OwnerController();c.acquire(self.o,**dict(self.kw,write=False))
        for e in ('all_prior_H1_sinks_drained','bank_request_accepted'):
            c.event(self.o,die=0,lease=1,reference=9,event=e)
        for ordinal in range(4):
            for e in ('bank_word_request_accepted','bank_word_capture_accepted'):
                c.event(self.o,die=0,lease=1,reference=9,event=e,ordinal=ordinal)
        c.event(self.o,die=0,lease=1,reference=9,event='visibility_fence_accepted')
        with self.assertRaises(ValueError):c.event(self.o,die=0,lease=1,reference=9,event='reverse_lease_grant_accepted')

    def test_out_of_bounds_alignment_and_bitwidth_reject(self):
        for change in [dict(address=262144),dict(address=1),dict(size=512),dict(bank=8),dict(lease=2**64),dict(reference=2**32)]:
            with self.assertRaises(ValueError):m.OwnerController().acquire(self.o,**dict(self.kw,**change))

    def test_source_RF_coordinate_exact_macro_mapping(self):
        for sm in (0,31):
            for copy in (0,1):
                a=(2*sm+copy)*262144+511*512+15*32
                r=m.rf_coordinate(a//32)
                self.assertEqual((r['SM'],r['mirror'],r['page'],r['row'],r['bank']),(sm,copy,3,127,15))
        for bad in (-1,524288,1.5):
            with self.assertRaises(ValueError):m.rf_coordinate(bad)

    def test_exact_archive_and_model_scope(self):
        s=m.inputs();projection=dict(raw_journal_SHA256=m.RAW_SHA,transactions=738816,paired_mirror_write_sectors=246144,publications=[{}]*384)
        x=m.controller_model(projection,s)
        self.assertFalse(x['hardware_admitted']);self.assertFalse(x['engine_build_allowed'])
        self.assertIsNone(x['whole_token_latency_ns'])
        self.assertIsNone(x['finite_wait_contract']['backend_edges'])
        self.assertFalse(x['finite_wait_contract']['provisional_1_1_1_admitted'])
        self.assertTrue(all(r['owner_subset_fits_local_reservation'] for r in x['source_context']))

    def test_no_line_publication_on_first_word_or_unaccepted_capture(self):
        self.event('all_prior_H1_sinks_drained');self.event('bank_request_accepted')
        with self.assertRaises(ValueError):self.event('bank_word_capture_accepted',ordinal=0)
        self.event('bank_word_request_accepted',ordinal=0)
        with self.assertRaises(ValueError):self.event('bank_word_request_accepted',ordinal=1)
        self.event('bank_word_capture_accepted',ordinal=0)
        with self.assertRaises(ValueError):self.event('RF_mirror_ACK_accepted',mirror=0)

    def test_combined_H1_ACK_needs_both_write_edges(self):
        self.start();kw=dict(die=0,lease=1,reference=9,copy0_write_edge=True,
            copy1_write_edge=False,host_ack_valid=True,host_ack_ready=True)
        with self.assertRaises(ValueError):self.c.h1_combined_ACK(self.o,**kw)
        self.c.h1_combined_ACK(self.o,**dict(kw,copy1_write_edge=True));self.finish()

    def test_combined_H1_ACK_after_partial_fence_is_atomic_reject(self):
        self.start();self.event('RF_mirror_ACK_accepted',mirror=1)
        with self.assertRaises(ValueError):self.c.h1_combined_ACK(self.o,die=0,lease=1,reference=9,
            copy0_write_edge=True,copy1_write_edge=True,host_ack_valid=True,host_ack_ready=True)
        self.assertEqual(self.c.sms[0,0]['mask'],2)
        self.assertEqual(self.c.sms[0,0]['phase'],'MIRRORS')

    def test_group_home_join_preserves_actual_translation_gaps(self):
        x=m.group_span_binding(m.inputs())
        self.assertEqual(len(x['source_spans']),512)
        self.assertEqual(x['source_current_RF_translation_differences'],512)
        self.assertEqual(x['output_current_home_index_differences_tiles'],64)
        self.assertFalse(x['production_physical_translation_closed'])
        for r in x['source_spans']:
            self.assertLess(r['source_expected_RF_byte_address'],32*2*262144)
            self.assertFalse(r['physical_RF_match'])

    def test_archived_real_H1_page_row_and_two_copy_accept_source(self):
        source=m.inputs()['RF_source.sv'].decode()
        for text in ('rd_a[8:7]==p','rd_a[6:0]','wr_addr[8:7]==p','wr_addr[6:0]','b<16'):
            self.assertIn(text,source)

    def test_complete_production_projection_pin_and_counts(self):
        p=m.BASE/'final_r5/PC0_projection.json.gz';raw=p.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),m.PROJECTION_SHA)
        x=json.loads(gzip.decompress(raw))
        self.assertEqual({r['rank'] for r in x['rows']},set(range(96)))
        self.assertEqual(x['event_counts']['software_backing_visible'],492288)
        self.assertEqual(x['event_counts']['software_read_capture'],246528)
        self.assertEqual(x['paired_mirror_write_sectors'],246144)
        self.assertEqual(len(x['publications']),384)
        self.assertTrue(all(r['final_live_tags']==0 for r in x['rows']))
        self.assertFalse(x['hardware_ACK_evidence'])

    def test_exact_manifest_and_archive_corruption_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);shutil.copytree(m.BASE/'inputs',p/'inputs')
            raw=(m.BASE/'inputs_manifest.json').read_bytes();(p/'inputs_manifest.json').write_bytes(raw)
            with patch.object(m,'BASE',p):
                self.assertIn('RF_source.sv',m.inputs())
                (p/'inputs/RF_source.sv').write_bytes(b'changed source')
                with self.assertRaisesRegex(ValueError,'exact input hash'):m.inputs()
                (p/'inputs_manifest.json').write_bytes(raw+b' ')
                with self.assertRaisesRegex(ValueError,'input manifest pin'):m.inputs()

    def test_missing_waits_refuse_and_source_ticks_reject(self):
        kw=dict(contenders=8,words=4,drain=None,word_service=None,mirror_ACK=None,
            visibility=None,consumer=None,reverse=None,provenance='actual_port_inventory')
        self.assertIsNone(m.finite_bounds(**kw)['upper_edges'])
        for key in ('drain','word_service','mirror_ACK','visibility','consumer','reverse'):
            kw[key]=(2,'software_ticks','a'*64)
        with self.assertRaises(ValueError):m.finite_bounds(**kw)

    def test_finite_bounds_include_all_credit_hold_terms(self):
        kw=dict(contenders=8,words=4,provenance='source_pin')
        for key in ('drain','word_service','mirror_ACK','visibility','consumer','reverse'):
            kw[key]=(2,'source_model','a'*64)
        x=m.finite_bounds(**kw)
        self.assertEqual(x['credit_hold_upper_edges'],18)
        self.assertEqual(x['completion_upper_edges'],7*19+18)
        self.assertFalse(x['hardware_qualified'])

if __name__=='__main__':unittest.main()
