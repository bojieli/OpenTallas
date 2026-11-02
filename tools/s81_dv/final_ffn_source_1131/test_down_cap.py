"""Single-frame FIN gate controls: useful work is the native/source pilot."""
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[3]
for p in ('tools','tools/s81','tools/s81_dv','tools/s81_dv/layer_prog'):sys.path.insert(0,str(ROOT/p))
from layer_prog.xs_place import down_cap_scorer

class DownCapTest(unittest.TestCase):
    def setUp(self):
        self.cfg=dict(obase=896,ops=0,np=0,fmt=2,rbase=0,rcnt=104,rsplit=0,lo32=0,hi32=0)
        self.score=down_cap_scorer([0,1,2,3],self.cfg)
    def test_complete_rows(self):
        self.assertEqual(self.score([[100+r, r<<13|1,0x3f800000,0] for r in range(4)]),0)
    def test_missing_row(self):
        self.assertGreater(self.score([[100+r,r<<13|1,0x3f800000,0] for r in range(3)]),0)
    def test_invalid_trial_port_collision_is_scored(self):
        self.assertGreater(self.score([[100,r<<13|1,0x3f800000,0] for r in range(4)]),0)
    def test_real_preexisting_f5_train(self):
        # Original0L01 shared.w2 phase71. Values/tags/relative dates preserved.
        words=[[358,134218821,981836768,0],[359,134227013,1017886456,0],[362,134235205,998417996,0],[363,134243397,1024755758,0],[377,134217765,3162757393,0],[378,134225957,992321200,0],[383,134218277,993928064,0],[384,134226469,3174713300,0],[392,134234149,1017852215,0],[393,134242341,3171154886,0],[399,134234661,1032177564,0],[400,134242853,3183062582,0]]
        self.assertGreater(self.score(words),0)

if __name__=='__main__':unittest.main()
