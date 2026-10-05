"""Independent address/lifetime/ownership checks; no native arithmetic claim."""
import collections
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import qwen_hbm_provider_bindings_r17 as B


class ProviderBindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding = B.build()

    def test_all_source_PC_version_and_class_references(self):
        b = self.binding
        self.assertEqual(b['coverage']['PCs'], 1737)
        self.assertEqual(b['coverage']['versions'], 2027)
        self.assertEqual(b['coverage']['opcode_classes'], 21)
        refs = {h['provider_ref'] for h in b['version_homes']+b['control_homes']}
        for op in b['operations']:
            self.assertTrue(all(ref in refs for field in ['inputs','outputs'] for group in op[field].values() for ref in group))
            self.assertTrue(all(x < op['pc'] for x in op['source_dependencies']))
        self.assertFalse(b['hardware_or_rate_qualified'])

    def test_spill_and_provider_state_are_charged_and_disjoint(self):
        for allocation in self.binding['allocation']:
            ext = allocation['extents']; spill = next(e for e in ext if e['name']=='activation_scratch')
            self.assertEqual(spill['base'], 4714740864)
            self.assertEqual(spill['bytes'], 32*1024**2)
            state = next(e for e in ext if e['name']=='KV_provider_state')
            self.assertEqual(state['bytes'], 37504)
            self.assertGreaterEqual(state['base'], spill['base']+spill['bytes'])
            for a,z in zip(ext,ext[1:]):
                self.assertLessEqual(a['base']+a['bytes'],z['base'])
            self.assertLess(allocation['max_stack_allocated_bytes'],allocation['capacity_bytes_per_stack'])

    def test_stripe_decode_is_lossless_including_upper_bits_boundaries(self):
        cases = [0,31,32,127,128,511,512,2**31-1,2**32,4714740864,4748332799,80999999999]
        for byte in cases:
            p = B.physical(byte); local = 32*p['local_sector31']+p['byte_in_sector']
            decoded = 512*(local//128)+128*p['stack']+local%128
            self.assertEqual(decoded,byte)
            self.assertLess(p['local_sector31'],2**31)
        with self.assertRaises(ValueError):B.physical(81000000000)

    def test_every512B_spill_vector_uses16_unique_real_sectors(self):
        base = 4714740864
        sectors = {(B.physical(base+32*i)['stack'],B.physical(base+32*i)['local_sector31']) for i in range(16)}
        self.assertEqual(len(sectors),16)
        self.assertEqual(collections.Counter(s for s,_ in sectors),{0:4,1:4,2:4,3:4})
        self.assertNotEqual(base%512,0)  # source alignment must not be silently changed

    def test_native_RF_words_and_homes_do_not_alias_while_live(self):
        groups=collections.defaultdict(list)
        for h in self.binding['version_homes']:
            p=h['home'];groups[h['rank'],h['SM'],p['class']].append(h)
        for values in groups.values():
            active=[]
            for h in sorted(values,key=lambda x:(x['birth_pc'],x['version'])):
                active=[x for x in active if x['retire_pc']>=h['birth_pc']]
                p=h['home'];lo=p.get('slot_first',p.get('global_byte_base'));size=p.get('vectors',p.get('bytes'))
                for old in active:
                    q=old['home'];a=q.get('slot_first',q.get('global_byte_base'));n=q.get('vectors',q.get('bytes'))
                    self.assertFalse(lo<a+n and a<lo+size)
                active.append(h)
        addresses={tuple(B.rf_address(32,lane)[k] for k in ['page','row','bank','bit_offset']) for lane in range(128)}
        self.assertEqual(len(addresses),128)

    def test_actual_K_token16_and_V_row_coordinate_uniqueness(self):
        for kind in ['K','V']:
            offsets={B.kv_offset(kind,h,p,d) for h in range(4) for p in range(32) for d in range(128)}
            self.assertEqual(len(offsets),4*32*128)
            self.assertLess(max(offsets),4*8192*128)
        self.assertEqual(B.kv_offset('K',0,16,0),2048)
        self.assertEqual(B.kv_offset('V',0,16,0),2048)
        self.assertEqual(B.kv_offset('K',0,1,1),17)
        self.assertEqual(B.kv_offset('V',0,1,1),129)

    def test_epoch_chunk_and_physical_owner_identity_do_not_alias(self):
        args=[3,1736,0,0,5,2,19,1,4714740864]
        old=B.packet_identity(*args)
        for index in [0,2,3,5,6]:
            new=list(args);new[index]+=1
            self.assertNotEqual(old,B.packet_identity(*new))
        self.assertEqual(old['transport'],1736<<21)
        with self.assertRaises(ValueError):B.packet_identity(3,1736,2**21,0,5,2,19,1,4714740864)

    def test_immutable_reads_do_not_charge_codes_again_for_row_scales(self):
        for op in self.binding['operations']:
            if op['opcode'] in ['ROW_SCALE','ALL_REDUCE']:
                self.assertTrue(all('.codes' not in x['provider_ref'] for x in op['external_providers']))
            if op['opcode']=='MATRIX':
                self.assertTrue(all('.scales' not in x['provider_ref'] for x in op['external_providers']))

    def test_reuse_waits_for_causal_release_not_only_PC_bounds(self):
        homes={h['provider_ref']:h for h in self.binding['version_homes']}
        events={h['release_event']:h for h in homes.values()}
        self.assertGreater(len(self.binding['reuse_dependencies']),0)
        for edge in self.binding['reuse_dependencies']:
            prior=events[edge['wait_release']];next_home=homes[edge['new_home']]
            self.assertLess(prior['retire_pc'],next_home['birth_pc'])
            self.assertIn('all reverse validated grants accepted',prior['release_requires'])


if __name__=='__main__':unittest.main()
