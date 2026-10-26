#!/usr/bin/env python3
"""Source join: die-emitted canonical536 body equals the physically hardened wrapper."""
import re
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_s81_fulldie as G
import die_port_bind as B

def normalized(s):return re.sub(r'\s+','',re.sub(r'//[^\n]*','',s))

class Relay536Reset(unittest.TestCase):
    def setUp(self):
        self.old=G.RLY536_RSTREG
        self.pdir={f'dsfd_rly_{w}_{f}':dict(ck=('input',1),rs=('input',1),i=('input',w),o=('output',w)) for w,f in [(536,'SN'),(536,'SW'),(536,'WS'),(283,'WN')]}
        self.model=dict(pdir=self.pdir,glue={})
    def tearDown(self):G.RLY536_RSTREG=self.old
    def test_default_source_unchanged_and_only_536_changes(self):
        G.RLY536_RSTREG=False;plain=G.glue_rtl(self.model)
        mods={m.name:m for m in B.parse_modules(plain,'plain')}
        for name,mod in mods.items():
            w=self.pdir[name]['i'][1]
            self.assertIn(normalized(f"reg[{w-1}:0]r;always@(posedgeck[0]ornegedgers[0])if(!rs[0])r<={w}'d0;elser<=i;assigno=r;"),normalized(mod.body))
        G.RLY536_RSTREG=True;new={m.name:m for m in B.parse_modules(G.glue_rtl(self.model),'new')}
        self.assertEqual(mods['dsfd_rly_283_WN'].body,new['dsfd_rly_283_WN'].body)
    def test_candidate_body_equals_hardened_canonical_rtl(self):
        G.RLY536_RSTREG=True
        emitted={m.name:m for m in B.parse_modules(G.glue_rtl(self.model),'emitted')}
        canonical=B.parse_modules((ROOT/'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_536.sv').read_text(),'canonical')
        for m in canonical:
            self.assertEqual(normalized(m.body),normalized(emitted[m.name].body))
            for pn in m.ports:
                self.assertEqual(m.width(pn,m.env({})),emitted[m.name].width(pn,emitted[m.name].env({})))
        self.assertEqual(len(canonical),3)

    def test_reset_contract_is_explicit_and_default_off(self):
        G.RLY536_RSTREG=False
        self.assertIsNone(G.rly536_reset_contract(self.model))
        G.RLY536_RSTREG=True
        contract=G.rly536_reset_contract(self.model)
        self.assertEqual(contract['release_edges_before_first_production'],1)
        self.assertEqual(contract['added_normal_edges'],0)
        self.assertEqual(len(contract['masters']),3)
        self.assertTrue(contract['compiler_bootstrap_qualification'].startswith('OPEN:'))

if __name__=='__main__':unittest.main()
