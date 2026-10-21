"""Actual source graph and causal refusals for the complete transport proposal."""
import copy
from pathlib import Path
import tempfile
import unittest
from layer_prog import final_ffn_transport as T
from layer_prog.final_ffn import transfers, verify_moves


class Transport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record=T.model(T.ROOT)
        cls.network=T.Network(T.Die(T.ROOT))

    def test_full_exact_pair_cover(self):
        r=self.record
        actual=[m for p in r['local'] for m in p['members']]
        self.assertTrue(verify_moves(actual))
        self.assertEqual(len(actual),4480)
        self.assertEqual(len(r['local']),1568)
        self.assertEqual(len(r['peers']),480)
        self.assertEqual(r['counts']['peer_payload_bytes'],61440)
        for packet in r['local']:
            first,last=packet['legs'][0],packet['legs'][-1]
            m=packet['members'][0]
            self.assertEqual((first['source'],first['source_leaf'],first['source_row']),
                             (m['source_sid'],m['source_leaf'],m['source_row']))
            self.assertEqual((last['destination'],last['leaf'],last['row']),
                             (m['sid'],m['leaf'],m['row']))
            for left,right in zip(packet['legs'],packet['legs'][1:]):
                self.assertEqual(left['destination'],right['source'])
                self.assertEqual(left['row'],right['source_row'])

    def test_actual_landed_bridges(self):
        for tier in range(2):
            self.assertEqual([x[0] for x in self.network.bridges(tier)],[2,5,6])
        for packet in self.record['local']+self.record['peers']:
            for leg in packet['legs']:
                if leg['kind']=='typed_v_pair_candidate':
                    self.assertIn(leg['source']//2,(2,5,6))
                    self.assertTrue(leg['path'][0]['landed'])
                if leg['kind']=='horizontal':
                    self.assertEqual(leg['source']%2,leg['destination']%2)
                    self.assertTrue(all(len(h['lanes'])==4 for h in leg['path']))

    def test_proposed_pair_word_exact_width(self):
        for leaf in range(5):
            for row in range(0,1024,2):
                data=((1<<255)|((row+17)*(leaf+1)))
                w=T.v_pair(row,leaf,data)
                self.assertLess(w,1<<273)
                self.assertEqual(T.unpack_v_pair(w),(row,leaf,data))
                self.assertNotEqual(T.unpack_v_pair(w^(2<<7)),(row,leaf,data))
        for bad in (T.v_pair(0,0,0)^(1<<273),T.v_pair(0,0,0)^(1<<7)):
            with self.assertRaises(ValueError):T.unpack_v_pair(bad)

    def test_peer_circuits(self):
        count=0
        for packet in self.record['peers']:
            link=next(x for x in packet['legs'] if x['kind']=='end_link')
            delta=(link['destination_rank']-link['source_rank'])%4
            self.assertEqual((link['source'],link['destination']),{1:(14,0),2:(15,1),3:(0,14)}[delta])
            self.assertIsNone(link['arrival_age'])
            count+=1
        self.assertEqual(count,480)

    def test_wrong_missing_duplicate_pairs_refused(self):
        pairs=[m for rank in range(4) for m in transfers(rank)]
        variants=[pairs[:-1],pairs+[pairs[0]]]
        wrong=copy.deepcopy(pairs);wrong[0]['row']+=2;variants.append(wrong)
        owner=copy.deepcopy(pairs);owner[0]['sid']^=1;variants.append(owner)
        for candidate in variants:
            with self.assertRaises(ValueError):verify_moves(candidate)

    def test_phantom_tier_link_refused(self):
        with self.assertRaisesRegex(ValueError,'cannot cross tiers'):
            self.network.horizontal(0,1)

    def test_source_pins(self):
        T.verify_source(T.ROOT,self.record['source_pins'])
        wrong=dict(self.record['source_pins']);wrong[T.SOURCE_PATHS[0]]='0'*64
        with self.assertRaisesRegex(ValueError,'stale'):
            T.verify_source(T.ROOT,wrong)

    def test_arbitrary_calendar_cannot_unlock(self):
        r=self.record
        cases=[({},'source pins'),({'source_pins':r['source_pins']},'unreserved'),
               ({'source_pins':r['source_pins'],'reservations':[1]},'lifetimes'),
               ({'source_pins':r['source_pins'],'reservations':[1],'leases':[1],
                 'qualified':True,'peer_post_age':123},'current source lacks')]
        for binding,message in cases:
            with self.assertRaisesRegex(ValueError,message):T.admit(r,binding)
        self.assertFalse(r['admitted'])
        self.assertEqual(r['ages']['vs13_pin_edges'],75)
        self.assertEqual(r['ages']['post_pin_edges'],63)
        self.assertIsNone(r['ages']['actual_peer_post_arrival'])

if __name__=='__main__':unittest.main(verbosity=2)
