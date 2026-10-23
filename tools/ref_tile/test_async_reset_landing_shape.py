"""Exact async-assert/two-edge-release shape; raw reset/data trees stay refused."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import textbook_lint as T


def graph(first=1, final=2, loads=10, clock='ck', tied_cell=True):
    s='module top(ck,hck,rst_n,d); input ck,hck,rst_n,d;\n'
    names=['hi']+[f'f{i}' for i in range(first)]+[f'fn{i}' for i in range(first)]
    names += [f'l{i}' for i in range(final)]+[f'ln{i}' for i in range(final)]
    names += [f'q{i}_{j}' for i in range(final) for j in range(loads)]
    s+='wire '+','.join(names)+';\n'
    s+='TIEHIx1_ASAP7_75t_R tie(.H(hi));\n' if tied_cell else "assign hi=1'b1;\n"
    def ff(n,d,q,r='rst_n'):
        return f'DFFASRHQNx1_ASAP7_75t_R {n}(.CLK({clock}),.D({d}),.QN({q}),.RESETN({r}),.SETN(hi));\n'
    for i in range(first):
        s+=ff(f'a{i}','hi',f'fn{i}')+f'INVxp67_ASAP7_75t_R ai{i}(.A(fn{i}),.Y(f{i}));\n'
    for i in range(final):
        s+=ff(f'b{i}',f'f{i%first}',f'ln{i}')+f'INVxp67_ASAP7_75t_R bi{i}(.A(ln{i}),.Y(l{i}));\n'
        for j in range(loads):
            s+=ff(f'c{i}_{j}','d',f'q{i}_{j}',f'l{i}')
    s+='endmodule'
    return T.flatten(T.parse_verilog(s), None)[0]


def proof(g):
    a=T.build(g,None)
    return T.async_two_stage_reset_proof(g,a,'rst_n',g.ports['rst_n'][1])


def cell(g,name):
    return next(c[2] for c in g.cells if c[1]==name)


class AsyncResetLandingShape(unittest.TestCase):
    def test_actual_core_shape_and_literal_high(self):
        for tie in [True,False]:
            p=proof(graph(tied_cell=tie));self.assertTrue(p['pass'],p)
            self.assertEqual((p['first'],p['final'],p['root_loads'],p['edges']), (1,2,3,2))

    def test_actual_hbm_shape_and_clock(self):
        p=proof(graph(final=11,loads=32,clock='hck'))
        self.assertTrue(p['pass'],p);self.assertEqual(p['clock'],'hck')
        self.assertEqual((p['root_loads'],p['first_max_loads'],p['final_max_loads']),(12,11,32))

    def test_legacy_refusal_only_removed_for_exact_shape(self):
        g=graph();r=T.analyse(g,None,dict(T.THRESHOLDS))
        self.assertNotIn('reset_landing',r['refuse'])
        self.assertTrue(r['metrics']['reset_landing'][0]['async_two_stage_proof']['pass'])

    def test_data_and_direct_reset_dependence_rejected(self):
        for name,pin,value in [('a0','D','d'),('b0','D','d'),('c0_0','RESETN','rst_n'),('c0_0','D','rst_n')]:
            g=graph();cell(g,name)[pin]=[g.ports[value][1]]
            self.assertFalse(proof(g)['pass'],(name,pin))

    def test_wrong_clock_polarity_control_and_master(self):
        for name,pin,value in [('a0','CLK','hck'),('b0','CLK','hck'),('a0','SETN','rst_n'),('a0','RESETN','d')]:
            g=graph();cell(g,name)[pin]=[g.ports[value][1]]
            self.assertFalse(proof(g)['pass'],(name,pin))
        g=graph();cell(g,'b0')['D']=cell(g,'a0')['QN'][:]
        self.assertFalse(proof(g)['pass'])
        g=graph();i=next(i for i,c in enumerate(g.cells) if c[1]=='b0')
        g.cells[i]=('DFFASRHQNx2_ASAP7_75t_R',g.cells[i][1],g.cells[i][2])
        self.assertFalse(proof(g)['pass'])

    def test_missing_extra_stage_and_asynchronous_feedback(self):
        self.assertFalse(proof(graph(final=0))['pass'])
        g=graph();cell(g,'b1')['D']=cell(g,'bi0')['Y'][:]
        self.assertFalse(proof(g)['pass'])
        g=graph();cell(g,'a0')['D']=cell(g,'bi0')['Y'][:]
        self.assertFalse(proof(g)['pass'])
        g=graph();cell(g,'a0')['RESETN']=cell(g,'bi0')['Y'][:]
        self.assertFalse(proof(g)['pass'])

    def test_export_orphan_and_fanout_rejected(self):
        g=graph();g.ports['escape']=('output',g.ports['rst_n'][1]);self.assertFalse(proof(g)['pass'])
        for name in ['ai0','bi0']:
            g=graph();g.ports['escape']=('output',cell(g,name)['Y'][0]);self.assertFalse(proof(g)['pass'])
        self.assertFalse(proof(graph(first=2,final=1))['pass'])
        self.assertFalse(proof(graph(final=32))['pass'])
        self.assertFalse(proof(graph(loads=33))['pass'])
        self.assertFalse(proof(graph(loads=0))['pass'])

    def test_bad_final_async_publication_polarity(self):
        g=graph();cell(g,'c0_0')['RESETN']=cell(g,'b0')['QN'][:]
        self.assertFalse(proof(g)['pass'])

    def test_bad_shape_stays_legacy_failure(self):
        g=graph();cell(g,'a0')['D']=[g.ports['d'][1]]
        self.assertIn('reset_landing',T.analyse(g,None,dict(T.THRESHOLDS))['refuse'])


if __name__=='__main__':
    unittest.main()
