import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('connector_r7_tests',ROOT/'tools/h3_complete_native_calendar_source_connector_r7.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ConnectorTests(unittest.TestCase):
    def setup_parent(self, expected=0xffff, die=0):
        x=m.ConnectorOwners(die=die)
        native=dict(owner64=(1<<63)+17,generation64=(1<<63)+25,program_PC=9,rank=die,SM=1,
                    versions=['qwen.native.v7'],home='retained.home.r17',lease='explicit.directed.lease')
        owner=m.R6.owner46(7,5,0xfeedbeef,6)
        x.bind_parent(ref=91,native=native,owner46=owner,SM=1,RF_slot=43,base=0,expected=expected)
        return x,91,(owner<<9)|43

    def allocate(self,x,ref,index,tag12=None,backend_gen4=10,provider_class=2):
        p=m.physical(index*32)
        legacy=dict(die=x.die,stack=p['stack'],sector=p['local_sector31'],producer=(1<<63)+101,
                    transport=0xffff0000+index,caller=index,provider_class=provider_class,IRSslot=5,IRSserial=0xffff0010)
        owner=m.R6.owner46(p['physical_PC'],5,0xabcde000+index,6)
        r=x.allocate_child(ref=ref,owner46=owner,first=index,sectors=1,tag12=index if tag12 is None else tag12,
                           backend_gen4=backend_gen4,context_index=index%4,legacy=legacy)
        return r,legacy

    def capture(self,x,r,legacy,index,**updates):
        args=dict(die=x.die,stack=legacy['stack'],backend_token16=r['backend_token16'],source_meta92=r['source_meta92'],
                  beat=0,legacy=legacy,payload=bytes([index])*32)
        args.update(updates)
        return x.capture(**args)

    def ready(self):
        x,ref,parent55=self.setup_parent();children=[]
        for index in range(16):
            r,legacy=self.allocate(x,ref,index);children.append((r,legacy,index))
            self.assertEqual(self.capture(x,r,legacy,index),parent55)
        image=x.frame(ref);pair=x.write_both_copies(ref,parent55)
        self.assertEqual(pair,(image,image));x.common_ACK(ref,parent55);x.visible(ref,parent55);x.consume(ref,parent55)
        return x,ref,parent55,children

    def reverse(self,x,r,legacy,parent55,**updates):
        args=dict(die=x.die,stack=legacy['stack'],backend_token16=r['backend_token16'],source_meta92=r['source_meta92'],beat=0,owner55=parent55)
        args.update(updates);x.child_reverse(**args)

    def test_source_address_and_512B_stripe_inverse_no_low7_overwrite(self):
        p=m.physical(32)
        self.assertEqual(p['physical_PC'],0);self.assertEqual(p['system_sector34']&127,1)
        self.assertEqual([c['physical_PC'] for c in m.split_frame(0)],[0,32,64,96])
        self.assertEqual([c['first'] for c in m.split_frame(0)],[0,4,8,12])
        for b in (0,31,32,127,128,511,512,1048608):
            r=m.physical(b);local=r['local_sector31']*32+r['byte_in_sector']
            self.assertEqual((local//128)*512+r['stack']*128+local%128,b)

    def test_parent55_is_from_bound_ref_not_last_child_and_native64_unchanged(self):
        x,ref,parent55=self.setup_parent();r,legacy=self.allocate(x,ref,15,provider_class=8)
        self.assertEqual(x.parents[ref]['native']['owner64'],(1<<63)+17)
        self.assertEqual(x.parents[ref]['native']['generation64'],(1<<63)+25)
        self.assertNotEqual((x.children[(legacy['stack'],r['backend_token16'])]['owner46']<<9)|43,parent55)
        self.assertEqual(self.capture(x,r,legacy,15),parent55)
        self.assertEqual(x.children[(legacy['stack'],r['backend_token16'])]['legacy']['provider_class'],8)
        self.assertEqual(r['source_meta92']&0xffffffff,ref)
        self.assertEqual(len(x.local_W2_keys),0)
        self.assertEqual(len(x.children),1)

    def test_high4_truncation_mutant_and_independent_generations_fail_closed(self):
        x,ref,_=self.setup_parent();r,legacy=self.allocate(x,ref,0)
        self.assertEqual(r['backend_token16']>>12,10)
        self.assertEqual((r['source_meta92']>>46)&15,6)
        with self.assertRaises(ValueError):
            self.capture(x,r,legacy,0,backend_token16=r['allocated_tag12'])
        self.assertTrue(x.fault);self.assertEqual(len(x.children),1)
        self.assertFalse(x.parents[ref]['captured'])

    def test_meta_wrong_parent_wrong_die_beat1_and_FP8_do_not_capture(self):
        for mutant in ('meta','die','beat','format'):
            with self.subTest(mutant=mutant):
                x,ref,_=self.setup_parent();r,legacy=self.allocate(x,ref,0)
                change={'meta':dict(source_meta92=r['source_meta92']^1),'die':dict(die=1),
                        'beat':dict(beat=1),'format':dict(payload_format='FP8_unconverted')}[mutant]
                with self.assertRaises(ValueError):self.capture(x,r,legacy,0,**change)
                self.assertEqual(len(x.children),1);self.assertFalse(x.parents[ref]['captured'])

    def test_LEN4_not_W2_sector_contract(self):
        x,ref,_=self.setup_parent();r=m.physical(0)
        legacy=dict(die=0,stack=0,sector=0,producer=1,transport=1,caller=0,provider_class=2,IRSslot=1,IRSserial=1)
        with self.assertRaises(ValueError):
            x.allocate_child(ref=ref,owner46=m.R6.owner46(r['physical_PC'],5,1,6),first=0,sectors=4,
                             tag12=0,backend_gen4=10,context_index=0,legacy=legacy)
        self.assertFalse(x.children)

    def test_complete_frame_old_tail_and_no_zero_fill(self):
        x,ref,p=self.setup_parent(expected=1);r,legacy=self.allocate(x,ref,0)
        self.capture(x,r,legacy,0)
        with self.assertRaises(ValueError):x.frame(ref)
        old=bytes(range(256))*2;x.preserved_RF_read(ref,old*2)
        self.assertEqual(x.frame(ref),bytes(32)+old[32:])
        with self.assertRaises(ValueError):x.preserved_RF_read(ref,old*2)
        full,ref,p,children=self.ready()
        self.assertEqual(full.frame(ref),b''.join(bytes([i])*32 for i in range(16)))
        self.assertEqual(len(full.children),16)
        self.assertFalse(full.local_W2_keys)

    def test_full_quarantine_wrong_reverse_and_positive_drain(self):
        x,ref,p,children=self.ready()
        r,legacy,index=children[0]
        with self.assertRaises(ValueError):self.reverse(x,r,legacy,p,direction=True)
        self.assertTrue(x.fault);self.assertEqual(len(x.children),16)
        x,ref,p,children=self.ready()
        for r,legacy,index in children:self.reverse(x,r,legacy,p)
        self.assertEqual(len(x.children),16)
        x.parent_reverse_CDC(ref,p)
        with self.assertRaises(ValueError):x.release_after_model_drain(ref,positive_wait_edges=0,receipt=x.prospective_drain_receipt(ref))
        self.assertEqual(len(x.children),16)
        x.release_after_model_drain(ref,positive_wait_edges=8,receipt=x.prospective_drain_receipt(ref))
        self.assertFalse(x.children);self.assertFalse(x.contexts);self.assertFalse(x.parents)

    def test_early_return_accept_and_reset_do_not_free_physical_tag(self):
        x,ref,p=self.setup_parent();r,legacy=self.allocate(x,ref,0);self.capture(x,r,legacy,0)
        with self.assertRaises(ValueError):self.allocate(x,ref,1,tag12=0)
        x.begin_reset()
        self.assertEqual(len(x.children),1)
        with self.assertRaises(ValueError):self.allocate(x,ref,1)

    def test_source_scope_die_and_duplicate_exact_logical_key(self):
        x,ref,p=self.setup_parent(die=1);r,legacy=self.allocate(x,ref,0);self.capture(x,r,legacy,0)
        self.assertEqual(legacy['die'],1)
        with self.assertRaises(ValueError):self.allocate(x,ref,0)
        self.assertEqual(len(x.children),1)

    def test_staging_one_credit_two_sectors_and_retained_frame_reverse(self):
        x,ref,p=self.setup_parent()
        for fragment in range(8):
            x.begin_fragment(ref,fragment,source_fragment_sequence64=(1<<63)+fragment)
            with self.assertRaises(ValueError):x.begin_fragment(ref,(fragment+1)%8,source_fragment_sequence64=fragment+1)
            for index in (2*fragment,2*fragment+1):
                r,legacy=self.allocate(x,ref,index);self.capture(x,r,legacy,index)
            with self.assertRaises(ValueError):x.release_staging_credit(ref,fragment)
            x.stage_store_ACK(ref,fragment,b''.join(bytes([i])*32 for i in (2*fragment,2*fragment+1)))
            x.release_staging_credit(ref,fragment)
            self.assertEqual(len(x.children),2*(fragment+1))
            self.assertEqual(len(x.parents[ref]['tickets']),fragment+1)
        self.assertEqual(len(x.frame(ref)),512)
        self.assertEqual(len(x.parents[ref]['tickets']),8)
        self.assertEqual(len(x.children),16)
        self.assertFalse(x.local_W2_keys)

    def test_source_credit_held_to_full_frame_ACK_is_deadlock(self):
        x,ref,p=self.setup_parent();x.begin_fragment(ref,0,source_fragment_sequence64=0)
        for index in (0,1):
            r,legacy=self.allocate(x,ref,index);self.capture(x,r,legacy,index)
        self.assertEqual(sum(len(v) for v in x.parents[ref]['captured'].values()),64)
        with self.assertRaises(ValueError):x.begin_fragment(ref,1,source_fragment_sequence64=1)
        with self.assertRaises(ValueError):x.write_both_copies(ref,p)
        self.assertEqual(len(x.children),2)

    def test_wrong_ACK_origin_and_stale_drain_cohort_retain_all_tags(self):
        x,ref,p=self.setup_parent()
        for index in range(16):
            r,legacy=self.allocate(x,ref,index);self.capture(x,r,legacy,index)
        x.write_both_copies(ref,p)
        with self.assertRaises(ValueError):x.common_ACK(ref,p,origin='internal_SIMD')
        self.assertEqual(x.parents[ref]['phase'],'ACK')
        x,ref,p,children=self.ready()
        for r,legacy,index in children:self.reverse(x,r,legacy,p)
        x.parent_reverse_CDC(ref,p)
        receipt=x.prospective_drain_receipt(ref)
        bad=json.loads(json.dumps(receipt));bad['zero_debts']['forward_return_reverse_CDC']=1
        with self.assertRaises(ValueError):x.release_after_model_drain(ref,positive_wait_edges=8,receipt=bad)
        x.begin_reset()
        with self.assertRaises(ValueError):x.release_after_model_drain(ref,positive_wait_edges=8,receipt=receipt)
        self.assertEqual(len(x.children),16)

    def test_calendar_source_services_not_128_free_backends_and_cost_freeze(self):
        raw=m.model_outputs();model=json.loads(raw['model.json']);runs=json.loads(gzip.decompress(raw['calendars.json.gz']))
        self.assertEqual(model['W10_missing_sideband_raw_bits'],50)
        self.assertEqual(model['cost_inputs']['pipeline_two_seats_38stages_144lanes_increment_bits'],1575936)
        self.assertEqual(model['W2_composition']['W2_model_costs']['full_wrapper_variant']['protected_state_bits_per_PC'],9144)
        self.assertEqual(model['W6_local_edges_counted_once'],19)
        self.assertEqual(model['allocator_lower_inventory']['gross_raw_bits'],93748)
        self.assertEqual(model['allocator_lower_inventory']['gross_protected_bits'],117936)
        self.assertEqual(model['W6_component']['table']['raw_bits_per_SM'],71)
        self.assertTrue(model['p_wr_done_ready_REQUIRED']);self.assertIsNone(model['matched_prior_W2_debit'])
        self.assertFalse(model['whole_program_composed']);self.assertFalse(model['hardware_admitted'])
        times=[]
        for bound in (8,64,256):
            run=runs['held.bound'+str(bound)];times.append(run['last_retire'])
            self.assertEqual(sum(e['kind']=='R14_lookup' for e in run['events']),64)
            self.assertEqual(sum(e['kind']=='R14_return_arb' for e in run['events']),64)
            self.assertEqual(sum(e['kind']=='command_bus' for e in run['events']),64)
            self.assertEqual(sum(e['kind']=='W2_restore' for e in run['events']),64)
            self.assertEqual(sum(e['kind']=='response_capture' for e in run['events']),64)
            self.assertTrue(all(j['R14_LEN']==1 and j['R14_BEAT']==0 for j in run['jobs']))
            for e in run['events']:
                self.assertGreater(e['duration'],0)
        self.assertLess(times[0],times[1]);self.assertLess(times[1],times[2])

if __name__=='__main__':unittest.main()
