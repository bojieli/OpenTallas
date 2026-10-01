import unittest
from w19_gpu_attention_dots import build, profile, dot_program


class AttentionDots(unittest.TestCase):
    def test_actual_headowner_graph(self):
        b=build();self.assertEqual(len(b['source_graph_binding']),40)
        self.assertEqual({i['owners'] for i in b['source_graph_binding']},{'heads'})
        self.assertIsNone(b['full_token_cycles']);self.assertFalse(b['physical_qualified'])

    def test_work_fullshape_and_warp_limit(self):
        for n in [128,640]:
            p=profile(n)
            self.assertEqual(sum(w['rows'] for w in p['QK']['waves'])*32,n)
            self.assertEqual(p['QK']['products_per_rank'],n*512)
            self.assertEqual(p['PV']['products_per_rank'],n*512)
            self.assertEqual(sum(w['chunks_per_output'] for w in p['PV']['waves']),n//8)
            for w in p['QK']['waves']+p['PV']['waves']:
                self.assertLessEqual(w['calendar']['resident_warps'],32)
                self.assertLessEqual(w['calendar']['peak_live_value_registers']+8,32)
                self.assertEqual(w['calendar']['RF_read_ports'],2)
                self.assertEqual(w['calendar']['RF_write_ports'],1)

    def test_subwarps_do_not_mix_output_dims(self):
        p=dot_program(16)
        sh=[o['attributes']['offset'] for o in p if o['op']=='SHFL_PAIR']
        self.assertEqual(sh,[1,2,4,8])
        self.assertEqual(p[-1]['attributes']['predicate'],'lane % 16 == 0')
        adds=[o for o in p if o['op']=='FADD']
        self.assertEqual(adds[0]['src'],['@F32_POS_ZERO','p0'])
        with self.assertRaises(ValueError):dot_program(20)

    def test_symbolic_640_tail_tree(self):
        def tree(v):
            while len(v)>1:v=[(v[i],v[i+1]) for i in range(0,len(v),2)]
            return v[0]
        leaves=list(range(80))+['zero']*48
        z16=tree(['zero']*16);z32=tree(['zero']*32)
        self.assertEqual(tree(leaves),(tree(leaves[:64]),((tree(leaves[64:80]),z16),z32)))

    def test_live_both_layouts_and_no_free_transpose(self):
        for n in [128,640]:
            p=profile(n);s=p['staging']
            self.assertLessEqual(s['total_live_bytes_SM'],65536)
            self.assertEqual(s['key_transpose_bytes_rank'],n*512*2)
            self.assertGreater(s['total_live_bytes_SM'],s['source_QK_key_bytes_SM']+s['destination_PV_key_bytes_SM'])
            self.assertIsNone(p['full_attention_cycles'])
            self.assertFalse(p['connected_exactness'])
        with self.assertRaises(ValueError):profile(512)


if __name__=='__main__':unittest.main()
