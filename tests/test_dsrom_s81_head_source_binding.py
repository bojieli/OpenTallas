import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('head_binding',ROOT/'tools/dsrom_s81_head_source_binding.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


class HeadBindingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding=M.HeadSourceBinding()

    def test_literal_program_and_terminal(self):
        p=self.binding.compile(opt_in=True,entry14=400,pc_base=100)
        self.assertEqual([n['source_pc'] for n in p['instructions']],list(range(100,107)))
        self.assertEqual((p['producer_pc14'],p['end_pc14']),(105,106))
        f=p['instructions'][5]['literal_fields']
        self.assertEqual([f[x] for x in ('me_nout','me_k','me_round','me_amax','me_oen')],
                         [32320,5120,0,1,1])
        self.assertEqual(p['instructions'][-1]['literal_fields']['wait'],31)
        self.assertFalse(p['actual_terminal_offer'])
        self.assertIn('global_argmax',p['consumer_services'])
        with self.assertRaises(ValueError):self.binding.compile(entry14=0)
        with self.assertRaises(ValueError):self.binding.compile(opt_in=True,entry14=16384)

    def test_rank_homes_and_boundaries(self):
        for rank in range(4):
            for row,col in ((0,0),(0,15),(0,16),(32319,5119)):
                h=self.binding.head_address(rank,row,col)
                w=((rank*32320+row)*5120+col)//16
                gp=2525+w//16384
                self.assertEqual(h['pair']*self.binding.head_dies+h['die'],gp)
                self.assertEqual(h['physical_row']*2+h['parity'],w%8192)
                self.assertEqual(h['bit_range'][0],col%16*16)
        for args in ((4,0,0),(0,32320,0),(0,0,5120),(0,-1,0)):
            with self.assertRaises(ValueError):self.binding.head_address(*args)
        self.assertEqual(self.binding.address('norm.weight',5119)['die'],5050%12)

    def test_model_no_false_timing(self):
        p=self.binding.model()
        self.assertEqual(p['MACs_per_rank'],165478400)
        self.assertEqual(p['chunk8_leaves'],640)
        self.assertEqual(p['padded_leaf_slots'],1024)
        self.assertIsNone(p['whole_token_latency_ns'])
        self.assertFalse(p['hardware_admission'])
        self.assertFalse(p['legacy_sequential_accumulator_admitted'])

    def test_bounded_checkpoint_raw_bytes(self):
        # Sparse exact-shape source fixture: no full tensor materialization.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            table={};patches=[]
            for name,shape in M.SHAPES.items():
                count=shape[0]*(shape[1] if len(shape)==2 else 1)
                table[name]=dict(dtype='BF16',shape=shape,data_offsets=[0,count*2])
                path=root/(name+'.safetensors')
                hdr=json.dumps({name:table[name]}).encode()
                with path.open('wb') as f:
                    f.write(struct.pack('<Q',len(hdr)));f.write(hdr);f.truncate(8+len(hdr)+count*2)
                patterns=[0x8000,0x7fc1,0x7f80,0xff80,0x0001,0x3f80,0x7fff,0xffff]
                fd=os.open(path,os.O_RDWR)
                try:
                    offset=8+len(hdr)
                    os.pwrite(fd,struct.pack('<8H',*patterns),offset)
                    os.pwrite(fd,struct.pack('<H',0x8000),offset+(count-1)*2)
                finally:os.close(fd)
                patches.append((name,path.name))
            (root/'model.safetensors.index.json').write_text(json.dumps({'weight_map':dict(patches)}))
            with M.ReleasedHeadByteProvider(self.binding,root) as p:
                c=p.chunk8(0,0,0)
                self.assertEqual(c['bf16_bits'],patterns)
                self.assertEqual(len(c['payload']),16)
                self.assertEqual(p.chunk8(3,32319,639)['bf16_bits'][-1],0x8000)
                self.assertEqual(p.norm_crom(0)['word64'],0x80000000)
                self.assertEqual(p.norm_crom(1)['word64'],0x7fc10000)
                self.assertEqual(p.norm_crom(5119)['word64'],0x80000000)
                self.assertEqual(len(p.raw_word(0,0,0)[1]),32)
                bf=p.native_bf_word(0,0,0,0)
                self.assertEqual(bf['word274']&65535,patterns[0])
                self.assertEqual(bf['word274']>>256,0)
                self.assertEqual(len(bf['source_homes']),8)
                with self.assertRaises(ValueError):p.read('head.weight',0,0,0)
                with self.assertRaises(ValueError):p.chunk8(0,0,640)
            with self.assertRaises(ValueError):p.norm_crom(0)


if __name__=='__main__':unittest.main()
