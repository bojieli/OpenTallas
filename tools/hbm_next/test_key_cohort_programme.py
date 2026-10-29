import copy
import unittest
from key_cohort_programme import compile_allocation


def fixture():
    # Explicit synthetic addresses/deadlines are a compiler mechanism vehicle,
    # never a production HBM allocation or a service completion measurement.
    a=dict(schema='opentallas.hbm_idx.key_cohort_allocation.v1',physical_stack=2,slots=4,
           packet_from_go_edges=4,relay_cycles=3,go_done_tail_edges=10,query_start_at=4000,programme_base=32,descriptor_base=16,occupied_programme_ranges=[[0,32]],occupied_descriptor_ranges=[[0,16]],cohorts=[])
    for c in range(2):
        groups=[]
        for lane in range(8):
            blocks=[]
            for b in range(3):
                go=401+c*1500+b*400+lane%4
                blocks.append(dict(row_base=100+c,slot=b,epoch=100+c*10+b,go_at=go,cache_ready_by=go-20))
            groups.append(dict(lane=lane,blocks=blocks))
        a['cohorts'].append(dict(id=c,groups=groups))
    return a


class KeyProgramme(unittest.TestCase):
    def test_complete_distinct_cohorts_and_actual_issuer_fields(self):
        r=compile_allocation(fixture())
        self.assertFalse(r['installable'])
        self.assertEqual(len(r['ingest_timeline']),2736)
        self.assertEqual(r['programme_word_count'],4)
        self.assertEqual({x['consumer'] for x in r['ingest_timeline']},{'hb_idx__s_SW','hb_idx__s_SE','hb_idx__s_NW','hb_idx__s_NE'})
        for lane in range(8):
            records=r['source_groups'][f'svg_NW{lane}']
            self.assertEqual(len(records),6)
            for x in records:
                w=int(x['descriptor_word'],16)
                self.assertEqual(w>>240,0x5d15)
                self.assertEqual((w>>30)&3,2)
                self.assertEqual((w>>232)&255,x['descriptor'])
                self.assertEqual((w>>72)&1023,(lane*128+x['first_row'])%1024)
                self.assertEqual((w>>119)&((1<<24)-1),x['go_at'])
                self.assertFalse(x['arithmetic_issue'])
                self.assertEqual((w>>103)&65535,x['rows'])
                self.assertEqual((w>>191)&15,1)
                self.assertEqual(x['programme_runtime_edges'],4*x['rows'])
        # Shape words must have packet expectation without any SM arithmetic
        # command or SM request. This preserves the existing request checker.
        for h in r['programme_words']:
            w=int(h,16)
            self.assertEqual((w>>25)&1,0)
            self.assertEqual((w>>40)&((1<<43)-1),0)

    def test_distributed_paths_align_final_slots_and_reject_node_collisions(self):
        a=fixture()
        for c in a['cohorts']:
            for g in c['groups']:
                lane=g['lane'];p=lane%4
                g['path']=[dict(node=f'hub{lane//4}_node{n}',cycles=1) for n in range(p,4)]
                for b,x in enumerate(g['blocks']):
                    x['go_at']=400+c['id']*1500+b*400+2*p
                    x['cache_ready_by']=x['go_at']-20
        r=compile_allocation(a)
        self.assertTrue(all(x['arrival_edge']%4==x['lane'] for x in r['ingest_timeline']))
        self.assertEqual(len({(x['physical_lane']//4,x['arrival_edge']) for x in r['ingest_timeline']}),2736)
        a['cohorts'][0]['groups'][0]['path'][2]['node']='hub0_node1'
        with self.assertRaisesRegex(ValueError,'named distributed path node'):compile_allocation(a)

    def test_rejects_alias_late_go_bad_slot_or_early_query(self):
        for mutation in ('alias','late','slot','query','missing','programme_overlap','descriptor_overlap','capacity'):
            a=fixture()
            if mutation=='alias':a['cohorts'][1]['groups'][0]['blocks'][0]['row_base']=100
            if mutation=='late':a['cohorts'][0]['groups'][0]['blocks'][0]['cache_ready_by']=401
            if mutation=='slot':a['cohorts'][0]['groups'][1]['blocks'][0]['go_at']+=1
            if mutation=='query':a['query_start_at']=400
            if mutation=='missing':a['cohorts'][0]['groups'].pop()
            if mutation=='programme_overlap':a['occupied_programme_ranges'].append([34,40])
            if mutation=='descriptor_overlap':a['occupied_descriptor_ranges'].append([20,24])
            if mutation=='capacity':a['programme_base']=2046
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):compile_allocation(a)

if __name__=='__main__':unittest.main()
