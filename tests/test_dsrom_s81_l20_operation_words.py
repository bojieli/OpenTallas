import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dsrom_s81_execution_binding import CanonicalS81Execution
from dsrom_s81_qe_native_word_bridge import ReleasedQeOperationWords
import dsrom_s82_payload_interface as API

class OperationWordsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use real source descriptors/fragment resolution. No full-stage CFG
        # sweep or inference: the test dispatch only transports source hashes.
        canonical=CanonicalS81Execution(ROOT,stage_join_factory=lambda *a,**k:None)
        cls.source=canonical.source
        def dispatch(node,rank,**kw):
            f=cls.source.resolve(node,rank,**kw)['fragments']
            return dict(source_dispatch_bound=True,fragments=[dict(stage=x['matrix']['stage'],rank=rank,
                source_matrix_sha256=hashlib.sha256(json.dumps(x['matrix'],sort_keys=True,separators=(',',':')).encode()).hexdigest()) for x in f])
        cls.execution=SimpleNamespace(source=cls.source,dispatch=dispatch)
        types={}
        for matrices in cls.source.matrices.values():
            for m in matrices:
                types[m['tensor']]=m['source_dtype']
                if m['source_scale_tensor']:types[m['source_scale_tensor']]='F8_E8M0'
        cls.headers=SimpleNamespace(root=Path(API.SNAPSHOT),descriptor=lambda name:(None,None,dict(dtype=types[name])))
        # Archived reference choices are test inputs, never runtime defaults.
        cls.fixture_ids=[41,65,158,164,259,266]

    def test_all_26_qe_and_six_me_nodes_and_every_fragment(self):
        counts={3:0,1:0};formats=set()
        for node,entry in self.source.nodes.items():
            if not node.startswith('L20.') or 'instruction' not in entry:continue
            f=entry['instruction'];unit=f['unit']
            if not ((unit==3 and f.get('qe_mode')==0) or (unit==1 and f.get('me_wsrc')==0)):continue
            counts[unit]+=1
            ids=self.fixture_ids if self.source.bindings[node]['selector_slot'] is not None else None
            kw={} if ids is None else dict(expert_ids=ids)
            resolved=self.source.resolve(node,0,**kw)
            for ordinal in range(len(resolved['fragments'])):
                p=ReleasedQeOperationWords(self.execution,self.headers,node,0,fragment=ordinal,expert_ids=ids)
                formats.add(p.matrix['format'])
        self.assertEqual(counts,{3:26,1:6});self.assertEqual(formats,{'fp4','fp8','bf16'})

    def test_dynamic_ids_missing_duplicate_unsorted_out_of_range(self):
        for ids in (None,[41]*6,[65,41,158,164,259,266],[41,65,158,164,259,384]):
            with self.assertRaises(ValueError):
                ReleasedQeOperationWords(self.execution,self.headers,'L20.I97',0,expert_ids=ids)
        with self.assertRaises(ValueError):
            ReleasedQeOperationWords(self.execution,self.headers,'L20.I20',0)

    def test_fp8_to_bf16_word_refused_before_host_codec(self):
        p=ReleasedQeOperationWords(self.execution,self.headers,'L20.I68',0)
        with patch.object(API,'matrix_word') as codec:
            with self.assertRaisesRegex(ValueError,'native source transform required'):
                p.read(p.matrix['stage'],0,4*p.pairs[0],0)
            codec.assert_not_called()

    def test_raw_chunk_released_codes_scale_and_fp4_nibble(self):
        # A few raw source bytes only; no matvec, decode or golden callback.
        source=API.Checkpoint()
        try:
            for node,ids in [('L20.I68',None),('L20.I97',self.fixture_ids),('L20.I86',None)]:
                p=ReleasedQeOperationWords(self.execution,source,node,0,expert_ids=ids)
                chunk=p.raw_chunk(0,1,3)
                d=source.descriptor(p.matrix['tensor'])[2]
                row,col=chunk['source_row'],chunk['source_col']
                if chunk['dtype']=='I8':
                    raw=source.raw(p.matrix['tensor'],row*d['shape'][1]+col//2,(col+4)//2-col//2)
                    self.assertEqual(chunk['first_nibble'],col%2)
                else:
                    width=2 if chunk['dtype']=='BF16' else 1
                    raw=source.raw(p.matrix['tensor'],(row*d['shape'][1]+col)*width,3*width)
                self.assertEqual(chunk['codes'],raw)
                self.assertEqual(len(chunk['scales']),0 if chunk['dtype']=='BF16' else 1)
        finally:source.close()

if __name__=='__main__':unittest.main()
