import importlib.util
import itertools
import json
from pathlib import Path
import random
import struct
import unittest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('tree',ROOT/'tools/uarch_topk_integer_tree_model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def bits_to_key(x):
    c=0 if x==0x80000000 else x
    return (~c)&0xffffffff if c>>31 else c|0x80000000

def tree_radix_select(words,ranks,n,k,stride):
    keys=[bits_to_key(x) for x in words];width=m.clog2(ranks*n+1);prefix=0;rr=k
    for shift in [24,16,8,0]:
        counts=[0]*256
        for key in keys:
            if (key>>(shift+8))==(prefix>>(shift+8)):counts[(key>>shift)&255]+=1
        suffix=m.tree_suffix(counts,width);valid,b,gt=m.tree_choose(counts,suffix,rr,width)
        if not valid:raise AssertionError('no legal radix match')
        prefix|=b<<shift;rr-=gt
    result=[]
    for i,key in enumerate(keys):
        if key>prefix or (key==prefix and rr>0):
            result.append((i//n)*stride+i%n)
            if key==prefix:rr-=1
    return result

class IntegerTree(unittest.TestCase):
    def test_checkpoint_explicitly_refuses_caller_credit(self):
        r=m.build();self.assertEqual(r["checkpoint_scope"]["status"],"STRUCTURAL_SIZING_ONLY_NOT_FULL_CALLER_G0")
        self.assertIn("LDW4",r["checkpoint_scope"]["known_ROM_binding_gap"])
        self.assertFalse(r["admission"]["engine_RTL_admitted"])
    def test_byte_exact_model_replay(self):
        self.assertEqual(m.build(),json.loads((m.BASE/'model.json').read_text()))
    def test_exhaustive_modulo_and_priority(self):
        for counts in itertools.product(range(8),repeat=4):
            oracle=[sum(counts[b+1:])&7 for b in range(4)]
            self.assertEqual(m.serial_suffix(counts,3),oracle);self.assertEqual(m.tree_suffix(counts,3),oracle)
            for rr in range(8):
                matches=[b for b in range(4) if oracle[b]<rr<=((oracle[b]+counts[b])&7)]
                want=(True,matches[-1],oracle[matches[-1]]) if matches else (False,0,0)
                self.assertEqual(m.serial_choose(counts,oracle,rr,3),want)
                self.assertEqual(m.tree_choose(counts,oracle,rr,3),want)
    def test_all_actual_CB_widths_boundaries(self):
        rng=random.Random(20261002)
        for width in [12,14,16,18]:
            mask=(1<<width)-1
            vectors=[[0]*256,[mask]*256,[1]+[0]*255,[0]*255+[mask],[mask if i&1 else 1 for i in range(256)]]+[[rng.randrange(mask+1) for _ in range(256)] for _ in range(64)]
            for v in vectors:
                oracle=[sum(v[b+1:])&mask for b in range(256)]
                self.assertEqual(m.tree_suffix(v,width),oracle)
                for rr in [0,1,mask,mask//2]:self.assertEqual(m.tree_choose(v,oracle,rr,width),m.serial_choose(v,oracle,rr,width))
    def test_popcount_exhaustive16_and_full_P(self):
        for v in range(65536):self.assertEqual(m.popcount_tree([(v>>i)&1 for i in range(16)]),v.bit_count())
        for p in [64,1024]:
            for v in [[0]*p,[1]*p,[i&1 for i in range(p)]]:self.assertEqual(m.popcount_tree(v),sum(v))
    def test_mutants_detected(self):
        v=[1,2,3,4];correct=m.tree_suffix(v,4)
        wrong=[sum(v[:i])&15 for i in range(4)];self.assertNotEqual(correct,wrong)
        v=[5]*4;su=m.tree_suffix(v,3);self.assertEqual(m.tree_choose(v,su,4,3),(True,3,0))
        matching=[i for i in range(4) if su[i]<4<=((su[i]+v[i])&7)]
        self.assertNotEqual(min(matching),m.tree_choose(v,su,4,3)[1])
        self.assertNotEqual(64&63,m.popcount_tree([1]*64))
    def test_all_full_shapes_rank_order_and_tie_filter(self):
        for ranks,n in [(4,512),(4,2048),(96,512),(96,2048)]:
            cap=ranks*n;words=[(0x80000000,0,0x3f800000,0xbf800000,0x7f800000,0xff800000,1,0x80000001)[i%8] for i in range(cap)]
            stride=n*2
            floats=[struct.unpack('!f',struct.pack('!I',x))[0] for x in words]
            for k in [1,n,cap]:
                ids=[(i//n)*stride+i%n for i in range(cap)]
                selected=sorted(range(cap),key=lambda i:(-floats[i],ids[i]))[:k]
                expected=sorted(ids[i] for i in selected)
                self.assertEqual(tree_radix_select(words,ranks,n,k,stride),expected)
    def test_model_complete_shapes_no_guessed_clock_slot_credit(self):
        r=m.build();self.assertFalse(r['admission']['engine_RTL_admitted']);self.assertFalse(r['admission']['physical_PR_admitted'])
        self.assertEqual([(s['parameters']['N'],s['parameters']['NMAX']) for s in r['shapes']],[(4,512),(4,2048),(96,512),(96,2048)])
        for s in r['shapes']:
            self.assertIsNone(s['clock']['SS_stage_delay_ps']);self.assertIsNone(s['area']['full_instance_area_um2'])
            self.assertIsNone(s['boundary_and_tracks']['fit']);self.assertEqual(s['storage']['bits_by_register_group']['candidate_score_and_ID'],64*s['parameters']['N']*s['parameters']['NMAX'])
    def test_cycle_comparison_and_pipeline_cost(self):
        shapes=m.build()['shapes']
        self.assertEqual([s['pipeline']['extra_cycles_command'] for s in shapes],[116,116,132,132])
        self.assertEqual([s['latency']['DIG4_extra_vs_DIG8'] for s in shapes],[156,540,220,796])
        self.assertEqual([s['extra_bits']['total'] for s in shapes],[60091,62129,799403,801441])
    def test_retained_no_match_control_contract(self):
        state=(7,9);found,bin,gt=m.tree_choose([0]*256,[0]*256,1,12)
        nextstate=(bin,gt) if found else state
        self.assertEqual(nextstate,state)
        source=(m.BASE/'inputs/rtl/chip/ot_coll_topk_merge.sv').read_text();self.assertIn('if (!found && suf[b] < rr && rr <= suf[b] + cnt[b])',source)
if __name__=='__main__':unittest.main()
