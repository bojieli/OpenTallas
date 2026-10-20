import random
import unittest
from collections import Counter
from functools import partial
import test_svc7_bound_graph as reference_tests
from svc7_bound_graph import bound, ReplicationFrontier

class WorklistOriginalCases(reference_tests.GraphTests):
    def setUp(self):
        self.old=reference_tests.bound
        reference_tests.bound=partial(bound,incremental=True)
    def tearDown(self):reference_tests.bound=self.old

class WorklistDifferentialTests(unittest.TestCase):
    def check_result(self,result,limit):
        m,cells,inputs,outputs,origins,clones=result
        loads=Counter()
        for ports in inputs.values():
            for bits in ports.values():
                for bit,inv in bits:
                    if isinstance(bit,int) and bit!=2:loads[bit]+=1
        for bits in outputs.values():
            for bit,inv in bits:
                if isinstance(bit,int):loads[bit]+=1
        self.assertLessEqual(max(loads.values(),default=0),limit)
        self.assertEqual(len(cells)-len(set(origins.values())),clones)

    def test_random_dags_match_reference_frontiers_and_bound_all_roots(self):
        for seed in range(150):
            rng=random.Random(seed)
            ports={'clk':dict(direction='input',bits=[2]),
                   'd':dict(direction='input',bits=list(range(3,11)))}
            cells={}
            available=list(range(3,11))
            for i in range(65):
                out=20+i
                if i%11==0:
                    inputs=dict(CLK=2,D=rng.choice(available))
                    typ='DFF_TEST'
                else:
                    inputs=dict(A=rng.choice(available),B=rng.choice(available))
                    typ='AND_TEST'
                cells['c%d'%i]=reference_tests.cell(typ,inputs,out)
                available.append(out)
            ports['y']=dict(direction='output',bits=[rng.choice(available) for _ in range(9)])
            design={'modules':{'top':dict(ports=ports,cells=cells)}}
            outcomes=[]
            for incremental in (False,True):
                try:
                    result=bound(design,'top',limit=8,incremental=incremental)
                    self.check_result(result,8);outcomes.append('pass')
                except ReplicationFrontier as exc:
                    outcomes.append(exc.report['reason'])
            self.assertEqual(outcomes[0],outcomes[1],seed)

    def test_self_feedback_frontier_refuses_without_clone_growth(self):
        design=reference_tests.design(16)
        design['modules']['top']['cells']['pin']['connections']['D']=[4]
        for incremental in (False,True):
            with self.assertRaisesRegex(ReplicationFrontier,'feedback state/logic'):
                bound(design,'top',4,incremental=incremental)

if __name__=='__main__':unittest.main()
