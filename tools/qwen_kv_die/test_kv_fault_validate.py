import copy
import unittest
import kv_fault_validate as V


class ValidateTests(unittest.TestCase):
    def fixture(self):
        sources=[dict(id='a',pin_xy=[0,0],clock='c'),dict(id='b',pin_xy=[0,30],clock='c')]
        inv=dict(sources=sources,physical_obstacles=[[490,490,500,500]],spare_transport_candidates=[],consumer=dict(clock='c',pin_xy=[200,10]))
        n=lambda id,a,b,kind,x:dict(id=id,a=a,b=b,kind=kind,master='qkd_astk_fault_join',latency=1,clock='c',placement=dict(x=x,y=0,orient='R0'))
        plan=dict(sources=copy.deepcopy(sources),nodes=[n('j','a','b','join',50),n('s','j','s','sticky',100)],transports=[],sink='s',retirement_quiet_cycles=2,max_leaf_latency_bound=2)
        return inv,plan
    def test_complete_graph_and_geometry(self):
        inv,plan=self.fixture();r=V.validate(inv,plan)
        self.assertEqual(r['leaf_latencies'],{'a':2,'b':2})
    def test_missing_source_is_rejected(self):
        inv,plan=self.fixture();plan['nodes'][0]['b']='a'
        with self.assertRaisesRegex(ValueError,'missing real source'):V.validate(inv,plan)
    def test_overlap_is_rejected(self):
        inv,plan=self.fixture();plan['nodes'][1]['placement']['x']=50
        with self.assertRaisesRegex(ValueError,'overlapping'):V.validate(inv,plan)
    def test_long_edge_is_rejected(self):
        inv,plan=self.fixture();plan['nodes'][0]['placement']['x']=450
        with self.assertRaisesRegex(ValueError,'long data edge'):V.validate(inv,plan)
    def test_undeclared_crossing_is_rejected(self):
        inv,plan=self.fixture();plan['nodes'][0]['clock']='other'
        with self.assertRaisesRegex(ValueError,'untimed clock crossing'):V.validate(inv,plan)
    def test_insufficient_quiet_is_rejected(self):
        inv,plan=self.fixture();plan['retirement_quiet_cycles']=1
        with self.assertRaisesRegex(ValueError,'underpriced'):V.validate(inv,plan)


if __name__=='__main__':unittest.main()
