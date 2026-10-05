"""Software codec/golden checks, not RTL or selected-cluster qualification."""
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hbrom_vectors as H

class VectorsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (H.P.DEFAULT_CHECKPOINT/'model.safetensors.index.json').exists():
            raise unittest.SkipTest('released checkpoint unavailable')
        cls.source=H.P.Checkpoint()
    @classmethod
    def tearDownClass(cls):cls.source.close()

    def test_fullk_source_bits_and_golden(self):
        # Cross row32 scale boundary. These small shards test codecs, not cluster shape.
        seen=set()
        with tempfile.TemporaryDirectory() as d:
            for i,name in enumerate(H.DEFAULT_TENSORS):
                payload=H.checkpoint_rows(self.source,name,[31,32])
                k=payload['codes'].shape[1];seen.add(k)
                x=H.G.to_bf16(np.random.default_rng(55).normal(size=k).astype(np.float32))
                out=Path(d)/str(i)
                m=H.emit_case(self.source,name,[31,32],out,2*i,x)
                self.assertEqual(m['logical_K'],k)
                self.assertGreater(m['weight_nonzero_codes'],0)
                self.assertGreater(m['weight_distinct_codes'],1)
                self.assertEqual(m['geometry']['groups'],(k+({'fp4':2048,'fp8':1024,'bf16':512}[m['format']])-1)//({'fp4':2048,'fp8':1024,'bf16':512}[m['format']]))
                expected=np.array([int(v,16) for v in (out/'expected_fp32.hex').read_text().split()],dtype=np.uint32)
                if m['format']!='bf16':
                    self.assertTrue(np.array_equal(H.G.bits(H.G.to_bf16(H.G.from_bits(expected))),H.G.bits(H.V.linear_q(payload['weights'],x))))
                else:
                    self.assertTrue(np.array_equal(expected,H.G.bits(H.V.csum(H.G.mul(payload['weights'],H.G.to_bf16(x)[None,:])))))
                # Independently decode actual macro files and compare every lane code
                # against direct checkpoint values at the issue coordinate.
                address=[int(v,16) for v in (out/'line_address.hex').read_text().split()]
                images={}
                for file in out.glob('rom_*.hex'):images[file.name]=[int(v,16) for v in file.read_text().split()]
                for index,(r,g,t) in enumerate(H.S.issue_order(2,m['geometry']['groups'],8,True)):
                    rec=address[index]
                    self.assertNotEqual(rec,0xffffffff)
                    bg=m['bankgroup_base']+rec//8192; rec%=8192
                    parity=(rec//8)%2; row=(rec//16)*8+rec%8
                    words=[images[f'rom_g{bg}_s{s}_p{parity}.hex'][row] for s in range(4)]
                    for lane in range({'fp4':8,'fp8':4,'bf16':64}[m['format']]):
                        fmt=m['format'];start=H.A.code_coordinate(fmt,g,t,lane)
                        if fmt=='bf16':
                            got=(words[lane//16]>>(16*(lane%16)))&65535
                            want=int(payload['codes'][r,start]) if start<k else 0
                            self.assertEqual(got,want)
                        else:
                            wi=lane//2 if fmt=='fp4' else lane
                            base=136*(lane%2) if fmt=='fp4' else 0
                            width=4 if fmt=='fp4' else 8
                            for j in range(32):
                                got=(words[wi]>>(base+width*j))&((1<<width)-1)
                                want=int(payload['codes'][r,start+j]) if start+j<k else 0
                                self.assertEqual(got,want)
                            sc=(words[wi]>>(base+32*width))&255
                            self.assertEqual(sc,int(payload['scales'][r,start//32]) if start<k else 127)
                self.assertFalse(set(m['checker_only'])&set(m['runtime_inputs']))
        self.assertEqual(seen,{5120,2304,1280,4096,8192})

    def test_wo_a_grouped_owner_conservation_and_distinct_inputs(self):
        import hbrom_gate as gate
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'vectors'
            subprocess.run([sys.executable,str(ROOT/'tools/hbrom_vectors.py'),'--tensor',
                            'layers.0.attn.wo_a.weight','--owners','416','--out',str(out)],check=True)
            campaign=json.loads((out/'campaign.json').read_text());cases=campaign['cases']
            self.assertEqual(len(cases),8)
            self.assertEqual([c['activation_group'] for c in cases],list(range(8)))
            self.assertEqual(sorted(r for c in cases for r in c['source_rows']),list(range(0,8192,416)))
            self.assertEqual(len({c['files_sha256']['activation.npy'] for c in cases}),8)
            for c in cases:
                g=c['activation_group']
                self.assertTrue(all(g*1024<=r<(g+1)*1024 for r in c['source_rows']))
            runtime=Path(d)/'runtime';prep=gate.prepare(out/'campaign.json',runtime,4)
            self.assertEqual(prep['operations'],8)
            config=[int(v,16) for v in (runtime/'config.hex').read_text().split()]
            self.assertEqual([config[8*g+6] for g in range(8)],
                             [c['physical_base_record'] for c in cases])
            # Eight disjoint jobs are merged into the same immutable physical
            # bank group; each record still matches its original source image.
            for i,c in enumerate(cases):
                for record in range(c['physical_base_record'],c['physical_base_record']+c['physical_records']):
                    par=(record//8)%2;row=(record//16)*8+record%8
                    for stream in range(4):
                        name=f'rom_g0_s{stream}_p{par}.hex'
                        source=(out/f'op{i:02d}'/name).read_text().split()
                        merged=(runtime/name).read_text().split()
                        self.assertEqual(source[row],merged[row])

    def test_reject_bounds_and_bad_activation(self):
        with self.assertRaises(ValueError):H.checkpoint_rows(self.source,'head.weight',[-1])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):H.emit_case(self.source,'head.weight',[0],Path(d)/'bad',0,np.zeros(17))
        with self.assertRaises(ValueError):H.activation_fragments(np.ones(5120,dtype=np.float32),'bf16',17)

if __name__=='__main__':unittest.main()
