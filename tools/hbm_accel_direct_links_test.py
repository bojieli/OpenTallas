#!/usr/bin/env python3
"""Focused graph, compiler order, and golden reduction fixtures; no inference."""
import json
import unittest
from pathlib import Path
import numpy as np
import hbm_accel_direct_links_model as M
import hdc_golden as G

class Contract(unittest.TestCase):
    def test_reciprocal_ports(self):
        for r in range(96):
            peers=[M.peer(r,p) for p in range(20)]
            self.assertEqual(len(set(peers)),20)
            self.assertNotIn(r,peers)
            for q in peers: self.assertIn(r,[M.peer(q,p) for p in range(20)])
    def test_two_hop_reachability(self):
        for src in range(96):
            for dst in range(96):
                if src==dst: continue
                peers=[M.peer(src,p) for p in range(20)]
                self.assertTrue(dst in peers or any(dst in [M.peer(q,p) for p in range(20)] for q in peers))
    def test_w19_subtree(self):
        plan=M.compile_plan('w19_oreduce')
        self.assertEqual(len(plan['trees']),8)
        self.assertEqual(len(plan['trees'][0]),3)
        self.assertEqual(plan['trees'][0][-1][0],[[[0,1],[2,3]],[[4,5],[6,7]]])
        self.assertFalse(plan['zeros_inserted'])
    def test_non_power_two_tail(self):
        t=M.tree(range(96))
        self.assertEqual(len(t),7)
        self.assertEqual(len(t[-2][-1]),1)
    def test_budget_no_free_mux_or_phy(self):
        p=M.price()
        self.assertFalse(p['adopt'])
        self.assertIsNone(p['area']['mux_area_mm2'])
        self.assertIsNone(p['area']['corridor_capacity_tracks'])
        self.assertGreater(p['area']['wire_register_bits'],0)
        self.assertEqual(p['timing']['phy_fec_grade'].split(':')[0],'ESTIMATE')

def fixture(out):
    rng=np.random.default_rng(20261003)
    cases=[]; expected=[]
    for i in range(12):
        a=(rng.normal(size=96)*np.exp2(rng.integers(-20,20,size=96))).astype(np.float32)
        if i==0: a[:8]=[1e10,1,-1e10,3,2**24,1,-2**24,1]
        if i==1: a[:]=0; a[::2]=-0.
        if i==2: a[:]=np.nextafter(np.float32(0),np.float32(1))
        nodes=list(a)
        while len(nodes)>1:
            nodes=[G.add(nodes[j],nodes[j+1]) if j+1<len(nodes) else nodes[j]
                   for j in range(0,len(nodes),2)]
        cases.extend(a.view(np.uint32).tolist()); expected.append(int(G.bits(nodes[0])))
    out.mkdir(parents=True,exist_ok=True)
    for name,values in [('inputs.hex',cases),('expected.hex',expected)]:
        p=out/name
        if p.exists(): raise RuntimeError('refuse overwrite')
        p.write_text(''.join(f'{x:08x}\n' for x in values))

if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='fixture': fixture(Path(sys.argv[2]))
    else: unittest.main()
