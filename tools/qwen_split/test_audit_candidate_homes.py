import copy
import unittest
from qwen_split.audit_candidate_homes import audit


class HomesTests(unittest.TestCase):
    def setUp(self):
        self.graph = dict(die=dict(w=100,h=100), insts=[dict(n='a',m='m',x=0,y=0,w=10,h=10,o='R0'),
            dict(n='b',m='m',x=30,y=0,w=10,h=10,o='R0')], masters={'m':dict(w=10,h=10,pins=[])},
            buses=[dict(b='ab',n=1,c='data',e=[['a','o'],['b','i']])])
        self.homes = dict(candidate='fixture',homes={i['n']:dict(m='m',x=i['x'],y=i['y'],o='R0') for i in self.graph['insts']})

    def test_current_graph_is_compatible_but_not_qualified(self):
        r=audit(self.graph,self.graph,self.homes)
        self.assertTrue(r['compatible_for_geometry_recheck']);self.assertFalse(r['qualification'])

    def test_pin_mutant_and_incident_inventory(self):
        cur=copy.deepcopy(self.graph);cur['masters']['m']['pins']=[{'name':'x','rect':[0,0,1,1]}]
        r=audit(self.graph,cur,self.homes)
        self.assertFalse(r['compatible_for_geometry_recheck'])
        self.assertEqual(len(r['changed_instances']),2)
        self.assertEqual([b['bus'] for b in r['incident_buses_requiring_recheck']],['ab'])

    def test_missing_and_overlap_are_not_hidden(self):
        cur=copy.deepcopy(self.graph);cur['insts'].append(dict(n='new',m='m',x=60,y=0,w=10,h=10,o='R0'))
        self.homes['homes']['b']['x']=5
        r=audit(self.graph,cur,self.homes)
        self.assertEqual(r['missing_homes'],['new']);self.assertEqual(len(r['rectangle_overlaps']),1)
        self.assertFalse(r['compatible_for_geometry_recheck'])

    def test_bus_only_mutant_refuses_stale_graph(self):
        cur=copy.deepcopy(self.graph);cur['buses'][0]['n']=2
        self.assertFalse(audit(self.graph,cur,self.homes)['compatible_for_geometry_recheck'])


if __name__=='__main__': unittest.main()
