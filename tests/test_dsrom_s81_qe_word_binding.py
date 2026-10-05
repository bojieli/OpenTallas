import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from dsrom_s81_qe_word_binding import ReleasedQeWordBinding
import dsrom_s82_payload_interface as API


class BindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with gzip.open(ROOT / 'results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz', 'rt') as f:
            cls.matrix = next(json.loads(line) for line in f if '"alias":"wkv"' in line)

    def setup_binding(self):
        m = self.matrix
        e = SimpleNamespace(source=SimpleNamespace(resolve=lambda node, rank: dict(fragments=[dict(matrix=m)])))
        s = SimpleNamespace(root=Path(API.SNAPSHOT), descriptor=lambda name: (None, None, dict(dtype='F8_E8M0' if name.endswith('.scale') else 'F8_E4M3')))
        d = dict(node='L0.I8', source_dispatch_bound=True, fragments=[dict(stage=0, rank=0,
                 phase=1, key=65536, cfg_logical_range=[25,50],
                 source_matrix_sha256=hashlib.sha256(json.dumps(m, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                 instruction=dict(unit=3, qe_mode=0, qe_fp4=0, qe_nb=160, qe_nout=128,
                                  qe_xbase=46464, qe_obase=420096, qe_wbase=65536, qe_ind=0))])
        return e, s, d

    def test_actual_pair_census_and_codec_delegation(self):
        e, s, d = self.setup_binding()
        p = ReleasedQeWordBinding(e,s,0,d)
        self.assertEqual((len(p.pairs),p.pairs[0],p.pairs[-1]), (64,2,1190))
        with patch.object(API, 'matrix_word', return_value=123) as codec:
            self.assertEqual(p(0,0,8,0),123)
            codec.assert_called_once_with(self.matrix,s,0,8,0)

    def test_i7_pair_and_wrong_rank_refused_before_read(self):
        e,s,d = self.setup_binding(); p=ReleasedQeWordBinding(e,s,0,d)
        with patch.object(API, 'matrix_word') as codec:
            for a in [(0,0,0,0),(0,1,8,0),(1,0,8,0)]:
                with self.assertRaises(ValueError): p(*a)
            codec.assert_not_called()

    def test_dispatch_mutants(self):
        for key,value in [('phase',0),('source_matrix_sha256','bad'),('cfg_logical_range',[0,25])]:
            e,s,d=self.setup_binding(); d=copy.deepcopy(d); d['fragments'][0][key]=value
            with self.assertRaises(ValueError): ReleasedQeWordBinding(e,s,0,d)

    def test_literal_and_dtype_mutants(self):
        e,s,d=self.setup_binding(); d['fragments'][0]['instruction']['qe_obase']=419776
        with self.assertRaises(ValueError): ReleasedQeWordBinding(e,s,0,d)
        e,s,d=self.setup_binding(); s.descriptor=lambda _: (None,None,dict(dtype='BF16'))
        with self.assertRaises(ValueError): ReleasedQeWordBinding(e,s,0,d)

    def test_unowned_padding_rejected_by_original_decoder(self):
        e,s,d=self.setup_binding(); p=ReleasedQeWordBinding(e,s,0,d)
        # Only160 logical words are owned in each bank; physical row80 is past them.
        with self.assertRaisesRegex(ValueError,'unique matrix owner'): p(0,0,8,80)

if __name__ == '__main__': unittest.main()
