import copy
from collections import Counter
import unittest
from w19_gpu_norm_calendar import build, calendar, vector_program, scalar_norm_program, bf16_round


class NormCalendar(unittest.TestCase):
    def test_actual_tp96_binding(self):
        c=build()
        self.assertEqual(Counter(x['function'] for x in c['source_graph_binding']),
                         {'hc_pre_norm':80,'final_norm':1,'hc_post':80})
        self.assertIsNone(c['full_cycles']);self.assertFalse(c['physical_qualified'])

    def test_seqsum_and_post_operand_order(self):
        for kind in ['pre','post']:
            adds=[i for i in vector_program(kind) if i['op']=='FADD']
            self.assertEqual([i['src'] for i in adds[:3]],
                             [['p0','p1'],['s1','p2'],['s2','p3']])
            if kind=='post':self.assertEqual(adds[-1]['src'],['yp','mix'])
            self.assertEqual(vector_program(kind)[-1]['attributes']['source_bits'],'31:16')

    def test_bf16_rounding_recipe(self):
        r=bf16_round('x','b')
        self.assertEqual([i['op'] for i in r],['SHR','AND','IADD','IADD','AND'])
        self.assertEqual(r[2]['src'],['x','@U7FFF'])
        self.assertEqual(r[3]['src'],['bias','lsb'])
        self.assertEqual(r[-1]['src'],['rounded','@UFFFF0000'])

    def test_norm_newton_order_and_division(self):
        p=scalar_norm_program()
        self.assertEqual(p[1]['src'],['sum','@F5120'])
        self.assertEqual(p[2]['src'],['mean','@EPS'])
        self.assertEqual([i['op'] for i in p[6:]],['FMUL','FMUL','XOR','FADD','FMUL']*3)
        for i in range(3):self.assertEqual(p[6+5*i+3]['src'],['@FONEHALF','neg'])

    def test_contiguous_power_two_subtrees_match_global_tree(self):
        # Symbolic tree, no tensor arithmetic.20 aligned32-chunk SM subtrees
        # followed by twelvezero subtrees must equal640leaves padded1024.
        def tree(v):
            while len(v)>1:v=[(v[i],v[i+1]) for i in range(0,len(v),2)]
            return v[0]
        chunks=list(range(640))+['zero']*384
        self.assertEqual(tree(chunks),tree([tree(chunks[i:i+32]) for i in range(0,1024,32)]))

    def test_scoreboard_shared_and_rf_limits(self):
        for kind,w in [('pre',8),('post',32)]:
            p=vector_program(kind);s=calendar(p,w)
            self.assertGreaterEqual(s['cycles'],s['shared_issue_cycles'])
            self.assertEqual(s['RF_write_slots'],w*sum(i['dst'] is not None for i in p))
        with self.assertRaises(ValueError):calendar(vector_program('post'),33)
        p=copy.deepcopy(vector_program('pre'));p[-1]['src']=['not_written']
        with self.assertRaisesRegex(ValueError,'unwritten'):calendar(p,8)
        p=copy.deepcopy(vector_program('pre'));p[3]['src']=['@UNKNOWN','x0']
        with self.assertRaisesRegex(ValueError,'unknown'):calendar(p,8)
        p=copy.deepcopy(vector_program('pre'));p[3]['src']=['x0']
        with self.assertRaisesRegex(ValueError,'arity'):calendar(p,8)

    def test_shared_staging_fits_without_free_transport(self):
        c=build()
        self.assertLessEqual(c['allocation']['pre_shared_bytes_per_active_SM'],65536)
        self.assertLessEqual(c['allocation']['post_shared_bytes_per_active_SM'],65536)
        self.assertIsNone(c['norms']['global_tree_transport_cycles'])


if __name__=='__main__':unittest.main()
