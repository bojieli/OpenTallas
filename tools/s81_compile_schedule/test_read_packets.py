import unittest
from read_packets import compile_packets


class ReadPacketTests(unittest.TestCase):
    def test_sparse_su_and_hc_same_low_bits_keep_distinct_native_ports(self):
        events=[dict(id=str(i),kind='read',client=client,slot=port,row=row,job=0,tag=1,issue_cycle=10)
                for i,(client,port,row) in enumerate([('su',0,2),('su',1,26),('hc',0,66),('hc',1,90)])]
        result=compile_packets(dict(events=events));packet=result['packets'][0]
        self.assertEqual(len(packet['rows']),4)
        self.assertEqual(len({r['logical_return_slot'] for r in packet['rows']}),4)
        for row in packet['rows']:
            self.assertEqual(row['logical_return_slot']%4,row['row']%4)
            self.assertEqual(row['scatter_packet_slot'],8*(row['row']%4)+row['logical_return_slot']//4)
        self.assertEqual(packet['release_cycle'],20)
        self.assertFalse(result['dispatch_eligible'])

    def test_full16_plus_two_hc_reads_fit_explicit32_slot_profile(self):
        events=[dict(id=f'su{i}',kind='read',client='su',slot=i,row=4096+i,job=0,tag=1,issue_cycle=0) for i in range(16)]
        events += [dict(id=f'hc{i}',kind='read',client='hc',slot=i,row=2+i,job=0,tag=2,issue_cycle=0) for i in range(2)]
        result=compile_packets(dict(events=events))
        self.assertEqual(len(result['packets'][0]['rows']),18)
        self.assertNotIn('insufficient_read_return_lane',[v['kind'] for v in result['violations']])
        self.assertEqual({r['logical_return_slot'] for r in result['packets'][0]['rows'] if r['source_client']=='su'},set(range(16)))

    def test_bank_conflict_cannot_be_hidden_by_packet_permutation(self):
        events=[dict(id=str(i),kind='read',client='su',slot=i,row=32*i,job=0,tag=1,issue_cycle=10) for i in range(2)]
        result=compile_packets(dict(events=events),bank_mapping='rowmod')
        self.assertIn('fixed_read_bank_conflict',[v['kind'] for v in result['violations']])
        self.assertEqual({p['issue_cycle'] for p in result['packets']},{10})


if __name__=='__main__':unittest.main()
