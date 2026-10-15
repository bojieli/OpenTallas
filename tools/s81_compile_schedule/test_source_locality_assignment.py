"""Structural optimiser tests, not native execution or physical qualification."""
from itertools import product
import unittest
from source_locality_assignment import assign,literal_graph,optimise

def node(name,unit,reads=(),writes=(),scope=0,pred=0):
    return dict(id=name,kind='instruction',scope=scope,template_word_sha256=name+'-sha',
                instruction=dict(unit=unit,_reads=list(reads),_writes=list(writes),pred=pred))
def anchor(name,*choices):
    return dict(node=name,template_sha256=name+'-sha',canonical_choices=[dict(fragments=[dict(stage=s) for s in c]) for c in choices])

class LocalityTests(unittest.TestCase):
    def test_read_modify_write_preserves_order_and_both_field_producers(self):
        d=dict(nodes=[node('w1',3,[],['GU']),node('w3',3,[],['GU']),
                      node('sw',2,['GU'],['ACT']),node('out',3,['ACT'],['Y'])])
        _,edges,_=literal_graph(d)
        self.assertEqual({(e['producer'],e['consumer']) for e in edges},{('w1','sw'),('w3','sw'),('sw','out')})
        r=assign(d,{'w1':anchor('w1',[5]),'w3':anchor('w3',[5]),'out':anchor('out',[6])})
        self.assertEqual({x['stage'] for x in r['source_operation_homes']},{5})
        self.assertTrue(all(x['physical_instance'] is None for x in r['source_operation_homes']))
        self.assertFalse(r['dispatch_eligible'])
    def test_inplace_scalar_versions_do_not_drop_the_previous_result(self):
        d=dict(nodes=[node('p',3,[],['X']),node('a',2,['X'],['X']),node('b',2,['X'],['Y'])])
        _,edges,_=literal_graph(d)
        self.assertEqual([(e['producer'],e['consumer']) for e in edges],[('p','a'),('a','b')])
    def test_predicated_write_keeps_possible_previous_value(self):
        d=dict(nodes=[node('p',3,[],['X']),node('read',2,['X'],[]),node('conditional',2,[],['X'],pred=1),node('use',2,['X'],[])])
        _,edges,_=literal_graph(d)
        self.assertEqual({e['producer'] for e in edges if e['consumer']=='use'},{'p','conditional'})
    def test_unrelated_layer_temporary_names_do_not_create_fake_dependencies(self):
        d=dict(nodes=[node('a',2,[],['T'],scope=0),node('b',2,['T'],[],scope=1)])
        _,edges,external=literal_graph(d);self.assertEqual(edges,[]);self.assertEqual(external[0]['consumer'],'b')
    def test_cross_scope_hidden_state_has_literal_producer(self):
        d=dict(nodes=[node('a',2,[],['H'],scope=0),node('b',2,['H'],[],scope=1)])
        _,edges,_=literal_graph(d);self.assertEqual(edges[0]['producer'],'a')
    def test_stale_field_template_is_a_hard_error(self):
        d=dict(nodes=[node('field',3,[],['X']),node('su',2,['X'],[])])
        h=anchor('field',[3]);h['template_sha256']='mutated'
        with self.assertRaisesRegex(ValueError,'stale FIELD'):assign(d,{'field':h})
    def test_binary_graphcut_matches_exhaustive_optimum(self):
        ids=['a','b','c','d'];edges=[('a','b'),('b','c'),('b','d')]
        unary={'a':{0:0,1:3},'d':{0:4,1:0}}
        labels,report=optimise(ids,edges,unary,[0,1])
        def cost(lab):return sum(unary.get(n,{}).get(lab[n],0) for n in ids)+sum(lab[a]!=lab[b] for a,b in edges)
        exact=min(cost(dict(zip(ids,bits))) for bits in product((0,1),repeat=4))
        self.assertEqual(report['final'],exact);self.assertEqual(cost(labels),exact)
        self.assertEqual(report['strict_improvements'],sorted(report['strict_improvements'],reverse=True))
    def test_no_field_anchor_does_not_invent_a_home(self):
        labels,r=optimise(['a','b'],[('a','b')],{},[0,1])
        self.assertEqual(labels,{});self.assertEqual(r['unanchored_operations'],['a','b'])
    def test_conditional_expert_alternatives_have_no_free_fixed_choice(self):
        d=dict(nodes=[node('field',3,[],['X']),node('su',2,['X'],[])])
        r=assign(d,{'field':anchor('field',[0],[1])})
        self.assertEqual(r['objective']['final'],1)
    def test_changed_field_anchor_moves_candidate_without_provider_rule(self):
        d=dict(nodes=[node('field',3,[],['X']),node('su',2,['X'],[])])
        a=assign(d,{'field':anchor('field',[3])});b=assign(d,{'field':anchor('field',[17])})
        self.assertEqual({x['stage'] for x in a['source_operation_homes']},{3})
        self.assertEqual({x['stage'] for x in b['source_operation_homes']},{17})
if __name__=='__main__':unittest.main()
