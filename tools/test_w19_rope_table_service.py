import json
import unittest
import numpy as np
import hdc_golden_v41 as V
import w19_rope_table_service as R


class RopeTable(unittest.TestCase):
    def test_offline_row_bits_match_actual_golden_source(self):
        c=json.loads(R.CONFIG.read_text())
        positions=[0,1,1048575,1048576]
        for variant in ['plain','yarn']:
            f=V.rope_freqs(c['rope_head_dim'],c['original_seq_len'] if variant=='yarn' else 0,
                          c['compress_rope_theta'] if variant=='yarn' else c['rope_theta'],
                          c['rope_factor'],c['beta_fast'],c['beta_slow'])
            rows=R.coefficients(c,variant,positions)
            for i,p in enumerate(positions):
                cs=V.rope_cs(f,p)
                self.assertTrue(np.array_equal(rows[i].view(np.uint32),np.concatenate(cs).view(np.uint32)))
        for p in [-1,R.POSITIONS]:
            with self.assertRaises(ValueError):R.coefficients(c,'yarn',[p])

    def test_consumer_replication_and_aperture(self):
        b=R.build();self.assertEqual(b['ownership']['plain_full_replicas'],64)
        self.assertEqual(b['ownership']['yarn_full_replicas'],96)
        self.assertEqual(b['allocation']['required_sector_bits'],27)
        for r in b['allocation']['ranks']:
            expected=2 if r['rank']<64 else 1;self.assertEqual(len(r['regions']),expected)
            end=r['historical_stack_end']
            for reg in r['regions']:
                for s in range(4):self.assertGreaterEqual(reg['base'][s],end[s])
                end=[v+e for v,e in zip(reg['base'],reg['extent'])]
        self.assertIsNone(b['runtime']['service_wait_cycles']);self.assertFalse(b['adopted'])

    def test_finite_two_line_service_and_lastposition(self):
        b=R.build()
        for r in b['allocation']['ranks']:
            for reg in r['regions']:
                for p in [0,1,1048575,1048576]:
                    req=R.requests(reg,p);self.assertEqual(len(req),2)
                    self.assertEqual(sum(x['bytes'] for x in req),256)
                    self.assertNotEqual(req[0]['stack'],req[1]['stack'])
                    for q in req:
                        self.assertLessEqual(q['sectors'],16)
                        self.assertLess(q['sector']+q['sectors'],1<<27)
                with self.assertRaises(ValueError):R.requests(reg,R.POSITIONS)


if __name__=='__main__':unittest.main()
