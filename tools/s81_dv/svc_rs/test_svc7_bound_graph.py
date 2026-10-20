import unittest
from copy import deepcopy
from svc7_bound_graph import bound


def cell(typ,ins,out):
    return dict(type=typ,parameters={},attributes={},
                connections={**{p:[v] for p,v in ins.items()},'Y':[out]},
                port_directions={**{p:'input' for p in ins},'Y':'output'})


def design(n=16):
    cells={'pin':cell('DFF_TEST',dict(CLK=2,D=3),4)}
    for i in range(n):cells['use%d'%i]=cell('AND_TEST',dict(A=4,B=5+i),100+i)
    return {'modules':{'top':dict(
        ports={'clk':dict(direction='input',bits=[2]),
               'd':dict(direction='input',bits=[3]),
               'mask':dict(direction='input',bits=list(range(5,5+n))),
               'y':dict(direction='output',bits=list(range(100,100+n)))},
        cells=cells)}}


class GraphTests(unittest.TestCase):
    def test_register_clones_preserve_data_and_clock(self):
        m,c,ins,out,origins,n=bound(design(), 'top',4)
        self.assertEqual(n,3)
        copies=[name for name in c if origins[name]=='pin']
        self.assertEqual(len(copies),4)
        self.assertTrue(all(ins[name]=={'CLK':[(2,False)],'D':[(3,False)]} for name in copies))
        # Check every output's Boolean function after the first common clock.
        for d in (0,1):
            for mask in (0,0x5555,0xaaaa,0xffff):
                values={2:0,3:d,**{5+i:(mask>>i)&1 for i in range(16)}}
                for name in copies:
                    q=c[name]['connections']['Y'][0];values[q]=d
                for i in range(16):
                    a=values[ins['use%d'%i]['A'][0][0]]
                    self.assertEqual(a & ((mask>>i)&1),d & ((mask>>i)&1))

    def test_port_overflow_fails_without_buffer_waiver(self):
        d=design(17)
        with self.assertRaisesRegex(AssertionError,'unregistered port'):
            bound(d,'top',4)

    def test_inverted_output_and_buffer_alias_survive(self):
        d=design(4)
        m=d['modules']['top']
        m['cells']['inv']=cell('INV_TEST',dict(A=100),200)
        m['cells']['buf']=cell('HB1_TEST',dict(A=200),201)
        m['ports']['y']['bits'][0]=201
        _,cells,_,outputs,_,_=bound(d,'top',4)
        self.assertNotIn('inv',cells);self.assertNotIn('buf',cells)
        self.assertEqual(outputs['y'][0],(100,True))

    def test_clock_distribution_is_not_data_cloned(self):
        d=design(4);m=d['modules']['top']
        for i in range(6):m['cells']['ff%d'%i]=cell('DFF_TEST',dict(CLK=2,D=5+i%4),300+i)
        _,cells,_,_,_,_=bound(d,'top',4)
        self.assertEqual(sum(c['type']=='DFF_TEST' for c in cells.values()),7)

    def test_self_feedback_fails_before_unbounded_cloning(self):
        d=design();d['modules']['top']['cells']['pin']['connections']['D']=[4]
        with self.assertRaisesRegex(AssertionError,'feedback') as caught:
            bound(d,'top',4)
        self.assertEqual(caught.exception.report['clones_so_far'],0)

    def test_feedback_through_logic_also_refuses(self):
        d=design();m=d['modules']['top']
        m['cells']['feed']=cell('AND_TEST',dict(A=4,B=5),400)
        m['cells']['pin']['connections']['D']=[400]
        with self.assertRaisesRegex(AssertionError,'feedback'):
            bound(d,'top',4)


if __name__=='__main__':unittest.main()
