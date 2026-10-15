"""Ordered arithmetic graph and finite-host topology invariants."""
import copy
import unittest
from tree_hosts import candidate, blocks


def fixture():
    # Morton leaves and the production first-unused host rule.
    leaves=[f't_{(i&1)+2*((i>>2)&1)}_{((i>>1)&1)+2*((i>>3)&1)}' for i in range(16)]
    insts=[dict(n=f't_{x}_{y}',m='qfd_tile_nk',x=x*522.288,y=y*1450,w=449.256,h=1442.856)
           for x in range(4) for y in range(4)]
    insts.append(dict(n='slab',m='qfd_port_tiles_0',x=2400,y=1450,w=1036.8,h=2462.4))
    buses=[];used=set();prev=leaves
    for lv in range(4):
        out=[]
        for idx in range(len(prev)//2):
            subtree=leaves[idx*2**(lv+1):(idx+1)*2**(lv+1)]
            host=next(t for t in subtree if t not in used);used.add(host)
            for side,src in zip('ab',prev[2*idx:2*idx+2]):
                buses.append((f'tree_0_{lv}_{2*idx}{side}','tree_block',514,[src,host]))
            out.append(host)
        prev=out
    buses.append(('bword_0','tree_spine',514,[prev[0],'slab']))
    return dict(insts=insts,buses=buses)


def ordered_ast(d):
    nodes=blocks(d['buses'])[0]
    results={}
    for (lv,idx),ab in sorted(nodes.items()):
        root=ab['a'][3][1]
        assert root==ab['b'][3][1]
        results[root]=tuple(ab[s][3][0] if lv==0 else results[ab[s][3][0]] for s in 'ab')
    return results[root]


class TreeHostsTest(unittest.TestCase):
    def test_exact_order_and_unique_hardened_owner(self):
        old=fixture();new,r=candidate(old)
        self.assertEqual(ordered_ast(old),ordered_ast(new))
        hosts=[x[2] for x in r['blocks'][0]['hosts']]
        self.assertEqual(len(set(hosts)),15)
        self.assertNotIn(r['blocks'][0]['unused'],hosts)
        self.assertLessEqual(r['candidate_max'],r['baseline_max'])

    def test_wrong_pair_mutant_changes_arithmetic_graph(self):
        new,_=candidate(fixture());bad=copy.deepcopy(new)
        # Keep all values delivered, but exchange two non-sibling K slices.
        ia=next(i for i,b in enumerate(bad['buses']) if b[0]=='tree_0_0_0a')
        ib=next(i for i,b in enumerate(bad['buses']) if b[0]=='tree_0_0_2a')
        bad['buses'][ia][3][0],bad['buses'][ib][3][0]=bad['buses'][ib][3][0],bad['buses'][ia][3][0]
        self.assertNotEqual(ordered_ast(new),ordered_ast(bad))

    def test_relayed_input_refused(self):
        d=fixture();d['buses'][0][3][0]='rly_bad'
        with self.assertRaises(ValueError):candidate(d)


if __name__=='__main__':unittest.main()
